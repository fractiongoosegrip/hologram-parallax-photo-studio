"""Fill disocclusion holes with OpenCV Telea by default.

LaMa / MAT ONNX models can be dropped in later; the interface stays the
same so the render pipeline doesn't branch on backend.
"""
from __future__ import annotations

import logging

import cv2
import numpy as np

log = logging.getLogger(__name__)


def fill_holes(rgba: np.ndarray, method: str = "telea", radius: int = 3) -> np.ndarray:
    """Fill transparent pixels (alpha==0) using neighboring opaque content.

    Args:
        rgba: HxWx4 uint8. Alpha is the hole mask.
        method: "telea" or "ns" (Navier-Stokes).
        radius: inpainting neighborhood radius in pixels.

    Returns:
        HxWx4 uint8 with the RGB channels inpainted where alpha was 0.
        Alpha is preserved so the layer still composites correctly.
    """
    if rgba.ndim != 3 or rgba.shape[2] != 4:
        raise ValueError("expected HxWx4 RGBA")

    alpha = rgba[..., 3]
    mask = (alpha == 0).astype(np.uint8)
    if mask.sum() == 0:
        return rgba

    flag = cv2.INPAINT_TELEA if method == "telea" else cv2.INPAINT_NS
    bgr = cv2.cvtColor(rgba[..., :3], cv2.COLOR_RGB2BGR)
    filled = cv2.inpaint(bgr, mask, radius, flag)
    filled_rgb = cv2.cvtColor(filled, cv2.COLOR_BGR2RGB)

    out = rgba.copy()
    out[..., :3] = np.where(mask[..., None].astype(bool), filled_rgb, rgba[..., :3])
    log.debug("filled %d hole pixels (method=%s)", int(mask.sum()), method)
    return out