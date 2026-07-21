import piexif
from PIL import Image

from photo_border.core.models import BorderConfig, BorderMode
from photo_border.core.pipeline import process_image


def _save_with_exif(path, size, color, orientation=None, model="TestCam", icc=None):
    zeroth = {piexif.ImageIFD.Model: model}
    if orientation is not None:
        zeroth[piexif.ImageIFD.Orientation] = orientation
    exif_bytes = piexif.dump({"0th": zeroth})
    kwargs = {"exif": exif_bytes}
    if icc is not None:
        kwargs["icc_profile"] = icc
    Image.new("RGB", size, color).save(path, **kwargs)


class TestProcessImageHappyPath:
    def test_output_matches_geometry_plan(self, tmp_path):
        src = tmp_path / "src.jpg"
        _save_with_exif(src, (100, 80), (10, 20, 30))
        dst = tmp_path / "out.jpg"
        config = BorderConfig(mode=BorderMode.PERCENT, percent=0.1, color=(255, 0, 0))

        result = process_image(src, dst, config)

        assert result.success is True
        assert result.dst_path == dst
        assert dst.exists()
        # 短邊 80 * 0.1 = 8(四捨五入) -> 四邊各加 8
        assert result.canvas_plan.canvas_size == (116, 96)

    def test_border_color_applied_in_output_file(self, tmp_path):
        src = tmp_path / "src.jpg"
        _save_with_exif(src, (100, 80), (10, 20, 30))
        dst = tmp_path / "out.jpg"
        config = BorderConfig(mode=BorderMode.PERCENT, percent=0.1, color=(255, 0, 0))

        process_image(src, dst, config)

        with Image.open(dst) as out:
            # JPEG 有損壓縮，容許極小誤差
            pixel = out.getpixel((0, 0))
            assert all(abs(a - b) <= 2 for a, b in zip(pixel, (255, 0, 0)))

    def test_keeps_metadata_by_default(self, tmp_path):
        src = tmp_path / "src.jpg"
        _save_with_exif(src, (100, 80), (10, 20, 30), model="MyCamera", icc=b"fake-icc")
        dst = tmp_path / "out.jpg"
        config = BorderConfig(mode=BorderMode.PERCENT, percent=0.1)

        process_image(src, dst, config)

        reloaded_exif = piexif.load(str(dst))
        assert reloaded_exif["0th"][piexif.ImageIFD.Model] == b"MyCamera"
        with Image.open(dst) as out:
            assert out.info.get("icc_profile") == b"fake-icc"

    def test_keep_metadata_false_strips_exif(self, tmp_path):
        src = tmp_path / "src.jpg"
        _save_with_exif(src, (100, 80), (10, 20, 30), model="MyCamera")
        dst = tmp_path / "out.jpg"
        config = BorderConfig(mode=BorderMode.PERCENT, percent=0.1, keep_metadata=False)

        process_image(src, dst, config)

        reloaded_exif = piexif.load(str(dst))
        assert reloaded_exif["0th"].get(piexif.ImageIFD.Model) is None


class TestProcessImageOrientation:
    def test_exif_orientation_is_applied_and_reset(self, tmp_path):
        src = tmp_path / "src.jpg"
        # Orientation=6 表示需要順時針轉 90 度才是正確方向，原始像素是橫的 100x80
        _save_with_exif(src, (100, 80), (5, 6, 7), orientation=6)
        dst = tmp_path / "out.jpg"
        config = BorderConfig(mode=BorderMode.PERCENT, percent=0.0)

        result = process_image(src, dst, config)

        assert result.success is True
        with Image.open(dst) as out:
            assert out.size == (80, 100)  # 轉正後長寬互換
        reloaded_exif = piexif.load(str(dst))
        assert reloaded_exif["0th"][piexif.ImageIFD.Orientation] == 1


class TestProcessImageErrors:
    def test_missing_src_file_returns_failure_result(self, tmp_path):
        src = tmp_path / "does_not_exist.jpg"
        dst = tmp_path / "out.jpg"
        config = BorderConfig(mode=BorderMode.PERCENT, percent=0.1)

        result = process_image(src, dst, config)

        assert result.success is False
        assert result.dst_path is None
        assert result.error is not None
        assert not dst.exists()

    def test_invalid_config_returns_failure_result(self, tmp_path):
        src = tmp_path / "src.jpg"
        _save_with_exif(src, (100, 80), (10, 20, 30))
        dst = tmp_path / "out.jpg"
        config = BorderConfig(mode=BorderMode.PERCENT, percent=None)

        result = process_image(src, dst, config)

        assert result.success is False
        assert result.error is not None
