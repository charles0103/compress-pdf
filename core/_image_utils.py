from PIL import Image

# 16:9 寬螢幕投影片長邊約 13.33 英寸，用於 DPI → 最大像素換算
_SLIDE_LONG_INCH = 13.33


def dpi_to_max_px(target_dpi: int) -> int:
    """將目標 DPI 換算為投影片長邊最大像素數（16:9 寬螢幕基準）。"""
    return int(target_dpi * _SLIDE_LONG_INCH)


def resample_by_dpi(img: Image.Image, target_dpi: int) -> Image.Image:
    """依 DPI metadata 降採樣，適用於帶可靠 DPI 資訊的 JPG。"""
    dpi_info = img.info.get("dpi") or img.info.get("DPI")
    if isinstance(dpi_info, (tuple, list)):
        current_dpi = float(dpi_info[0]) or 72.0
    elif isinstance(dpi_info, (int, float)):
        current_dpi = float(dpi_info)
    else:
        current_dpi = 72.0

    if current_dpi <= target_dpi:
        return img

    scale = target_dpi / current_dpi
    new_w = max(1, int(img.width * scale))
    new_h = max(1, int(img.height * scale))
    return img.resize((new_w, new_h), Image.LANCZOS)


def resample_by_max_px(img: Image.Image, max_long_side: int) -> Image.Image:
    """依像素尺寸降採樣，適用於無可靠 DPI metadata 的 PPTX 內嵌圖片。"""
    long_side = max(img.width, img.height)
    if long_side <= max_long_side:
        return img
    scale = max_long_side / long_side
    new_w = max(1, int(img.width * scale))
    new_h = max(1, int(img.height * scale))
    return img.resize((new_w, new_h), Image.LANCZOS)
