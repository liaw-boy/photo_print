from pathlib import Path

import typer

from photo_border.core import batch, io as image_io, pipeline
from photo_border.core.color import parse_color
from photo_border.core.errors import InvalidBorderConfigError, PhotoBorderError
from photo_border.core.models import BorderConfig, BorderMode, ReferenceEdge

app = typer.Typer(add_completion=False, no_args_is_help=True)

_MODE_MAP = {
    "percent": BorderMode.PERCENT,
    "aspect": BorderMode.ASPECT,
    "aspect-then-percent": BorderMode.ASPECT_THEN_PERCENT,
}
_EDGE_MAP = {
    "long": ReferenceEdge.LONG,
    "short": ReferenceEdge.SHORT,
}


def build_config(
    *,
    mode: str,
    percent: float | None,
    edge: str,
    ratio: str | None,
    color: str,
    format: str,
    quality: int,
    no_metadata: bool,
    metadata_backend: str,
) -> BorderConfig:
    """把 CLI 傳入的字串參數組成 BorderConfig。純函式，跟 Typer 無關，方便單獨測試。"""
    if mode not in _MODE_MAP:
        raise InvalidBorderConfigError(
            f"未知的 --mode: {mode!r}（可用值：{', '.join(_MODE_MAP)}）"
        )
    if edge not in _EDGE_MAP:
        raise InvalidBorderConfigError(f"未知的 --edge: {edge!r}（可用值：long, short）")

    return BorderConfig(
        mode=_MODE_MAP[mode],
        percent=percent,
        reference_edge=_EDGE_MAP[edge],
        target_ratio=_parse_ratio(ratio),
        color=parse_color(color),
        output_format=None if format == "keep" else format,
        jpeg_quality=quality,
        keep_metadata=not no_metadata,
        metadata_backend=metadata_backend,
    )


def _parse_ratio(value: str | None) -> tuple[int, int] | None:
    if value is None:
        return None
    parts = value.split(":")
    if len(parts) != 2:
        raise InvalidBorderConfigError(f"--ratio 需為 W:H 格式，例如 4:5，收到: {value!r}")
    try:
        return (int(parts[0]), int(parts[1]))
    except ValueError as exc:
        raise InvalidBorderConfigError(f"--ratio 需為整數 W:H，收到: {value!r}") from exc


@app.command()
def main(
    input: Path = typer.Argument(..., help="輸入檔案或資料夾"),
    output: Path = typer.Argument(..., help="輸出資料夾（單檔輸入時也可指定完整輸出檔名）"),
    mode: str = typer.Option("percent", "--mode", help="percent | aspect | aspect-then-percent"),
    percent: float | None = typer.Option(None, "--percent", help="邊框百分比，如 0.05"),
    edge: str = typer.Option("short", "--edge", help="百分比參考邊：long | short"),
    ratio: str | None = typer.Option(None, "--ratio", help="目標長寬比，如 4:5"),
    color: str = typer.Option("#FFFFFF", "--color", help="邊框顏色，hex/named/rgb"),
    format: str = typer.Option("keep", "--format", help="jpeg | png | tiff | heif | keep"),
    quality: int = typer.Option(95, "--quality", help="JPEG 品質 1-100"),
    no_metadata: bool = typer.Option(False, "--no-metadata", help="不保留 EXIF/ICC"),
    metadata_backend: str = typer.Option(
        "auto", "--metadata-backend", help="auto | piexif | exiftool"
    ),
    recursive: bool = typer.Option(False, "--recursive", help="遞迴處理子資料夾"),
    overwrite: bool = typer.Option(True, "--overwrite/--no-overwrite", help="是否覆寫既有輸出"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="顯示逐張處理結果"),
) -> None:
    if not input.exists():
        typer.echo(f"錯誤：輸入路徑不存在: {input}", err=True)
        raise typer.Exit(code=2)

    try:
        config = build_config(
            mode=mode,
            percent=percent,
            edge=edge,
            ratio=ratio,
            color=color,
            format=format,
            quality=quality,
            no_metadata=no_metadata,
            metadata_backend=metadata_backend,
        )
    except PhotoBorderError as exc:
        typer.echo(f"參數錯誤：{exc}", err=True)
        raise typer.Exit(code=2) from exc

    if input.is_file():
        raise typer.Exit(code=_run_single_file(input, output, config, overwrite, verbose))

    raise typer.Exit(code=_run_batch(input, output, config, recursive, overwrite, verbose))


def _run_single_file(
    src: Path, output: Path, config: BorderConfig, overwrite: bool, verbose: bool
) -> int:
    dst = output if output.suffix else output / src.name
    if config.output_format:
        dst = dst.with_suffix(image_io.extension_for_format(config.output_format))

    if not overwrite and dst.exists():
        typer.echo(f"略過（已存在）：{dst}")
        return 0

    result = pipeline.process_image(src, dst, config)
    for warning in result.warnings:
        typer.echo(f"警告：{warning}", err=True)

    if result.success:
        if verbose:
            typer.echo(f"完成：{dst}")
        return 0

    typer.echo(f"失敗：{src} -> {result.error}", err=True)
    return 1


def _run_batch(
    input_dir: Path,
    output_dir: Path,
    config: BorderConfig,
    recursive: bool,
    overwrite: bool,
    verbose: bool,
) -> int:
    def _progress(index: int, total: int, result) -> None:
        if verbose or not result.success:
            status = "OK" if result.success else f"FAIL: {result.error}"
            typer.echo(f"[{index}/{total}] {result.src_path.name}: {status}")

    report = batch.process_batch(
        input_dir,
        output_dir,
        config,
        recursive=recursive,
        overwrite=overwrite,
        progress_cb=_progress,
    )
    typer.echo(f"完成 {report.succeeded}/{report.total}（失敗 {report.failed}）")

    if report.failed > 0:
        return 1
    return 0


if __name__ == "__main__":
    app()
