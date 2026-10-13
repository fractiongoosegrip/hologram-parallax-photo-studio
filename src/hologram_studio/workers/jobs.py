"""Job dataclasses and preset table."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from uuid import uuid4


class RenderPreset(str, Enum):
    WIGGLE_2_5D = "wiggle-2.5d"
    LOOKING_GLASS = "looking-glass"
    LENTICULAR_PRINT = "lenticular-print"
    HOLO_LOOP = "holo-loop"


@dataclass(slots=True)
class RenderJob:
    source: Path
    preset: RenderPreset
    depth_model: str
    output_dir: Path
    id: str = field(default_factory=lambda: uuid4().hex[:12])
    attempts: int = 0
    max_attempts: int = 3

    def output_stem(self) -> str:
        return f"{self.source.stem}_{self.preset.value}_{self.id}"

    def next_attempt(self) -> "RenderJob":
        self.attempts += 1
        return self

    @property
    def exhausted(self) -> bool:
        return self.attempts >= self.max_attempts