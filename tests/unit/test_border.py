from PIL import Image

from photo_border.core.border import apply_border
from photo_border.core.geometry import calculate_canvas
from photo_border.core.models import BorderConfig, BorderMode


def _solid_image(size, color, mode="RGB"):
    return Image.new(mode, size, color)


class TestApplyBorderRGB:
    def test_output_size_matches_plan(self):
        src = _solid_image((100, 80), (10, 20, 30))
        config = BorderConfig(mode=BorderMode.PERCENT, percent=0.1)
        plan = calculate_canvas(src.size, config)

        result = apply_border(src, plan, config.color)

        assert result.size == plan.canvas_size

    def test_border_area_is_fill_color(self):
        src = _solid_image((100, 80), (10, 20, 30))
        config = BorderConfig(mode=BorderMode.PERCENT, percent=0.1, color=(255, 0, 0))
        plan = calculate_canvas(src.size, config)

        result = apply_border(src, plan, config.color)

        # 四個角落應該是邊框顏色
        assert result.getpixel((0, 0)) == (255, 0, 0)
        assert result.getpixel((result.width - 1, 0)) == (255, 0, 0)
        assert result.getpixel((0, result.height - 1)) == (255, 0, 0)
        assert result.getpixel((result.width - 1, result.height - 1)) == (255, 0, 0)

    def test_original_pixels_preserved_at_paste_offset(self):
        src = _solid_image((100, 80), (10, 20, 30))
        config = BorderConfig(mode=BorderMode.PERCENT, percent=0.1, color=(255, 0, 0))
        plan = calculate_canvas(src.size, config)

        result = apply_border(src, plan, config.color)

        ox, oy = plan.paste_offset
        assert result.getpixel((ox, oy)) == (10, 20, 30)
        assert result.getpixel((ox + src.width - 1, oy + src.height - 1)) == (10, 20, 30)

    def test_does_not_mutate_input_image(self):
        src = _solid_image((100, 80), (10, 20, 30))
        original_size = src.size
        original_pixel = src.getpixel((0, 0))
        config = BorderConfig(mode=BorderMode.PERCENT, percent=0.1)
        plan = calculate_canvas(src.size, config)

        apply_border(src, plan, config.color)

        assert src.size == original_size
        assert src.getpixel((0, 0)) == original_pixel

    def test_zero_border_returns_same_content(self):
        src = _solid_image((100, 80), (10, 20, 30))
        config = BorderConfig(mode=BorderMode.PERCENT, percent=0.0)
        plan = calculate_canvas(src.size, config)

        result = apply_border(src, plan, config.color)

        assert result.size == src.size
        assert result.getpixel((50, 40)) == (10, 20, 30)


class TestApplyBorderOtherModes:
    def test_rgba_image_border_gets_opaque_alpha(self):
        src = _solid_image((100, 80), (10, 20, 30, 200), mode="RGBA")
        config = BorderConfig(mode=BorderMode.PERCENT, percent=0.1, color=(255, 255, 255))
        plan = calculate_canvas(src.size, config)

        result = apply_border(src, plan, config.color)

        assert result.mode == "RGBA"
        assert result.getpixel((0, 0)) == (255, 255, 255, 255)

    def test_grayscale_image_border_uses_luminance(self):
        src = _solid_image((100, 80), 50, mode="L")
        config = BorderConfig(mode=BorderMode.PERCENT, percent=0.1, color=(255, 255, 255))
        plan = calculate_canvas(src.size, config)

        result = apply_border(src, plan, config.color)

        assert result.mode == "L"
        assert result.getpixel((0, 0)) == 255
