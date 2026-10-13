"""CLI entrypoint. `hps render photo.jpg --preset looking-glass`."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from hologram_studio.config.settings import load_settings
from hologram_studio.workers.pool import WorkerPool
from hologram_studio.workers.jobs import RenderJob, RenderPreset


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="hps",
        description="AI holographic / parallax 3D photo generator",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("render", help="Render a parallax hologram from a photo")
    r.add_argument("photo", type=Path)
    r.add_argument("--preset", default="wiggle-2.5d",
                   choices=[p.value for p in RenderPreset])
    r.add_argument("--output-dir", type=Path, default=Path("outputs"))
    r.add_argument("--depth-model", default="depth-anything-v2-small")
    r.add_argument("--config", type=Path, default=None)
    r.add_argument("--workers", type=int, default=2)

    sub.add_parser("selftest", help="Run a synthetic end-to-end render")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    settings = load_settings(args.config)

    if args.cmd == "selftest":
        from hologram_studio.workers.selftest import run_selftest
        return run_selftest(settings)

    job = RenderJob(
        source=args.photo,
        preset=RenderPreset(args.preset),
        depth_model=args.depth_model,
        output_dir=args.output_dir,
    )
    pool = WorkerPool(settings=settings, size=args.workers)
    try:
        pool.submit(job)
        pool.drain()
    finally:
        pool.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())