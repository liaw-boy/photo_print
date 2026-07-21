from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from .constants import DEFAULT_COLOR, DEFAULT_JPEG_QUALITY


class BorderMode(Enum):
    PERCENT = "percent"
    ASPECT = "aspect"
    ASPECT_THEN_PERCENT = "aspect_then_percent"


class ReferenceEdge(Enum):
    LONG = "long"
    SHORT = "short"


@dataclass(frozen=True)
class BorderConfig:
    mode: BorderMode
    percent: float | None = None
    reference_edge: ReferenceEdge = ReferenceEdge.SHORT
    target_ratio: tuple[int, int] | None = None
    color: tuple[int, int, int] = DEFAULT_COLOR
    output_format: str | None = None
    jpeg_quality: int = DEFAULT_JPEG_QUALITY
    keep_metadata: bool = True


@dataclass(frozen=True)
class CanvasPlan:
    src_size: tuple[int, int]
    canvas_size: tuple[int, int]
    paste_offset: tuple[int, int]
    border_px: tuple[int, int, int, int]  # left, top, right, bottom


@dataclass(frozen=True)
class ProcessResult:
    src_path: Path
    dst_path: Path | None
    success: bool
    canvas_plan: CanvasPlan | None = None
    error: str | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class BatchReport:
    results: tuple[ProcessResult, ...]
    total: int
    succeeded: int
    failed: int
