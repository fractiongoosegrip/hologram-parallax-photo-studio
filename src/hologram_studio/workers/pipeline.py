"""The ingest -> depth -> slice -> inpaint -> composite -> render chain."""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from hologram_studio.config.settings import Settings
from hologram_studio.depth.depth_engine import DepthEngine
from hologram_studio.inpaint.hole_filler import fill_holes
from hologram_studio.ingest.photo_loader import load_photo
from hologram_studio.parallax.displacement import displacement_field
from hologram_studio.parallax.layer_slicer import slice_layers
from hologram_studio.render.drivers import get_driver
from hologram_studio.utils.geometry import warp_layer
from hologram_studio.utils.timing import stopwatch
from hologram_studio.workers.jobs import RenderJob, RenderPreset

log = logging.getLogger(__name__)

# Preset -> (driver name, layer_count, max_displacement_px, focal_plane)
_PRESET_TABLE: dict[RenderPreset, tuple[str, int, int, float]] = {
    RenderPreset.WIGGLE_2_5D:       ("gif",        8,  24, 0.5),
    RenderPreset.LOOKING_GLASS:     ("mp4",       16,  64, 0.4),
    RenderPreset.LENTICULAR_PRINT:  ("lenticular", 24, 96, 0.5),
    RenderPreset.HOLO_LOOP:         ("webm",      12,  40, 0.45),
}


def run_pipeline(job: RenderJob, settings: Settings) -> Path:
    driver_name, layer_count, max_disp, focal = _PRESET_TABLE[job.preset]
    job.output_dir.mkdir(parents=True, exist_ok=True)

    with stopwatch("ingest") as t_ingest:
        photo = load_photo(job.source)

    model_path = settings.depth.weights_dir / f"{job.depth_model}.onnx"
    with stopwatch("depth") as t_depth:
        engine = DepthEngine(
            model_path,
            providers=settings.depth.providers,
            input_size=settings.depth.input_size,
        )
        depth_map = engine.infer(photo.rgb)

    with stopwatch("slice") as t_slice:
        layers = slice_layers(
            photo.rgb, depth_map.depth, layer_count,
            edge_bleed=settings.parallax.edge_bleed,
        )

    with stopwatch("inpaint") as t_inpaint:
        filled = [fill_holes(l.rgba) for l in layers]

    with stopwatch("composite") as t_comp:
        frames = _composite_frames(
            filled, depth_map.depth, layer_count, max_disp, focal,
            settings.render.fps, settings.render.duration_s,
            settings.render.loop_pingpong,
        )

    with stopwatch("render") as t_render:
        driver = get_driver(driver_name, crf=settings.render.crf) \
            if driver_name == "mp4" else get_driver(driver_name)
        out_path = job.output_dir / job.output_stem()
        written = driver.write(frames, out_path, fps=settings.render.fps)

    log.info(
        "job %s timings: ingest=%.2fs depth=%.2fs slice=%.2fs inpaint=%.2fs comp=%.2fs render=%.2fs",
        job.id, t_ingest.elapsed, t_depth.elapsed, t_slice.elapsed,
        t_inpaint.elapsed, t_comp.elapsed, t_render.elapsed,
    )
    return written


def _composite_frames(layers, depth, layer_count, max_disp, focal,
                      fps, duration_s, pingpong) -> list[np.ndarray]:
    n_frames = max(2, int(fps * duration_s))
    h, w = depth.shape
    frames: list[np.ndarray] = []

    # Ping-pong swing so the loop is seamless without a keyframe pop.
    if pingpong:
        swing = np.concatenate([np.linspace(-1, 1, n_frames // 2),
                                np.linspace(1, -1, n_frames - n_frames // 2)])
    else:
        swing = np.linspace(-1, 1, n_frames)

    for s in swing:
        canvas = np.zeros((h, w, 3), dtype=np.float32)
        for layer in layers:
            field = displacement_field(depth, layer.index, layer_count, max_disp, focal)
            warped = warp_layer(layer.rgba, field * float(s))
            alpha = warped[..., 3:4].astype(np.float32) / 255.0
            canvas = canvas * (1 - alpha) + warped[..., :3].astype(np.float32) *