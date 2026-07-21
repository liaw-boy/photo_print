from pathlib import Path

from PIL import ImageOps

from . import border, geometry, io as image_io, metadata as metadata_mod
from .models import BorderConfig, ProcessResult


def process_image(src: Path, dst: Path, config: BorderConfig) -> ProcessResult:
    """單張影像的完整處理流程：讀取→EXIF方向轉正→算邊框→合成→寫回 metadata→存檔。

    任何失敗都會被捕捉並包成 success=False 的 ProcessResult，不對外拋例外，
    讓 batch.py 可以逐張隔離錯誤。
    """
    try:
        image = image_io.load_image(src)
        image = ImageOps.exif_transpose(image) or image

        plan = geometry.calculate_canvas(image.size, config)
        result_image = border.apply_border(image, plan, config.color)

        exif_bytes = None
        icc_bytes = None
        warnings: list[str] = []

        if config.keep_metadata:
            meta = metadata_mod.extract_metadata(src)
            exif_bytes = metadata_mod.normalize_orientation(meta.exif)
            icc_bytes = meta.icc_profile

        image_io.save_image(
            result_image,
            dst,
            format=config.output_format,
            quality=config.jpeg_quality,
            exif=exif_bytes,
            icc_profile=icc_bytes,
        )

        if config.keep_metadata:
            backend = metadata_mod.select_backend(config.metadata_backend)
            if backend == "exiftool":
                warnings.extend(metadata_mod.transfer_with_exiftool(src, dst))

        return ProcessResult(
            src_path=src,
            dst_path=dst,
            success=True,
            canvas_plan=plan,
            warnings=tuple(warnings),
        )
    except Exception as exc:
        return ProcessResult(
            src_path=src,
            dst_path=None,
            success=False,
            error=str(exc),
        )
