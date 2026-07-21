import pytest
from PIL import Image
from typer.testing import CliRunner

from photo_border.cli.main import app, build_config
from photo_border.core.errors import InvalidBorderConfigError, InvalidColorError
from photo_border.core.models import BorderMode, ReferenceEdge

runner = CliRunner()


class TestBuildConfig:
    def test_basic_percent_config(self):
        config = build_config(
            mode="percent",
            percent=0.1,
            edge="short",
            ratio=None,
            color="#FFFFFF",
            format="keep",
            quality=95,
            no_metadata=False,
            metadata_backend="auto",
        )
        assert config.mode == BorderMode.PERCENT
        assert config.percent == 0.1
        assert config.reference_edge == ReferenceEdge.SHORT
        assert config.output_format is None
        assert config.keep_metadata is True

    def test_aspect_then_percent_with_ratio(self):
        config = build_config(
            mode="aspect-then-percent",
            percent=0.05,
            edge="long",
            ratio="4:5",
            color="black",
            format="png",
            quality=90,
            no_metadata=True,
            metadata_backend="piexif",
        )
        assert config.mode == BorderMode.ASPECT_THEN_PERCENT
        assert config.target_ratio == (4, 5)
        assert config.reference_edge == ReferenceEdge.LONG
        assert config.color == (0, 0, 0)
        assert config.output_format == "png"
        assert config.keep_metadata is False
        assert config.metadata_backend == "piexif"

    def test_invalid_mode_raises(self):
        with pytest.raises(InvalidBorderConfigError):
            build_config(
                mode="bogus",
                percent=0.1,
                edge="short",
                ratio=None,
                color="white",
                format="keep",
                quality=95,
                no_metadata=False,
                metadata_backend="auto",
            )

    def test_invalid_ratio_format_raises(self):
        with pytest.raises(InvalidBorderConfigError):
            build_config(
                mode="aspect",
                percent=None,
                edge="short",
                ratio="bad",
                color="white",
                format="keep",
                quality=95,
                no_metadata=False,
                metadata_backend="auto",
            )

    def test_invalid_color_raises(self):
        with pytest.raises(InvalidColorError):
            build_config(
                mode="percent",
                percent=0.1,
                edge="short",
                ratio=None,
                color="not-a-color",
                format="keep",
                quality=95,
                no_metadata=False,
                metadata_backend="auto",
            )


class TestCliSingleFile:
    def test_success_exit_code_zero(self, tmp_path):
        src = tmp_path / "photo.jpg"
        Image.new("RGB", (50, 40), (1, 2, 3)).save(src)
        dst_dir = tmp_path / "out"

        result = runner.invoke(
            app, [str(src), str(dst_dir), "--mode", "percent", "--percent", "0.1"]
        )

        assert result.exit_code == 0
        assert (dst_dir / "photo.jpg").exists()

    def test_missing_input_exit_code_two(self, tmp_path):
        result = runner.invoke(app, [str(tmp_path / "nope.jpg"), str(tmp_path / "out")])

        assert result.exit_code == 2

    def test_invalid_mode_argument_exit_code_two(self, tmp_path):
        src = tmp_path / "photo.jpg"
        Image.new("RGB", (50, 40), (1, 2, 3)).save(src)

        result = runner.invoke(app, [str(src), str(tmp_path / "out"), "--mode", "bogus"])

        assert result.exit_code == 2

    def test_output_format_changes_extension(self, tmp_path):
        src = tmp_path / "photo.jpg"
        Image.new("RGB", (50, 40), (1, 2, 3)).save(src)
        dst_dir = tmp_path / "out"

        result = runner.invoke(
            app,
            [str(src), str(dst_dir), "--percent", "0.1", "--format", "png"],
        )

        assert result.exit_code == 0
        assert (dst_dir / "photo.png").exists()


class TestCliBatch:
    def test_batch_success(self, tmp_path):
        input_dir = tmp_path / "in"
        input_dir.mkdir()
        Image.new("RGB", (30, 20), (1, 2, 3)).save(input_dir / "a.jpg")
        Image.new("RGB", (30, 20), (4, 5, 6)).save(input_dir / "b.jpg")
        output_dir = tmp_path / "out"

        result = runner.invoke(app, [str(input_dir), str(output_dir), "--percent", "0.1"])

        assert result.exit_code == 0
        assert (output_dir / "a.jpg").exists()
        assert (output_dir / "b.jpg").exists()

    def test_batch_partial_failure_exit_code_one(self, tmp_path):
        input_dir = tmp_path / "in"
        input_dir.mkdir()
        Image.new("RGB", (30, 20), (1, 2, 3)).save(input_dir / "good.jpg")
        (input_dir / "broken.jpg").write_bytes(b"not-an-image")
        output_dir = tmp_path / "out"

        result = runner.invoke(app, [str(input_dir), str(output_dir), "--percent", "0.1"])

        assert result.exit_code == 1

    def test_batch_recursive_preserves_structure(self, tmp_path):
        input_dir = tmp_path / "in"
        (input_dir / "sub").mkdir(parents=True)
        Image.new("RGB", (30, 20), (1, 2, 3)).save(input_dir / "sub" / "nested.jpg")
        output_dir = tmp_path / "out"

        result = runner.invoke(
            app, [str(input_dir), str(output_dir), "--percent", "0.1", "--recursive"]
        )

        assert result.exit_code == 0
        assert (output_dir / "sub" / "nested.jpg").exists()
