from pathlib import Path

from PIL import Image

from .errors import UnsupportedFormatError

_EXTENSION_TO_FORMAT = {
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
    ".tif": "TIFF",
    ".tiff": "TIFF",
    ".heic": "HEIF",
    ".heif": "HEIF",
}


def load_image(path: Path) -> Image.Image:
    """讀取影像，保留 Pillow 解析出的 exif/icc_profile 等 metadata 於 image.info。"""
    image = Image.open(path)
    image.load()
    return image


def save_image(
    image: Image.Image,
    dst_path: Path,
    *,
    format: str | None = None,
    quality: int = 95,
    exif: bytes | None = None,
    icc_profile: bytes | None = None,
) -> None:
    """依副檔名（或明確指定的 format）寫出影像，並帶入 EXIF/ICC 等 metadata。"""
    dst_path = Path(dst_path)
    save_format = format.upper() if format else _infer_format(dst_path)

    save_kwargs: dict = {}
    if save_format == "JPEG":
        save_kwargs["quality"] = quality
        save_kwargs["subsampling"] = 0
    if exif is not None:
        save_kwargs["exif"] = exif
    if icc_profile is not None:
        save_kwargs["icc_profile"] = icc_profile

    dst_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(dst_path, format=save_format, **save_kwargs)


def _infer_format(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix not in _EXTENSION_TO_FORMAT:
        raise UnsupportedFormatError(f"無法從副檔名判斷格式: {path}")
    return _EXTENSION_TO_FORMAT[suffix]
