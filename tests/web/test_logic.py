import zipfile
from io import BytesIO

from PIL import Image

from photo_border.web.logic import save_uploads, zip_directory


class TestSaveUploads:
    def test_writes_each_upload_to_dest_dir(self, tmp_path):
        dest = tmp_path / "uploads"
        uploads = [("a.jpg", b"fake-jpeg-bytes"), ("b.png", b"fake-png-bytes")]

        paths = save_uploads(uploads, dest)

        assert len(paths) == 2
        assert (dest / "a.jpg").read_bytes() == b"fake-jpeg-bytes"
        assert (dest / "b.png").read_bytes() == b"fake-png-bytes"

    def test_creates_dest_dir_if_missing(self, tmp_path):
        dest = tmp_path / "nested" / "uploads"

        save_uploads([("a.jpg", b"x")], dest)

        assert (dest / "a.jpg").exists()


class TestZipDirectory:
    def test_zips_all_files_with_relative_paths(self, tmp_path):
        src_dir = tmp_path / "out"
        (src_dir / "sub").mkdir(parents=True)
        Image.new("RGB", (5, 5), (1, 2, 3)).save(src_dir / "a.jpg")
        Image.new("RGB", (5, 5), (4, 5, 6)).save(src_dir / "sub" / "b.jpg")

        zip_bytes = zip_directory(src_dir)

        with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
            names = set(zf.namelist())
            assert names == {"a.jpg", "sub/b.jpg"}

    def test_empty_directory_produces_empty_zip(self, tmp_path):
        src_dir = tmp_path / "empty"
        src_dir.mkdir()

        zip_bytes = zip_directory(src_dir)

        with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
            assert zf.namelist() == []
