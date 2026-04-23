import io
from dataclasses import dataclass
import pikepdf
from PIL import Image
from pikepdf import PdfImage, Name

# 以 Letter 尺寸估算頁面像素上限（8.5 × 11 英吋）
_PAGE_W_IN = 8.5
_PAGE_H_IN = 11.0

# 無法安全重新編碼的圖片格式（不處理）
_SKIP_FILTERS = ("JBIG2", "CCITTFax", "JPXDecode")


@dataclass
class ImageInfo:
    """PDF 內嵌圖片的資訊"""
    width: int
    height: int
    dpi: float  # 估算的 DPI（基於 Letter 尺寸）
    color_mode: str
    size_bytes: int
    will_be_resampled: bool  # 是否會被重採樣


@dataclass
class PdfAnalysisResult:
    """PDF 圖片分析結果"""
    page_count: int
    total_images: int
    images: list[ImageInfo]
    dpi_distribution: dict[int, int]  # DPI → 數量


def analyze_pdf_images(input_path: str) -> PdfAnalysisResult:
    """
    分析 PDF 內嵌圖片的解析度資訊。

    Returns:
        PdfAnalysisResult 包含每張圖片的詳細資訊
    """
    images: list[ImageInfo] = []
    dpi_counts: dict[int, int] = {}

    with pikepdf.open(input_path) as pdf:
        page_count = len(pdf.pages)

        for page_num, page in enumerate(pdf.pages, 1):
            try:
                for _key, img_obj in page.images.items():
                    try:
                        info = _extract_image_info(img_obj, page, page_num)
                        if info:
                            images.append(info)
                            # 四捨五入 DPI 到整數以便統計
                            rounded_dpi = int(round(info.dpi))
                            dpi_counts[rounded_dpi] = dpi_counts.get(rounded_dpi, 0) + 1
                    except Exception:
                        pass
            except Exception:
                pass

    return PdfAnalysisResult(
        page_count=page_count,
        total_images=len(images),
        images=images,
        dpi_distribution=dpi_counts,
    )


def _extract_image_info(img_obj, page, page_num: int) -> ImageInfo | None:
    """提取單一圖片的資訊"""
    try:
        width = int(img_obj.get("/Width", 0))
        height = int(img_obj.get("/Height", 0))
        if width == 0 or height == 0:
            return None

        # 嘗試取得頁面實際尺寸來計算真實 DPI
        page_width_pt, page_height_pt = _get_page_size(page)

        # 計算圖片基於頁面尺寸的 DPI
        dpi_x = (width / page_width_pt) * 72 if page_width_pt > 0 else 0
        dpi_y = (height / page_height_pt) * 72 if page_height_pt > 0 else 0
        dpi = min(dpi_x, dpi_y)  # 取較低者

        # 顏色模式
        color_mode = _get_color_mode(img_obj)

        # 估算大小（壓縮前）
        size_bytes = width * height * _bytes_per_pixel(color_mode)

        # 檢查是否會被重採樣（基於 150 DPI 預設值）
        max_px_w = int(_PAGE_W_IN * 150)
        max_px_h = int(_PAGE_H_IN * 150)
        will_resample = width > max_px_w or height > max_px_h

        return ImageInfo(
            width=width,
            height=height,
            dpi=dpi,
            color_mode=color_mode,
            size_bytes=size_bytes,
            will_be_resampled=will_resample,
        )
    except Exception:
        return None


def _get_page_size(page) -> tuple[float, float]:
    """取得頁面尺寸（以 points 為單位）"""
    try:
        # 嘗試從 MediaBox 取得
        if "/MediaBox" in page:
            mb = page["/MediaBox"]
            return float(mb[2]), float(mb[3])  # width, height
    except Exception:
        pass
    # 預設 Letter 尺寸
    return 612.0, 792.0  # 8.5" × 11" × 72 dpi


def _get_color_mode(img_obj) -> str:
    """判斷圖片顏色模式"""
    try:
        cs = img_obj.get("/ColorSpace", "")
        cs_str = str(cs)

        if "/DeviceGray" in cs_str or "/CalGray" in cs_str:
            return "L"
        elif "/DeviceRGB" in cs_str or "/CalRGB" in cs_str or "/DeviceCMYK" in cs_str:
            return "RGB"
        elif "/Indexed" in cs_str:
            return "P"
        return "RGB"
    except Exception:
        return "RGB"


def _bytes_per_pixel(mode: str) -> int:
    """每像素位元組數"""
    return {"L": 1, "RGB": 3, "CMYK": 4, "P": 3}.get(mode, 3)


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
