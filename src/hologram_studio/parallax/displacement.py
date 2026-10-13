"""Convert a normalized depth map into a per-layer pixel displacement field."""
from __future__ import annotations

import numpy as np


def displacement_field(depth: np.ndarray, layer_index: int, layer_count: int,
                       max_displacement_px: int, focal_plane: float = 0.5) -> np.ndarray:
    """Return an HxWx2 float32 field (dx, dy) for the given layer.

    Layers in front of the focal plane move right on positive parallax,
    layers behind move left. The magnitude scales with distance from the
    focal plane so the hologram reads as real depth, not a uniform slide.
    """
    if not 0 <= focal_plane <= 1:
        raise ValueError("focal_plane must be in [0,1]")
    if layer_count < 2:
        raise ValueError("layer_count must be >= 2")

    layer_pos = layer_index / (layer_count - 1)
    signed = (layer_pos - focal_plane) * 2.0        # -1..1 around focal plane
    # Ease-out so the far layers don't overshoot and tear.
    magnitude = np.sign(signed) * (abs(signed) ** 0.85) * max_displacement_px

    h, w = depth.shape
    dx = np.full((h, w), magnitude, dtype=np.float32)
    dy = np.full((h, w), magnitude * 0.15, dtype=np.float32)  # slight vertical drift
    return np.stack([dx, dy], axis=-1)