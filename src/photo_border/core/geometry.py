from .errors import InvalidBorderConfigError
from .models import BorderConfig, BorderMode, CanvasPlan, ReferenceEdge

_ASPECT_MODES = (BorderMode.ASPECT, BorderMode.ASPECT_THEN_PERCENT)
_PERCENT_MODES = (BorderMode.PERCENT, BorderMode.ASPECT_THEN_PERCENT)


def calculate_canvas(src_size: tuple[int, int], config: BorderConfig) -> CanvasPlan:
    """依 BorderConfig 計算最終畫布尺寸與原圖貼上位置，純數字運算不碰像素。"""
    width, height = src_size

    if config.mode in _ASPECT_MODES:
        _validate_target_ratio(config.target_ratio)
        stage_width, stage_height, stage_off_x, stage_off_y = _apply_aspect(
            width, height, config.target_ratio
        )
    else:
        stage_width, stage_height, stage_off_x, stage_off_y = width, height, 0, 0

    if config.mode in _PERCENT_MODES:
        _validate_percent(config.percent)
        canvas_width, canvas_height, paste_x, paste_y = _apply_percent(
            stage_width, stage_height, stage_off_x, stage_off_y, config.percent, config.reference_edge
        )
    else:
        canvas_width, canvas_height = stage_width, stage_height
        paste_x, paste_y = stage_off_x, stage_off_y

    left, top = paste_x, paste_y
    right = canvas_width - width - left
    bottom = canvas_height - height - top

    return CanvasPlan(
        src_size=(width, height),
        canvas_size=(canvas_width, canvas_height),
        paste_offset=(paste_x, paste_y),
        border_px=(left, top, right, bottom),
    )


def _apply_aspect(
    width: int, height: int, target_ratio: tuple[int, int]
) -> tuple[int, int, int, int]:
    ratio_w, ratio_h = target_ratio

    if width * ratio_h > height * ratio_w:
        # 原圖比目標比例更「寬」，維持寬度，補高
        stage_width = width
        stage_height = round(width * ratio_h / ratio_w)
    elif width * ratio_h < height * ratio_w:
        # 原圖比目標比例更「高/窄」，維持高度，補寬
        stage_height = height
        stage_width = round(height * ratio_w / ratio_h)
    else:
        stage_width, stage_height = width, height

    off_x = (stage_width - width) // 2
    off_y = (stage_height - height) // 2
    return stage_width, stage_height, off_x, off_y


def _apply_percent(
    stage_width: int,
    stage_height: int,
    stage_off_x: int,
    stage_off_y: int,
    percent: float,
    reference_edge: ReferenceEdge,
) -> tuple[int, int, int, int]:
    reference_length = (
        min(stage_width, stage_height)
        if reference_edge == ReferenceEdge.SHORT
        else max(stage_width, stage_height)
    )
    border = round(reference_length * percent)

    canvas_width = stage_width + 2 * border
    canvas_height = stage_height + 2 * border
    paste_x = stage_off_x + border
    paste_y = stage_off_y + border
    return canvas_width, canvas_height, paste_x, paste_y


def _validate_target_ratio(target_ratio: tuple[int, int] | None) -> None:
    if target_ratio is None:
        raise InvalidBorderConfigError("aspect 模式需要提供 target_ratio")
    ratio_w, ratio_h = target_ratio
    if ratio_w <= 0 or ratio_h <= 0:
        raise InvalidBorderConfigError(f"target_ratio 必須為正數: {target_ratio}")


def _validate_percent(percent: float | None) -> None:
    if percent is None:
        raise InvalidBorderConfigError("percent 模式需要提供 percent")
    if percent < 0:
        raise InvalidBorderConfigError(f"percent 不可為負數: {percent}")
