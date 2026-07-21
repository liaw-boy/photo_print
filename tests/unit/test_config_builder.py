import pytest

from photo_border.core.config_builder import build_border_config
from photo_border.core.errors import InvalidBorderConfigError, InvalidColorError
from photo_border.core.models import BorderMode, ReferenceEdge


class TestBuildBorderConfig:
    def test_basic_percent_config(self):
        config = build_border_config(
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
        config = build_border_config(
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

    def test_accepts_rgb_tuple_color(self):
        config = build_border_config(
            mode="percent",
            percent=0.1,
            edge="short",
            ratio=None,
            color=(10, 20, 30),
            format="keep",
            quality=95,
            no_metadata=False,
            metadata_backend="auto",
        )
        assert config.color == (10, 20, 30)

    def test_invalid_mode_raises(self):
        with pytest.raises(InvalidBorderConfigError):
            build_border_config(
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
            build_border_config(
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
            build_border_config(
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
