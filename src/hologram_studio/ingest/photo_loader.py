"""Load a source photo, normalize orientation, cap resolution, extract EXIF."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

log = logging.getLogger(__name__)

MAX_SIDE = 16384
# Pillow's decompression-bomb guard defaults to ~89M px. We raise it
# deliberately because phone panoramas legitimately exceed that.
Image.MAX_IMAGE_PIXELS = 400_000_000


@dataclass(frozen=True, slots=True)
class LoadedPhoto:
    rgb: np.ndarray          # HxWx3, uint8, sRGB, EXIF-rotated
    source_path: Path
    exif: dict[str, str]
    had_alpha: bool


def load_photo(path: Path) -> LoadedPhoto:
    if not path.is_file():
        raise FileNotFoundError(f"photo not found: {path}")

    with Image.open(path) as img:
        exif_raw = img.getexif()
        exif = {str(k): str(v) for k, v in exif_raw.items()}
        had_alpha = img.mode in ("RGBA", "LA") or "transparency" in img.info

        img = ImageOps.exif_transpose(img) or img
        if img.mode != "RGB":
            img = img.convert("RGB")

        w, h = img.size
        if max(w, h) > MAX_SIDE:
            scale = MAX_SIDE / max(w, h)
            new_size = (int(w * scale), int(h * scale))
            log.warning("photo %dx%d exceeds cap; downscaling to %s", w, h, new_size)
            img = img.resize(new_size, Image.LANCZOS)

        rgb = np.asarray(img, dtype=np.uint8)

    log.info("loaded %s (%dx%d) alpha=%s", path.name, rgb.shape[1], rgb.shape[0], had_alpha)
    return LoadedPhoto(rgb=rgb, source_path=path, exif=exif, had_alpha=had_alpha)