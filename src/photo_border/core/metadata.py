import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import piexif
from PIL import Image

_EXIFTOOL_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class ImageMetadata:
    exif: bytes | None
    icc_profile: bytes | None


def extract_metadata(path: Path) -> ImageMetadata:
    """從來源檔案讀出 EXIF 與 ICC profile 原始 bytes（Tier 1，供 piexif/Pillow 寫回用）。"""
    with Image.open(path) as image:
        return ImageMetadata(
            exif=image.info.get("exif"),
            icc_profile=image.info.get("icc_profile"),
        )


def normalize_orientation(exif_bytes: bytes | None) -> bytes | None:
    """把 EXIF 的 Orientation 標記重設為 1。用於「像素已依原方向轉正後」避免輸出檔被二次旋轉。"""
    if exif_bytes is None:
        return None
    try:
        exif_dict = piexif.load(exif_bytes)
    except Exception:
        return exif_bytes

    if piexif.ImageIFD.Orientation in exif_dict.get("0th", {}):
        exif_dict["0th"][piexif.ImageIFD.Orientation] = 1

    return piexif.dump(exif_dict)


def exiftool_available() -> bool:
    return shutil.which("exiftool") is not None


def select_backend(requested: str = "auto") -> str:
    """決定要用哪個 metadata backend：'piexif' 或 'exiftool'。"""
    if requested != "auto":
        return requested
    return "exiftool" if exiftool_available() else "piexif"


def transfer_with_exiftool(src_path: Path, dst_path: Path) -> list[str]:
    """Tier 2：用 exiftool 把 src 的完整 metadata（含 MakerNote/XMP/IPTC）複製到已存檔的 dst。

    回傳 warnings 清單；exiftool 不存在或執行失敗都不拋例外，只回報 warning 讓上層決定如何處理。
    """
    if not exiftool_available():
        return ["exiftool 未安裝，僅保留 Tier 1（piexif）等級的 metadata"]

    cmd = [
        "exiftool",
        "-TagsFromFile",
        str(src_path),
        "-all:all",
        "-icc_profile",
        "-overwrite_original",
        str(dst_path),
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=_EXIFTOOL_TIMEOUT_SECONDS
        )
    except Exception as exc:
        return [f"exiftool 執行失敗: {exc}"]

    if result.returncode != 0:
        return [f"exiftool 回傳非 0 ({result.returncode}): {result.stderr.strip()}"]

    return []
