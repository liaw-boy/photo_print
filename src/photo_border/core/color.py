from .errors import InvalidColorError

_NAMED_COLORS = {
    "white": (255, 255, 255),
    "black": (0, 0, 0),
}


def parse_color(value: str | tuple[int, int, int]) -> tuple[int, int, int]:
    """把 hex 字串 / 具名顏色 / "r,g,b" 字串 / tuple 統一解析成 RGB tuple。"""
    if isinstance(value, tuple):
        return _validate_rgb(value)

    if not isinstance(value, str):
        raise InvalidColorError(f"不支援的顏色型別: {type(value)!r}")

    text = value.strip()

    if text.startswith("#"):
        return _parse_hex(text)

    lowered = text.lower()
    if lowered in _NAMED_COLORS:
        return _NAMED_COLORS[lowered]

    if "," in text:
        return _parse_csv(text)

    raise InvalidColorError(f"無法解析顏色: {value!r}")


def _parse_hex(text: str) -> tuple[int, int, int]:
    hex_part = text[1:]
    if len(hex_part) != 6:
        raise InvalidColorError(f"hex 顏色需為 6 碼: {text!r}")
    try:
        r = int(hex_part[0:2], 16)
        g = int(hex_part[2:4], 16)
        b = int(hex_part[4:6], 16)
    except ValueError as exc:
        raise InvalidColorError(f"無效的 hex 顏色: {text!r}") from exc
    return (r, g, b)


def _parse_csv(text: str) -> tuple[int, int, int]:
    parts = [p.strip() for p in text.split(",")]
    if len(parts) != 3:
        raise InvalidColorError(f"rgb 顏色需為 3 個數值: {text!r}")
    try:
        rgb = tuple(int(p) for p in parts)
    except ValueError as exc:
        raise InvalidColorError(f"無效的 rgb 顏色: {text!r}") from exc
    return _validate_rgb(rgb)


def _validate_rgb(rgb: tuple[int, ...]) -> tuple[int, int, int]:
    if len(rgb) != 3:
        raise InvalidColorError(f"rgb 需為 3 個數值: {rgb!r}")
    if not all(0 <= c <= 255 for c in rgb):
        raise InvalidColorError(f"rgb 數值需介於 0-255: {rgb!r}")
    return (rgb[0], rgb[1], rgb[2])
