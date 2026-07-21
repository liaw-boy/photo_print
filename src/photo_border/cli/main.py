from pathlib import Path

import typer

from photo_border.core import batch, config_builder, io as image_io, pipeline
from photo_border.core.errors import PhotoBorderError
from photo_border.core.models import BorderConfig

app = typer.Typer(add_completion=False, no_args_is_help=True)

# 保留 build_config 名稱與 core.config_builder.build_border_config 同義，
# 方便既有測試與其他呼叫端沿用（實際邏輯已搬到 core，cli/web 共用同一份）。
build_config = config_builder.build_border_config


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
