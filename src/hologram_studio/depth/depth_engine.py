"""Depth inference wrapper around ONNX Runtime.

Ships with a Depth-Anything-V2-small default. Any ONNX model with a
single image input and a single HxW depth output works; the wrapper
probes input names at load time rather than hardcoding them.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DepthMap:
    depth: np.ndarray        # HxW float32 in [0,1], 1.0 == nearest
    source_size: tuple[int, int]  # (w, h) of the RGB it was inferred from


class DepthEngine:
    def __init__(self, model_path: Path, providers: list[str] | None = None,
                 input_size: int = 518) -> None:
        import onnxruntime as ort  # local import — heavy, optional on non-Windows

        if not model_path.is_file():
            raise FileNotFoundError(
                f"depth model missing: {model_path}. "
                "Run scripts/fetch_weights.py to download."
            )
        self._input_size = input_size
        self._session = ort.InferenceSession(
            str(model_path),
            providers=providers or ["CPUExecutionProvider"],
        )
        self._input_name = self._session.get_inputs()[0].name
        self._output_name = self._session.get_outputs()[0].name
        log.info("depth engine ready: %s (%s)", model_path.name, self._session.get_providers())

    def infer(self, rgb: np.ndarray) -> DepthMap:
        import cv2

        h, w = rgb.shape[:2]
        resized = cv2.resize(rgb, (self._input_size, self._input_size),
                             interpolation=cv2.INTER_AREA)
        # ImageNet normalization — Depth-Anything-V2 expects it.
        x = resized.astype(np.float32) / 255.0
        x = (x - np.array([0.485, 0.456, 0.406], dtype=np.float32)) / \
            np.array([0.229, 0.224, 0.225], dtype=np.float32)
        x = x.transpose(2, 0, 1)[None, ...]  # NCHW

        out = self._session.run([self._output_name], {self._input_name: x})[0]
        depth = np.squeeze(out).astype(np.float32)

        dmin, dmax = float(depth.min()), float(depth.max())
        if dmax - dmin < 1e-6:
            log.warning("depth map is flat; check the input photo")
            depth = np.zeros_like(depth)
        else:
            depth = (depth - dmin) / (dmax - dmin)

        depth = cv2.resize(depth, (w, h), interpolation=cv2.INTER_LINEAR)
        return DepthMap(depth=depth, source_size=(w, h))