import io
import math
from dataclasses import dataclass
import pikepdf
from PIL import Image
from pikepdf import PdfImage, Name

# 嘗試載入 pikepdf 官方 CTM 工具（pikepdf 8.x/9.x 可能不同）
try:
    from pikepdf.models.ctm import get_objects_with_ctm as _pike_get_ctm
    _HAS_CTM_API = True
except Exception:
    _HAS_CTM_API = False

# 無法安全重新編碼的圖片格式（不處理）
_SKIP_FILTERS = ("JBIG2", "CCITTFax", "JPXDecode")

# 低於此像素尺寸的圖片視為 icon，不做 JPEG 重編碼（重編反而變大）
_MIN_RECOMPRESS_PX = 64


@dataclass
class ImageInfo:
    """PDF 內嵌圖片的資訊"""
    width: int
    height: int
    dpi: float
    color_mode: str
    size_bytes: int
    will_be_resampled: bool


@dataclass
class PdfAnalysisResult:
    """PDF 圖片分析結果"""
    page_count: int
    total_images: int
    images: list[ImageInfo]
    dpi_distribution: dict[int, int]


# ── 頁面 / CTM 尺寸收集 ──────────────────────────────────────────

def _page_mediabox_pt(page) -> tuple[float, float]:
    """回傳頁面 mediabox 尺寸 (width_pt, height_pt)，fallback 為 Letter。"""
    try:
        mb = page.mediabox
        w = float(mb[2]) - float(mb[0])
        h = float(mb[3]) - float(mb[1])
        if w > 0 and h > 0:
            return w, h
    except Exception:
        pass
    return 612.0, 792.0  # Letter


def _ctm_display_size(matrix) -> tuple[float, float]:
    """從 CTM 矩陣計算圖片在頁面上的顯示尺寸（points），處理旋轉。"""
    # PDF 圖片 XObject 預設為 1x1 單位方塊，經 CTM 縮放後得顯示尺寸
    # 寬 = |(a, b)|，高 = |(c, d)|（將旋轉也納入）
    try:
        a, b, c, d = float(matrix.a), float(matrix.b), float(matrix.c), float(matrix.d)
    except Exception:
        return 0.0, 0.0
    return math.hypot(a, b), math.hypot(c, d)


def _collect_display_sizes(pdf) -> dict:
    """
    掃描整份 PDF，回傳每張圖片的最大顯示尺寸。
    Returns: {objgen: (max_w_pt, max_h_pt)}

    同一張圖片多處引用時取最大顯示尺寸，避免降採樣過度讓大引用模糊。
    若某張圖片的 CTM 無法取得（Form XObject 巢狀等），fallback 到 page mediabox。
    """
    sizes: dict = {}

    for page in pdf.pages:
        # page 內 XObject 名稱 → objgen 映射
        name_to_oid: dict = {}
        try:
            for name, img_obj in page.images.items():
                try:
                    name_to_oid[str(name)] = img_obj.objgen
                except Exception:
                    pass
        except Exception:
            continue

        if not name_to_oid:
            continue

        # 取 CTM 資料（若 API 可用）
        ctm_sizes: dict = {}  # name -> (w, h)
        if _HAS_CTM_API:
            try:
                for entry in _pike_get_ctm(page):
                    try:
                        obj_name, matrix = entry[0], entry[1]
                    except Exception:
                        continue
                    w, h = _ctm_display_size(matrix)
                    if w <= 0 or h <= 0:
                        continue
                    key = str(obj_name)
                    prev = ctm_sizes.get(key)
                    if prev is None:
                        ctm_sizes[key] = (w, h)
                    else:
                        ctm_sizes[key] = (max(prev[0], w), max(prev[1], h))
            except Exception:
                pass

        mb_fallback = _page_mediabox_pt(page)

        # 合併到全域 sizes
        for name, oid in name_to_oid.items():
            w, h = ctm_sizes.get(name, mb_fallback)
            prev = sizes.get(oid)
            if prev is None:
                sizes[oid] = (w, h)
            else:
                sizes[oid] = (max(prev[0], w), max(prev[1], h))

    return sizes


# ── 分析 API ─────────────────────────────────────────────────────

def analyze_pdf_images(input_path: str) -> PdfAnalysisResult:
    """分析 PDF 內嵌圖片的解析度資訊（基於 CTM 的精確 DPI）。"""
    images: list[ImageInfo] = []
    dpi_counts: dict[int, int] = {}

    with pikepdf.open(input_path) as pdf:
        page_count = len(pdf.pages)
        display_sizes = _collect_display_sizes(pdf)

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
                        display_pt = display_sizes.get(oid) or _page_mediabox_pt(page)
                        info = _extract_image_info(img_obj, display_pt)
                        if info:
                            images.append(info)
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


def _extract_image_info(img_obj, display_pt: tuple[float, float]) -> ImageInfo | None:
    """提取單一圖片的資訊（DPI 以實際顯示尺寸計算）。"""
    try:
        width = int(img_obj.get("/Width", 0))
        height = int(img_obj.get("/Height", 0))
        if width == 0 or height == 0:
            return None

        display_w_pt, display_h_pt = display_pt
        if display_w_pt > 0 and display_h_pt > 0:
            dpi_x = width  * 72.0 / display_w_pt
            dpi_y = height * 72.0 / display_h_pt
            dpi = min(dpi_x, dpi_y)
        else:
            dpi = 0.0

        color_mode = _get_color_mode(img_obj)
        size_bytes = width * height * _bytes_per_pixel(color_mode)

        # 以 150 DPI 為基準判斷「預設會不會被重採樣」
        will_resample = dpi > 150.0

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


def _get_color_mode(img_obj) -> str:
    try:
        cs = img_obj.get("/ColorSpace", "")
        cs_str = str(cs)
        if "/DeviceGray" in cs_str or "/CalGray" in cs_str:
            return "L"
        if "/DeviceCMYK" in cs_str:
            return "CMYK"
        if "/DeviceRGB" in cs_str or "/CalRGB" in cs_str:
            return "RGB"
        if "/Indexed" in cs_str:
            return "P"
        return "RGB"
    except Exception:
        return "RGB"


def _bytes_per_pixel(mode: str) -> int:
    return {"L": 1, "RGB": 3, "CMYK": 4, "P": 3}.get(mode, 3)


# ── 壓縮 API ─────────────────────────────────────────────────────

def optimize_images(
    input_path: str,
    output_path: str,
    dpi: int = 150,
    quality: int = 75,
    grayscale: bool = False,
    force_recompress: bool = False,
) -> None:
    """
    以 pikepdf + Pillow 重採樣 PDF 內嵌圖片。

    Args:
        dpi: 目標 DPI；effective_dpi 超過此值時才降採樣
        quality: JPEG 品質（50-95）
        grayscale: 是否強制轉灰階
        force_recompress: 即使不需降採樣也以 JPEG 重編碼（讓 quality 對所有圖生效）
    """
    with pikepdf.open(input_path) as pdf:
        display_sizes = _collect_display_sizes(pdf)
        _walk_images(pdf, display_sizes, dpi, quality, grayscale, force_recompress)
        pdf.save(
            output_path,
            compress_streams=True,
            object_stream_mode=pikepdf.ObjectStreamMode.generate,
        )


def _walk_images(pdf, display_sizes, dpi, quality, grayscale, force_recompress):
    seen: set = set()
    for page in pdf.pages:
        mb_fallback = _page_mediabox_pt(page)
        try:
            for _key, img_obj in page.images.items():
                try:
                    oid = img_obj.objgen
                except Exception:
                    oid = id(img_obj)
                if oid in seen:
                    continue
                seen.add(oid)
                display_pt = display_sizes.get(oid) or mb_fallback
                try:
                    _try_compress(
                        img_obj, display_pt,
                        dpi, quality, grayscale, force_recompress,
                    )
                except Exception:
                    pass
        except Exception:
            pass


def _try_compress(
    img_obj,
    display_pt: tuple[float, float],
    target_dpi: int,
    quality: int,
    grayscale: bool,
    force_recompress: bool,
) -> None:
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

    # 最小尺寸門檻：過小的 icon 重編 JPEG 可能變更大
    if width < _MIN_RECOMPRESS_PX and height < _MIN_RECOMPRESS_PX:
        return

    display_w_pt, display_h_pt = display_pt
    if display_w_pt <= 0 or display_h_pt <= 0:
        return

    # 基於實際顯示尺寸計算 effective DPI
    effective_dpi = min(
        width  * 72.0 / display_w_pt,
        height * 72.0 / display_h_pt,
    )

    # 僅當 effective_dpi 超過目標才降採樣
    scale = (target_dpi / effective_dpi) if effective_dpi > target_dpi else 1.0

    need_resize = scale < 1.0
    need_recompress = force_recompress or grayscale

    if not (need_resize or need_recompress):
        return

    try:
        pil_img = PdfImage(img_obj).as_pil_image()
    except Exception:
        return

    # 統一色彩空間（確保 JPEG 相容）
    if pil_img.mode == "CMYK":
        pil_img = pil_img.convert("RGB")
    elif pil_img.mode in ("RGBA", "LA", "P"):
        pil_img = pil_img.convert("RGB")

    if grayscale:
        pil_img = pil_img.convert("L")
    elif pil_img.mode not in ("RGB", "L"):
        pil_img = pil_img.convert("RGB")

    if need_resize:
        new_w = max(1, int(width * scale))
        new_h = max(1, int(height * scale))
        pil_img = pil_img.resize((new_w, new_h), Image.LANCZOS)
    else:
        new_w, new_h = pil_img.size

    buf = io.BytesIO()
    pil_img.save(buf, format="JPEG", quality=quality, optimize=True)
    jpeg_bytes = buf.getvalue()

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
