from collections.abc import Callable, Iterator
from pathlib import Path

from . import pipeline
from .constants import SUPPORTED_EXTENSIONS
from .models import BatchReport, BorderConfig, ProcessResult

ProgressCallback = Callable[[int, int, ProcessResult], None]


def process_batch(
    input_dir: Path,
    output_dir: Path,
    config: BorderConfig,
    *,
    recursive: bool = False,
    progress_cb: ProgressCallback | None = None,
) -> BatchReport:
    """掃描 input_dir 下所有支援格式的圖片，逐張處理並輸出到 output_dir（保留子資料夾結構）。

    單張失敗不會中斷整批；結果彙整在回傳的 BatchReport 裡。
    """
    files = sorted(_iter_input_files(input_dir, recursive))
    total = len(files)
    results: list[ProcessResult] = []

    for index, src in enumerate(files, start=1):
        dst = output_dir / src.relative_to(input_dir)
        result = pipeline.process_image(src, dst, config)
        results.append(result)
        if progress_cb is not None:
            progress_cb(index, total, result)

    succeeded = sum(1 for r in results if r.success)
    return BatchReport(
        results=tuple(results),
        total=total,
        succeeded=succeeded,
        failed=total - succeeded,
    )


def _iter_input_files(input_dir: Path, recursive: bool) -> Iterator[Path]:
    pattern = "**/*" if recursive else "*"
    for path in sorted(input_dir.glob(pattern)):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            yield path
