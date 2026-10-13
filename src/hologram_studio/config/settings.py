"""Settings loader. TOML on disk, pydantic in memory, sane defaults."""
from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class DepthSettings(BaseModel):
    model_name: str = "depth-anything-v2-small"
    weights_dir: Path = Path("models/weights")
    input_size: int = 518
    use_gpu: bool = False
    # ONNX Runtime falls back to CPU silently when the EP is missing.
    # Pin the provider list explicitly to avoid the surprise.
    providers: list[str] = Field(default_factory=lambda: ["CPUExecutionProvider"])


class ParallaxSettings(BaseModel):
    layer_count: int = Field(default=12, ge=4, le=64)
    max_displacement_px: int = Field(default=48, ge=4, le=256)
    focal_plane: float = Field(default=0.5, ge=0.0, le=1.0)
    edge_bleed: int = Field(default=6, ge=0, le=32)


class RenderSettings(BaseModel):
    fps: int = Field(default=24, ge=8, le=60)
    duration_s: float = Field(default=4.0, gt=0, le=30)
    codec: Literal["libx264", "libvpx-vp9", "gif"] = "libx264"
    crf: int = Field(default=18, ge=0, le=51)
    loop_pingpong: bool = True


class Settings(BaseModel):
    depth: DepthSettings = Field(default_factory=DepthSettings)
    parallax: ParallaxSettings = Field(default_factory=ParallaxSettings)
    render: RenderSettings = Field(default_factory=RenderSettings)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    @field_validator("log_level", mode="before")
    @classmethod
    def _upper(cls, v: object) -> object:
        return v.upper() if isinstance(v, str) else v


def load_settings(path: Path | None) -> Settings:
    if path is None:
        return Settings()
    with path.open("rb") as fh:
        raw = tomllib.load(fh)
    return Settings.model_validate(raw)