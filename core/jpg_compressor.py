from __future__ import annotations

from PIL import Image
from core._image_utils import resample_by_dpi


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

    if mode >= 2:
        img = resample_by_dpi(img, dpi)

    out_quality = quality if mode == 3 else 92
    exif = img.info.get("exif", b"")

    save_kwargs: dict = {"quality": out_quality, "optimize": True}
    if exif:
        save_kwargs["exif"] = exif

    img.save(output_path, "JPEG", **save_kwargs)

