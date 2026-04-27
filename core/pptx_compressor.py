import io
import zipfile
from PIL import Image

_JPEG_EXTS = (".jpg", ".jpeg")
_PNG_EXT = ".png"
_MEDIA_PREFIX = "ppt/media/"


def compress_pptx(input_path: str, output_path: str, mode: int, dpi: int, quality: int) -> None:
    """PPTX 壓縮：拆 ZIP → 重壓 ppt/media/ 下的圖片 → 重新打包"""
    with zipfile.ZipFile(input_path, "r") as zin:
        with zipfile.ZipFile(
            output_path, "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if _should_recompress(item.filename, mode):
                    data = _recompress_image(data, item.filename, mode, dpi, quality)
                new_info = zipfile.ZipInfo(
                    filename=item.filename,
                    date_time=item.date_time,
                )
                new_info.external_attr = item.external_attr
                zout.writestr(new_info, data)


def _should_recompress(filename: str, mode: int) -> bool:
    if mode == 1:
        return False
    if not filename.startswith(_MEDIA_PREFIX):
        return False
    lower = filename.lower()
    return lower.endswith(_JPEG_EXTS) or lower.endswith(_PNG_EXT)


def _recompress_image(data: bytes, filename: str, mode: int, target_dpi: int, quality: int) -> bytes:
    """重壓單張圖片，若失敗或結果變大則保留原始 bytes"""
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
        is_png = filename.lower().endswith(_PNG_EXT)

        img = _maybe_resample(img, target_dpi)

        buf = io.BytesIO()
        if is_png:
            img.save(buf, "PNG", optimize=True)
        else:
            if img.mode in ("RGBA", "P", "LA"):
                img = img.convert("RGB")
            out_quality = quality if mode == 3 else 92
            save_kwargs = {"quality": out_quality, "optimize": True}
            exif = img.info.get("exif", b"")
            if exif:
                save_kwargs["exif"] = exif
            img.save(buf, "JPEG", **save_kwargs)

        new_data = buf.getvalue()
        return new_data if len(new_data) < len(data) else data
    except Exception:
        return data


def _maybe_resample(img: Image.Image, target_dpi: int) -> Image.Image:
    """若圖片 DPI 超過目標則降採樣"""
    dpi_info = img.info.get("dpi")
    if isinstance(dpi_info, (tuple, list)):
        current_dpi = float(dpi_info[0]) or 72.0
    else:
        current_dpi = 72.0
    if current_dpi <= target_dpi:
        return img
    scale = target_dpi / current_dpi
    new_w = max(1, int(img.width * scale))
    new_h = max(1, int(img.height * scale))
    return img.resize((new_w, new_h), Image.LANCZOS)


def analyze_pptx(input_path: str) -> dict:
    """分析 PPTX 內的媒體圖片統計"""
    jpeg_count = 0
    png_count = 0
    other_count = 0
    total_media_bytes = 0

    with zipfile.ZipFile(input_path, "r") as z:
        for item in z.infolist():
            if not item.filename.startswith(_MEDIA_PREFIX):
                continue
            lower = item.filename.lower()
            total_media_bytes += item.file_size
            if lower.endswith(_JPEG_EXTS):
                jpeg_count += 1
            elif lower.endswith(_PNG_EXT):
                png_count += 1
            else:
                other_count += 1

    return {
        "jpeg": jpeg_count,
        "png": png_count,
        "other": other_count,
        "total_media_bytes": total_media_bytes,
    }
