from .color import parse_color
from .errors import InvalidBorderConfigError
from .models import BorderConfig, BorderMode, ReferenceEdge

MODE_CHOICES = {
    "percent": BorderMode.PERCENT,
    "aspect": BorderMode.ASPECT,
    "aspect-then-percent": BorderMode.ASPECT_THEN_PERCENT,
}
EDGE_CHOICES = {
    "long": ReferenceEdge.LONG,
    "short": ReferenceEdge.SHORT,
}


def build_border_config(
    *,
    mode: str,
    percent: float | None,
    edge: str,
    ratio: str | None,
    color: str | tuple[int, int, int],
    format: str,
    quality: int,
    no_metadata: bool,
    metadata_backend: str,
) -> BorderConfig:
    """把字串/原生型別的參數（CLI 選項或網頁表單欄位）組成 BorderConfig。

    純函式、不依賴任何 UI 框架，cli 與 web 都呼叫同一份邏輯。
    """
    if mode not in MODE_CHOICES:
        raise InvalidBorderConfigError(
            f"未知的 mode: {mode!r}（可用值：{', '.join(MODE_CHOICES)}）"
        )
    if edge not in EDGE_CHOICES:
        raise InvalidBorderConfigError(f"未知的 edge: {edge!r}（可用值：long, short）")

    return BorderConfig(
        mode=MODE_CHOICES[mode],
        percent=percent,
        reference_edge=EDGE_CHOICES[edge],
        target_ratio=parse_ratio(ratio),
        color=parse_color(color),
        output_format=None if format == "keep" else format,
        jpeg_quality=quality,
        keep_metadata=not no_metadata,
        metadata_backend=metadata_backend,
    )


def parse_ratio(value: str | None) -> tuple[int, int] | None:
    if value is None:
        return None
    parts = value.split(":")
    if len(parts) != 2:
        raise InvalidBorderConfigError(f"ratio 需為 W:H 格式，例如 4:5，收到: {value!r}")
    try:
        return (int(parts[0]), int(parts[1]))
    except ValueError as exc:
        raise InvalidBorderConfigError(f"ratio 需為整數 W:H，收到: {value!r}") from exc
