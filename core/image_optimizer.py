import io
import pikepdf
from PIL import Image
from pikepdf import PdfImage, Name

# 以 Letter 尺寸估算頁面像素上限（8.5 × 11 英吋）
_PAGE_W_IN = 8.5
_PAGE_H_IN = 11.0

# 無法安全重新編碼的圖片格式（不處理）
_SKIP_FILTERS = ("JBIG2", "CCITTFax", "JPXDecode")


def optimize_images(
    input_path: str,
    output_path: str,
    dpi: int = 150,
    quality: int = 75,
    grayscale: bool = False,
) -> None:
    """
    以 pikepdf + Pillow 重採樣 PDF 內嵌圖片。
    向量圖形與文字不受影響。
    """
    with pikepdf.open(input_path) as pdf:
        _walk_images(pdf, dpi, quality, grayscale)
        pdf.save(
            output_path,
            compress_streams=True,
            object_stream_mode=pikepdf.ObjectStreamMode.generate,
        )


def _walk_images(pdf, dpi, quality, grayscale):
    seen: set = set()
    for page in pdf.pages:
        try:
            for _key, img_obj in page.images.items():
                try:
                    oid = img_obj.objgen
                except Exception:
                    oid = id(img_obj)
                if oid in seen:
                    continue
                seen.add(oid)
                try:
                    _try_compress(img_obj, dpi, quality, grayscale)
                except Exception:
                    pass  # 無法處理的圖片略過，不中斷整體壓縮
        except Exception:
            pass


def _try_compress(img_obj, dpi: int, quality: int, grayscale: bool) -> None:
    # 跳過圖片遮罩
    if img_obj.get("/ImageMask"):
        return

    # 跳過無法可靠重新編碼的格式
    filt = img_obj.get("/Filter")
    if filt is not None:
        if any(s in str(filt) for s in _SKIP_FILTERS):
            return

    width = int(img_obj.get("/Width", 0))
    height = int(img_obj.get("/Height", 0))
    if width == 0 or height == 0:
        return

    # 計算縮放比例（只在超出目標 DPI 時縮小）
    max_w = int(_PAGE_W_IN * dpi)
    max_h = int(_PAGE_H_IN * dpi)
    scale = min(
        max_w / width  if width  > max_w else 1.0,
        max_h / height if height > max_h else 1.0,
    )

    if scale >= 1.0 and not grayscale:
        return  # 尺寸已夠小且不需灰階轉換，略過

    # 用 pikepdf PdfImage 取得 PIL Image（自動處理各種 colorspace/filter）
    try:
        pil_img = PdfImage(img_obj).as_pil_image()
    except Exception:
        return

    # 統一轉為 RGB 或 L（確保 JPEG 相容）
    if pil_img.mode == "CMYK":
        pil_img = pil_img.convert("RGB")
    elif pil_img.mode in ("RGBA", "LA", "P"):
        pil_img = pil_img.convert("RGB")

    if grayscale:
        pil_img = pil_img.convert("L")
    elif pil_img.mode not in ("RGB", "L"):
        pil_img = pil_img.convert("RGB")

    # 縮放
    if scale < 1.0:
        new_w = max(1, int(width * scale))
        new_h = max(1, int(height * scale))
        pil_img = pil_img.resize((new_w, new_h), Image.LANCZOS)
    else:
        new_w, new_h = pil_img.size

    # 編碼為 JPEG
    buf = io.BytesIO()
    pil_img.save(buf, format="JPEG", quality=quality, optimize=True)
    jpeg_bytes = buf.getvalue()

    # 寫回 PDF：write() 同時更新串流資料與 /Filter，不會造成字典不一致
    colorspace = Name("/DeviceGray") if pil_img.mode == "L" else Name("/DeviceRGB")
    img_obj.write(jpeg_bytes, filter=Name("/DCTDecode"))
    img_obj["/Width"] = new_w
    img_obj["/Height"] = new_h
    img_obj["/ColorSpace"] = colorspace
    img_obj["/BitsPerComponent"] = 8

    # 移除與 DCTDecode 衝突的舊有解碼參數
    for key in ("/DecodeParms", "/Intent"):
        if key in img_obj:
            del img_obj[key]
