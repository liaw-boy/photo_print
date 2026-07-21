import piexif
from PIL import Image

from photo_border.core.io import load_image, save_image


def _make_exif_bytes(model: str = "TestCam") -> bytes:
    exif_dict = {"0th": {piexif.ImageIFD.Model: model}}
    return piexif.dump(exif_dict)


class TestSaveImageFormat:
    def test_infers_format_from_extension_jpeg(self, tmp_path):
        img = Image.new("RGB", (10, 10), (1, 2, 3))
        dst = tmp_path / "out.jpg"

        save_image(img, dst, quality=90)

        assert dst.exists()
        with Image.open(dst) as reopened:
            assert reopened.format == "JPEG"
            assert reopened.size == (10, 10)

    def test_infers_format_from_extension_png(self, tmp_path):
        img = Image.new("RGB", (10, 10), (1, 2, 3))
        dst = tmp_path / "out.png"

        save_image(img, dst)

        with Image.open(dst) as reopened:
            assert reopened.format == "PNG"

    def test_explicit_format_overrides_extension(self, tmp_path):
        img = Image.new("RGB", (10, 10), (1, 2, 3))
        dst = tmp_path / "out.jpg"

        save_image(img, dst, format="PNG")

        with Image.open(dst) as reopened:
            assert reopened.format == "PNG"

    def test_creates_parent_directories(self, tmp_path):
        img = Image.new("RGB", (10, 10), (1, 2, 3))
        dst = tmp_path / "nested" / "dir" / "out.jpg"

        save_image(img, dst)

        assert dst.exists()


class TestSaveImageMetadata:
    def test_exif_bytes_are_written_and_readable(self, tmp_path):
        img = Image.new("RGB", (10, 10), (1, 2, 3))
        dst = tmp_path / "out.jpg"
        exif_bytes = _make_exif_bytes("MyCamera")

        save_image(img, dst, exif=exif_bytes)

        reloaded = piexif.load(str(dst))
        assert reloaded["0th"][piexif.ImageIFD.Model] == b"MyCamera"

    def test_icc_profile_is_written(self, tmp_path):
        img = Image.new("RGB", (10, 10), (1, 2, 3))
        dst = tmp_path / "out.jpg"
        fake_icc = b"fake-icc-profile-bytes"

        save_image(img, dst, icc_profile=fake_icc)

        with Image.open(dst) as reopened:
            assert reopened.info.get("icc_profile") == fake_icc


class TestLoadImage:
    def test_loads_pixel_content(self, tmp_path):
        src = tmp_path / "src.png"
        Image.new("RGB", (5, 5), (9, 9, 9)).save(src)

        loaded = load_image(src)

        assert loaded.size == (5, 5)
        assert loaded.getpixel((0, 0)) == (9, 9, 9)

    def test_preserves_exif_info_for_downstream_extraction(self, tmp_path):
        src = tmp_path / "src.jpg"
        exif_bytes = _make_exif_bytes("LoadCam")
        Image.new("RGB", (5, 5), (1, 1, 1)).save(src, exif=exif_bytes)

        loaded = load_image(src)

        assert loaded.info.get("exif") is not None
