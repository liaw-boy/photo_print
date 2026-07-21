class PhotoBorderError(Exception):
    """所有 core 例外的基底類別"""


class InvalidBorderConfigError(PhotoBorderError):
    """BorderConfig 參數不合法（缺必要欄位、數值超出範圍等）"""


class InvalidColorError(PhotoBorderError):
    """顏色字串無法解析"""


class UnsupportedFormatError(PhotoBorderError):
    """不支援的圖片格式"""
