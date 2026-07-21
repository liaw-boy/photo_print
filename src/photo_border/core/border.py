from PIL import Image

from .models import CanvasPlan


def apply_border(
    image: Image.Image, plan: CanvasPlan, color: tuple[int, int, int]
) -> Image.Image:
    """依 CanvasPlan 建立留白畫布並貼上原圖，回傳新影像，不修改輸入的 image。"""
    canvas_color = _convert_color_to_mode(color, image.mode)
    canvas = Image.new(image.mode, plan.canvas_size, canvas_color)
    canvas.paste(image, plan.paste_offset)
    return canvas


def _convert_color_to_mode(color: tuple[int, int, int], mode: str):
    if mode == "RGB":
        return color
    if mode == "RGBA":
        return (*color, 255)
    # 其他 mode（L、CMYK 等）借助 Pillow 自身的色彩轉換規則
    sample = Image.new("RGB", (1, 1), color).convert(mode)
    return sample.getpixel((0, 0))
