import os
import tempfile
import threading
from dataclasses import dataclass, field
from typing import Callable

from core.lossless import compress_lossless
from core.image_optimizer import optimize_images, analyze_pdf_images, PdfAnalysisResult
from core.jpg_compressor import compress_jpg
from core.pptx_compressor import compress_pptx
from utils.file_utils import default_output_path, preserve_timestamps

_JPG_EXTS = {".jpg", ".jpeg"}
_PPTX_EXT = ".pptx"
_LEGACY_PPT_EXT = ".ppt"


@dataclass
class CompressOptions:
    mode: int = 1              # 1=無失真, 2=圖片優化, 3=高壓縮
    level: int = 9             # flate 壓縮等級 1-9
    dpi: int = 150             # 圖片目標 DPI（模式 2/3 有效）
    quality: int = 75          # JPEG 品質 50-95（模式 3 有效）
    output_dir: str = ""         # 空字串代表與輸入同目錄
    preserve_dates: bool = True  # 保留原始檔案建立/修改日期
    keep_filename: bool = False  # 保留原始檔名（輸出至 compressed/ 子資料夾）


@dataclass
class CompressResult:
    input_path: str
    output_path: str
    size_before: int
    size_after: int
    success: bool
    error: str = ""


def compress_file(
    input_path: str,
    opts: CompressOptions,
) -> CompressResult:
    output_path = default_output_path(
        input_path,
        opts.output_dir or None,
        keep_filename=opts.keep_filename,
    )
    size_before = os.path.getsize(input_path)

    ext = os.path.splitext(input_path)[1].lower()

    try:
        if ext in _JPG_EXTS:
            compress_jpg(input_path, output_path, opts.mode, opts.dpi, opts.quality)
        elif ext == _PPTX_EXT:
            compress_pptx(input_path, output_path, opts.mode, opts.dpi, opts.quality)
        elif ext == _LEGACY_PPT_EXT:
            raise ValueError("不支援舊版 .ppt，請在 PowerPoint 中另存為 .pptx 後再壓縮")
        elif opts.mode == 1:
            compress_lossless(input_path, output_path, opts.level)
        elif opts.mode == 2:
            _compress_image_optimized(input_path, output_path, opts)
        else:
            _compress_aggressive(input_path, output_path, opts)

        if opts.preserve_dates and os.path.exists(output_path):
            preserve_timestamps(input_path, output_path)

        size_after = os.path.getsize(output_path)
        return CompressResult(input_path, output_path, size_before, size_after, True)

    except Exception as exc:
        return CompressResult(input_path, output_path, size_before, 0, False, str(exc))


def _compress_image_optimized(
    input_path: str, output_path: str, opts: CompressOptions
) -> None:
    """模式 2：只降採樣超過目標 DPI 的圖片，品質保持高（95）以無感壓縮。"""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        optimize_images(
            input_path, tmp_path,
            dpi=opts.dpi,
            quality=95,
            force_recompress=False,
        )
        compress_lossless(tmp_path, output_path, opts.level)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _compress_aggressive(
    input_path: str, output_path: str, opts: CompressOptions
) -> None:
    """模式 3：所有圖片一律以使用者指定的品質重編碼，超過 DPI 的再加降採樣。"""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        optimize_images(
            input_path, tmp_path,
            dpi=opts.dpi,
            quality=opts.quality,
            force_recompress=True,
        )
        compress_lossless(tmp_path, output_path, opts.level)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def analyze_file(input_path: str) -> PdfAnalysisResult | None:
    """分析 PDF 檔案的圖片解析度資訊"""
    if not os.path.isfile(input_path):
        return None
    try:
        return analyze_pdf_images(input_path)
    except Exception:
        return None


def compress_batch(
    file_paths: list[str],
    opts: CompressOptions,
    on_progress: Callable[[int, int, CompressResult], None],
    on_done: Callable[[list[CompressResult]], None],
) -> threading.Thread:
    """在背景執行緒批次壓縮，每完成一個檔案呼叫 on_progress，全部完成後呼叫 on_done。"""

    def run():
        results = []
        total = len(file_paths)
        for i, path in enumerate(file_paths):
            result = compress_file(path, opts)
            results.append(result)
            on_progress(i + 1, total, result)
        on_done(results)

    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t
