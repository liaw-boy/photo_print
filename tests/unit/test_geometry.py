import pytest

from photo_border.core.errors import InvalidBorderConfigError
from photo_border.core.geometry import calculate_canvas
from photo_border.core.models import BorderConfig, BorderMode, ReferenceEdge


class TestPercentMode:
    def test_square_image_short_edge_default(self):
        config = BorderConfig(mode=BorderMode.PERCENT, percent=0.1)
        plan = calculate_canvas((1000, 1000), config)

        assert plan.src_size == (1000, 1000)
        assert plan.canvas_size == (1200, 1200)
        assert plan.paste_offset == (100, 100)
        assert plan.border_px == (100, 100, 100, 100)

    def test_landscape_image_uses_short_edge_by_default(self):
        config = BorderConfig(mode=BorderMode.PERCENT, percent=0.05)
        plan = calculate_canvas((4000, 3000), config)

        # 短邊 3000 * 0.05 = 150
        assert plan.canvas_size == (4300, 3300)
        assert plan.paste_offset == (150, 150)
        assert plan.border_px == (150, 150, 150, 150)

    def test_reference_edge_long(self):
        config = BorderConfig(
            mode=BorderMode.PERCENT, percent=0.05, reference_edge=ReferenceEdge.LONG
        )
        plan = calculate_canvas((4000, 3000), config)

        # 長邊 4000 * 0.05 = 200
        assert plan.canvas_size == (4400, 3400)
        assert plan.paste_offset == (200, 200)

    def test_portrait_image_short_edge(self):
        config = BorderConfig(mode=BorderMode.PERCENT, percent=0.1)
        plan = calculate_canvas((3000, 4000), config)

        # 短邊 3000 * 0.1 = 300
        assert plan.canvas_size == (3600, 4600)
        assert plan.paste_offset == (300, 300)

    def test_percent_zero_means_no_border(self):
        config = BorderConfig(mode=BorderMode.PERCENT, percent=0.0)
        plan = calculate_canvas((1000, 800), config)

        assert plan.canvas_size == (1000, 800)
        assert plan.border_px == (0, 0, 0, 0)

    def test_missing_percent_raises(self):
        config = BorderConfig(mode=BorderMode.PERCENT, percent=None)
        with pytest.raises(InvalidBorderConfigError):
            calculate_canvas((1000, 800), config)

    def test_negative_percent_raises(self):
        config = BorderConfig(mode=BorderMode.PERCENT, percent=-0.1)
        with pytest.raises(InvalidBorderConfigError):
            calculate_canvas((1000, 800), config)


class TestAspectMode:
    def test_landscape_to_square(self):
        config = BorderConfig(mode=BorderMode.ASPECT, target_ratio=(1, 1))
        plan = calculate_canvas((4000, 3000), config)

        assert plan.canvas_size == (4000, 4000)
        assert plan.paste_offset == (0, 500)
        assert plan.border_px == (0, 500, 0, 500)

    def test_landscape_to_portrait_4_5(self):
        config = BorderConfig(mode=BorderMode.ASPECT, target_ratio=(4, 5))
        plan = calculate_canvas((4000, 3000), config)

        # target ratio 4:5，寬固定，需要補高到 4000*5/4 = 5000
        assert plan.canvas_size == (4000, 5000)
        assert plan.paste_offset == (0, 1000)
        assert plan.border_px == (0, 1000, 0, 1000)

    def test_portrait_to_landscape(self):
        config = BorderConfig(mode=BorderMode.ASPECT, target_ratio=(3, 2))
        plan = calculate_canvas((2000, 3000), config)

        # target ratio 3:2（寬:高），原圖是直的，需要補寬到 3000*3/2 = 4500
        assert plan.canvas_size == (4500, 3000)
        assert plan.paste_offset == (1250, 0)
        assert plan.border_px == (1250, 0, 1250, 0)

    def test_already_matching_ratio_no_border(self):
        config = BorderConfig(mode=BorderMode.ASPECT, target_ratio=(4, 3))
        plan = calculate_canvas((4000, 3000), config)

        assert plan.canvas_size == (4000, 3000)
        assert plan.border_px == (0, 0, 0, 0)

    def test_odd_difference_splits_with_remainder_on_bottom_right(self):
        config = BorderConfig(mode=BorderMode.ASPECT, target_ratio=(1, 1))
        plan = calculate_canvas((1001, 1000), config)

        assert plan.canvas_size == (1001, 1001)
        # diff = 1 -> off = 1//2 = 0, remainder 1 落在 bottom
        assert plan.paste_offset == (0, 0)
        assert plan.border_px == (0, 0, 0, 1)

    def test_missing_target_ratio_raises(self):
        config = BorderConfig(mode=BorderMode.ASPECT, target_ratio=None)
        with pytest.raises(InvalidBorderConfigError):
            calculate_canvas((4000, 3000), config)

    def test_invalid_target_ratio_raises(self):
        config = BorderConfig(mode=BorderMode.ASPECT, target_ratio=(0, 5))
        with pytest.raises(InvalidBorderConfigError):
            calculate_canvas((4000, 3000), config)


class TestAspectThenPercentMode:
    def test_combo_applies_percent_on_top_of_aspect_canvas(self):
        config = BorderConfig(
            mode=BorderMode.ASPECT_THEN_PERCENT,
            target_ratio=(1, 1),
            percent=0.05,
        )
        plan = calculate_canvas((4000, 3000), config)

        # Stage 1 (aspect): 4000x4000, offset (0, 500)
        # Stage 2 (percent): 短邊(取 stage 尺寸的短邊 4000) * 0.05 = 200
        assert plan.canvas_size == (4400, 4400)
        assert plan.paste_offset == (200, 700)
        assert plan.border_px == (200, 700, 200, 700)

    def test_combo_requires_both_percent_and_ratio(self):
        config = BorderConfig(mode=BorderMode.ASPECT_THEN_PERCENT, target_ratio=(1, 1))
        with pytest.raises(InvalidBorderConfigError):
            calculate_canvas((4000, 3000), config)

        config2 = BorderConfig(mode=BorderMode.ASPECT_THEN_PERCENT, percent=0.05)
        with pytest.raises(InvalidBorderConfigError):
            calculate_canvas((4000, 3000), config2)
