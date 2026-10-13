"""Slice an RGB + depth pair into N RGBA layers with alpha from depth bands."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class ParallaxLayer:
    index: int
    rgba: np.ndarray          # HxWx4 uint8
    depth_band: tuple[float, float]
    displacement_px: float


def slice_layers(rgb: np.ndarray, depth: np.ndarray, layer_count: int,
                 edge_bleed: int = 6) -> list[ParallaxLayer]:
    if rgb.shape[:2] != depth.shape:
        raise ValueError("rgb and depth must share HxW")
    if layer_count < 2:
        raise ValueError("layer_count must be >= 2")

    h, w = depth.shape
    layers: list[ParallaxLayer] = []
    edges = np.linspace(0.0, 1.0, layer_count + 1)

    for i in range(layer_count):
        lo, hi = float(edges[i]), float(edges[i + 1])
        # Soft band with a small feather so adjacent layers overlap.
        band = ((depth >= lo) & (depth < hi)).astype(np.float32)
        if edge_bleed > 0:
            import cv2
            k = edge_bleed * 2 + 1
            band = cv2.GaussianBlur(band, (k, k), 0)

        alpha = np.clip(band * 255.0, 0, 255).astype(np.uint8)
        rgba = np.dstack([rgb, alpha])
        layers.append(ParallaxLayer(
            index=i,
            rgba=rgba,
            depth_band=(lo, hi),
            displacement_px=(i / (layer_count - 1) - 0.5) * 2.0,
        ))
    return layers