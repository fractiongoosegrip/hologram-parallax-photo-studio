"""Output driver registry. Each driver writes one parallax hologram format."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np


class OutputDriver(ABC):
    """A driver consumes a stack of composited frames and writes a file."""

    extension: str = ""

    @abstractmethod
    def write(self, frames: list[np.ndarray], out_path: Path, fps: int) -> Path:
        ...


class Mp4Driver(OutputDriver):
    extension = ".mp4"

    def __init__(self, crf: int = 18) -> None:
        self._crf = crf

    def write(self, frames: list[np.ndarray], out_path: Path, fps: int) -> Path:
        import imageio.v3 as iio
        out_path = out_path.with_suffix(self.extension)
        iio.imwrite(
            out_path, np.stack(frames), fps=fps, codec="libx264",
            pixelformat="yuv420p", quality=None,
            output_params=["-crf", str(self._crf)],
        )
        return out_path


class WebmDriver(OutputDriver):
    extension = ".webm"

    def write(self, frames: list[np.ndarray], out_path: Path, fps: int) -> Path:
        import imageio.v3 as iio
        out_path = out_path.with_suffix(self.extension)
        iio.imwrite(out_path, np.stack(frames), fps=fps, codec="libvpx-vp9")
        return out_path


class GifDriver(OutputDriver):
    extension = ".gif"

    def write(self, frames: list[np.ndarray], out_path: Path, fps: int) -> Path:
        import imageio.v3 as iio
        out_path = out_path.with_suffix(self.extension)
        duration_ms = int(1000 / fps)
        iio.imwrite(out_path, np.stack(frames), duration=duration_ms, loop=0)
        return out_path


class LenticularStripDriver(OutputDriver):
    """Writes a horizontal strip of N views for lenticular printing."""
    extension = ".strip.png"

    def write(self, frames: list[np.ndarray], out_path: Path, fps: int) -> Path:
        import imageio.v3 as iio
        out_path = out_path.with_suffix(self.extension)
        strip = np.concatenate(frames, axis=1)
        iio.imwrite(out_path, strip)
        return out_path


_REGISTRY: dict[str, type[OutputDriver]] = {
    "mp4": Mp4Driver,
    "webm": WebmDriver,
    "gif": GifDriver,
    "lenticular": LenticularStripDriver,
}


def get_driver(name: str, **kwargs: object) -> OutputDriver:
    try:
        cls = _REGISTRY[name.lower()]
    except KeyError as exc:
        raise ValueError(f"unknown output driver: {name!r}") from exc
    return cls(**kwargs)  # type: ignore[arg-type]