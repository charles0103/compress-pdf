from __future__ import annotations

from PIL import Image


def compress_jpg(input_path: str, output_path: str, mode: int, dpi: int, quality: int) -> None:
    """
    壓縮單張 JPEG 圖檔。

    mode 1：最佳化重編碼（quality=92），不降採樣
    mode 2：若原始 DPI 超過目標則降採樣，quality=92
    mode 3：強制以指定 quality 重編碼，超過目標 DPI 的一併降採樣
    """
    img = Image.open(input_path)

    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")

    img = _maybe_resample(img, mode, dpi)

    out_quality = quality if mode == 3 else 92
    exif = img.info.get("exif", b"")

    save_kwargs: dict = {"quality": out_quality, "optimize": True}
    if exif:
        save_kwargs["exif"] = exif

    img.save(output_path, "JPEG", **save_kwargs)


def _maybe_resample(img: Image.Image, mode: int, target_dpi: int) -> Image.Image:
    if mode == 1:
        return img

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
