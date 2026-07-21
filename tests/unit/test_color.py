import pytest

from photo_border.core.color import parse_color
from photo_border.core.errors import InvalidColorError


class TestParseColor:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("#FFFFFF", (255, 255, 255)),
            ("#ffffff", (255, 255, 255)),
            ("#000000", (0, 0, 0)),
            ("#FF8800", (255, 136, 0)),
            ("white", (255, 255, 255)),
            ("black", (0, 0, 0)),
            ("255,255,255", (255, 255, 255)),
            ("10, 20, 30", (10, 20, 30)),
            ((10, 20, 30), (10, 20, 30)),
        ],
    )
    def test_valid_inputs(self, value, expected):
        assert parse_color(value) == expected

    @pytest.mark.parametrize(
        "value",
        [
            "#FFF",
            "#GGGGGG",
            "not-a-color",
            "300,0,0",
            "10,20",
            (10, 20, 300),
            (10, 20),
        ],
    )
    def test_invalid_inputs_raise(self, value):
        with pytest.raises(InvalidColorError):
            parse_color(value)
