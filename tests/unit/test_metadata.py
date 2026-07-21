import subprocess

import piexif
from PIL import Image

from photo_border.core.metadata import (
    ImageMetadata,
    exiftool_available,
    extract_metadata,
    normalize_orientation,
    select_backend,
    transfer_with_exiftool,
)


def _make_exif_bytes(model: str = "TestCam", orientation: int | None = None) -> bytes:
    zeroth: dict = {piexif.ImageIFD.Model: model}
    if orientation is not None:
        zeroth[piexif.ImageIFD.Orientation] = orientation
    return piexif.dump({"0th": zeroth})


class TestExtractMetadata:
    def test_extracts_exif_and_icc(self, tmp_path):
        src = tmp_path / "src.jpg"
        exif_bytes = _make_exif_bytes("MyCamera")
        icc_bytes = b"fake-icc-bytes"
        Image.new("RGB", (5, 5), (1, 2, 3)).save(src, exif=exif_bytes, icc_profile=icc_bytes)

        meta = extract_metadata(src)

        assert isinstance(meta, ImageMetadata)
        assert meta.exif is not None
        assert meta.icc_profile == icc_bytes
        decoded = piexif.load(meta.exif)
        assert decoded["0th"][piexif.ImageIFD.Model] == b"MyCamera"

    def test_extracts_none_when_no_metadata(self, tmp_path):
        src = tmp_path / "plain.png"
        Image.new("RGB", (5, 5), (1, 2, 3)).save(src)

        meta = extract_metadata(src)

        assert meta.exif is None
        assert meta.icc_profile is None


class TestNormalizeOrientation:
    def test_resets_orientation_to_1(self):
        exif_bytes = _make_exif_bytes("Cam", orientation=6)

        normalized = normalize_orientation(exif_bytes)

        decoded = piexif.load(normalized)
        assert decoded["0th"][piexif.ImageIFD.Orientation] == 1
        assert decoded["0th"][piexif.ImageIFD.Model] == b"Cam"

    def test_none_input_returns_none(self):
        assert normalize_orientation(None) is None

    def test_no_orientation_tag_is_noop(self):
        exif_bytes = _make_exif_bytes("Cam")

        normalized = normalize_orientation(exif_bytes)

        decoded = piexif.load(normalized)
        assert decoded["0th"][piexif.ImageIFD.Model] == b"Cam"
        assert piexif.ImageIFD.Orientation not in decoded["0th"]

    def test_corrupted_bytes_returned_unchanged(self):
        garbage = b"not-real-exif-data"

        result = normalize_orientation(garbage)

        assert result == garbage


class TestExiftoolAvailable:
    def test_true_when_which_finds_it(self, mocker):
        mocker.patch("shutil.which", return_value="/usr/bin/exiftool")
        assert exiftool_available() is True

    def test_false_when_which_returns_none(self, mocker):
        mocker.patch("shutil.which", return_value=None)
        assert exiftool_available() is False


class TestSelectBackend:
    def test_auto_picks_exiftool_when_available(self, mocker):
        mocker.patch("photo_border.core.metadata.exiftool_available", return_value=True)
        assert select_backend("auto") == "exiftool"

    def test_auto_falls_back_to_piexif(self, mocker):
        mocker.patch("photo_border.core.metadata.exiftool_available", return_value=False)
        assert select_backend("auto") == "piexif"

    def test_explicit_choice_is_respected(self, mocker):
        assert select_backend("piexif") == "piexif"
        assert select_backend("exiftool") == "exiftool"


class TestTransferWithExiftool:
    def test_missing_exiftool_returns_warning_and_skips_subprocess(self, tmp_path, mocker):
        mocker.patch("photo_border.core.metadata.exiftool_available", return_value=False)
        run_mock = mocker.patch("subprocess.run")

        warnings = transfer_with_exiftool(tmp_path / "src.jpg", tmp_path / "dst.jpg")

        assert warnings
        run_mock.assert_not_called()

    def test_success_returns_no_warnings_and_calls_correct_command(self, tmp_path, mocker):
        mocker.patch("photo_border.core.metadata.exiftool_available", return_value=True)
        run_mock = mocker.patch(
            "subprocess.run",
            return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
        )
        src, dst = tmp_path / "src.jpg", tmp_path / "dst.jpg"

        warnings = transfer_with_exiftool(src, dst)

        assert warnings == []
        called_cmd = run_mock.call_args.args[0]
        assert called_cmd[0] == "exiftool"
        assert str(src) in called_cmd
        assert str(dst) in called_cmd

    def test_nonzero_returncode_produces_warning(self, tmp_path, mocker):
        mocker.patch("photo_border.core.metadata.exiftool_available", return_value=True)
        mocker.patch(
            "subprocess.run",
            return_value=subprocess.CompletedProcess(
                args=[], returncode=1, stdout="", stderr="boom"
            ),
        )

        warnings = transfer_with_exiftool(tmp_path / "src.jpg", tmp_path / "dst.jpg")

        assert any("boom" in w for w in warnings)

    def test_subprocess_exception_produces_warning(self, tmp_path, mocker):
        mocker.patch("photo_border.core.metadata.exiftool_available", return_value=True)
        mocker.patch("subprocess.run", side_effect=OSError("no permission"))

        warnings = transfer_with_exiftool(tmp_path / "src.jpg", tmp_path / "dst.jpg")

        assert any("no permission" in w for w in warnings)
