import zipfile
from io import BytesIO
from pathlib import Path


def save_uploads(uploads: list[tuple[str, bytes]], dest_dir: Path) -> list[Path]:
    """把 (檔名, 內容 bytes) 清單寫進 dest_dir，回傳寫入的路徑清單。"""
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    paths = []
    for filename, content in uploads:
        path = dest_dir / filename
        path.write_bytes(content)
        paths.append(path)
    return paths


def zip_directory(source_dir: Path) -> bytes:
    """把 source_dir 底下所有檔案（含子資料夾，保留相對路徑）打包成 zip bytes。"""
    source_dir = Path(source_dir)
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(source_dir.rglob("*")):
            if path.is_file():
                zf.write(path, arcname=path.relative_to(source_dir).as_posix())
    return buffer.getvalue()
