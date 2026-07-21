from collections.abc import Callable, Iterator
from pathlib import Path

from . import io as image_io, pipeline
from .constants import SUPPORTED_EXTENSIONS
from .models import BatchReport, BorderConfig, ProcessResult

ProgressCallback = Callable[[int, int, ProcessResult], None]


def process_batch(
    input_dir: Path,
    output_dir: Path,
    config: BorderConfig,
    *,
    recursive: bool = False,
    overwrite: bool = True,
    progress_cb: ProgressCallback | None = None,
) -> BatchReport:
    """掃描 input_dir 下所有支援格式的圖片，逐張處理並輸出到 output_dir（保留子資料夾結構）。

    單張失敗不會中斷整批；結果彙整在回傳的 BatchReport 裡。
    overwrite=False 時，輸出檔已存在的來源會被略過，不計入 total。
    """
    files = sorted(_iter_input_files(input_dir, recursive))
    planned = [(src, _dst_for(src, input_dir, output_dir, config)) for src in files]
    if not overwrite:
        planned = [(src, dst) for src, dst in planned if not dst.exists()]

    total = len(planned)
    results: list[ProcessResult] = []

    for index, (src, dst) in enumerate(planned, start=1):
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


def _dst_for(src: Path, input_dir: Path, output_dir: Path, config: BorderConfig) -> Path:
    rel = src.relative_to(input_dir)
    if config.output_format:
        rel = rel.with_suffix(image_io.extension_for_format(config.output_format))
    return output_dir / rel
