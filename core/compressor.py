import dataclasses
import concurrent.futures
import os
import tempfile
import threading
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Callable

from core.decrypt import decrypt_pdf, PasswordRequired, WrongPassword
from core.lossless import compress_lossless
from core.image_optimizer import optimize_images, analyze_pdf_images, PdfAnalysisResult
from core.jpg_compressor import compress_jpg
from core.pptx_compressor import compress_pptx
from utils.file_utils import default_output_path, preserve_timestamps

_JPG_EXTS = {".jpg", ".jpeg"}
_PPTX_EXT = ".pptx"
_LEGACY_PPT_EXT = ".ppt"

_MAX_PASSWORD_ATTEMPTS = 3

# 解密模式向 GUI 索取密碼的回呼：(檔名, 第幾次嘗試從 0 起算) -> 密碼字串；
# 回傳 None 代表使用者取消（該檔略過）。
PasswordProvider = Callable[[str, int], "str | None"]


def _decrypt_pdf_file(
    input_path: str,
    output_path: str,
    password_provider: "PasswordProvider | None",
) -> None:
    """解除 PDF 密碼。先試空密碼（涵蓋未加密與純權限密碼），
    需要 user 密碼時透過 password_provider 向 GUI 索取，最多重試數次。
    """
    try:
        decrypt_pdf(input_path, output_path, "")
        return
    except PasswordRequired:
        pass

    if password_provider is None:
        raise ValueError("此檔案需要開啟密碼")

    filename = os.path.basename(input_path)
    for attempt in range(_MAX_PASSWORD_ATTEMPTS):
        password = password_provider(filename, attempt)
        if password is None:
            raise ValueError("已略過（使用者取消密碼輸入）")
        try:
            decrypt_pdf(input_path, output_path, password)
            return
        except WrongPassword:
            continue
    raise ValueError("密碼錯誤，已達重試上限")


@dataclass
class CompressOptions:
    mode: int = 1              # 0=解除密碼, 1=無失真, 2=圖片優化, 3=高壓縮
    level: int = 9             # flate 壓縮等級 1-9
    dpi: int = 150             # 圖片目標 DPI（模式 2/3 有效）
    quality: int = 75          # JPEG 品質 50-95（模式 3 有效）
    output_dir: str = ""         # 空字串代表與輸入同目錄
    preserve_dates: bool = True  # 保留原始檔案建立/修改日期
    keep_filename: bool = False  # 保留原始檔名（輸出至 compressed/ 子資料夾）
    filename_template: str = ""  # 輸出檔名樣板，支援 {name} {date} {index}；空字串使用預設規則
    file_index: int = 1          # 樣板中 {index} 的值，由 compress_batch 自動設定  # 保留原始檔名（輸出至 compressed/ 子資料夾）


@dataclass
class CompressResult:
    input_path: str
    output_path: str
    size_before: int
    size_after: int
    success: bool
    error: str = ""
    elapsed: float = 0.0


def compress_file(
    input_path: str,
    opts: CompressOptions,
    password_provider: "PasswordProvider | None" = None,
) -> CompressResult:
    output_path = ""
    size_before = 0
    try:
        size_before = os.path.getsize(input_path)
        suffix = "_unlocked" if opts.mode == 0 else "_compressed"
        output_path = default_output_path(
            input_path,
            opts.output_dir or None,
            keep_filename=opts.keep_filename,
            filename_template=opts.filename_template,
            file_index=opts.file_index,
            default_suffix=suffix,
        )
    except PermissionError as exc:
        return CompressResult(input_path, "", size_before, 0, False, f"存取被拒：{exc}")
    except Exception as exc:
        return CompressResult(input_path, "", size_before, 0, False, str(exc))

    ext = os.path.splitext(input_path)[1].lower()

    try:
        if opts.mode == 0:
            if ext != ".pdf":
                raise ValueError("解除密碼僅支援 PDF 檔案")
            _decrypt_pdf_file(input_path, output_path, password_provider)
        elif ext in _JPG_EXTS:
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


def _compress_process_worker(args: tuple) -> tuple[int, CompressResult]:
    """ProcessPoolExecutor 工作函數（必須在模組頂層以供 pickle 序列化）"""
    idx, path, opts = args
    file_opts = dataclasses.replace(opts, file_index=idx + 1)
    t0 = time.perf_counter()
    try:
        result = compress_file(path, file_opts)
    except Exception as exc:
        result = CompressResult(path, "", 0, 0, False, f"未預期錯誤：{exc}")
    result.elapsed = time.perf_counter() - t0
    return idx, result


def compress_batch(
    file_paths: list[str],
    opts: CompressOptions,
    on_progress: Callable[[int, int, CompressResult], None],
    on_done: Callable[[list[CompressResult]], None],
    should_cancel: Callable[[], bool] | None = None,
    max_workers: int = 1,
    password_provider: "PasswordProvider | None" = None,
) -> threading.Thread:
    """在背景執行緒批次壓縮，每完成一個檔案呼叫 on_progress，全部完成後呼叫 on_done。

    max_workers > 1 時使用 ThreadPoolExecutor 並行壓縮。
    should_cancel 回傳 True 時：尚未開始的任務跳過，已在執行的任務完成後停止。
    解密模式（mode 0）需向 GUI 彈框索取密碼，強制單執行緒並走 thread 路徑。
    """
    if opts.mode == 0:
        max_workers = 1

    def _run_one(idx: int, path: str) -> tuple[int, CompressResult]:
        if should_cancel and should_cancel():
            r = CompressResult(path, "", 0, 0, False, "已取消")
            r.elapsed = 0.0
            return idx, r
        file_opts = dataclasses.replace(opts, file_index=idx + 1)
        t0 = time.perf_counter()
        try:
            result = compress_file(path, file_opts, password_provider)
        except Exception as exc:
            result = CompressResult(path, "", 0, 0, False, f"未預期錯誤：{exc}")
        result.elapsed = time.perf_counter() - t0
        return idx, result

    def run():
        total = len(file_paths)
        results_map: dict[int, CompressResult] = {}

        workers = max(1, max_workers)
        if workers == 1:
            for i, path in enumerate(file_paths):
                if should_cancel and should_cancel():
                    break
                _, result = _run_one(i, path)
                results_map[i] = result
                on_progress(len(results_map), total, result)
        else:
            lock = threading.Lock()
            done_count = [0]
            cancelled = False
            executor = ProcessPoolExecutor(max_workers=workers)
            try:
                futures = {
                    executor.submit(_compress_process_worker, (i, path, opts)): i
                    for i, path in enumerate(file_paths)
                }
                for future in as_completed(futures):
                    try:
                        idx, result = future.result()
                    except concurrent.futures.CancelledError:
                        i = futures[future]
                        result = CompressResult(file_paths[i], "", 0, 0, False, "已取消")
                        result.elapsed = 0.0
                        idx = i
                    except Exception as exc:
                        i = futures[future]
                        result = CompressResult(
                            file_paths[i], "", 0, 0, False, f"未預期錯誤：{exc}"
                        )
                        idx = i
                    results_map[idx] = result
                    with lock:
                        done_count[0] += 1
                        current = done_count[0]
                    on_progress(current, total, result)
                    if not cancelled and should_cancel and should_cancel():
                        cancelled = True
                        for f in futures:
                            f.cancel()
                        executor.shutdown(wait=False, cancel_futures=True)
                        break
            finally:
                if not cancelled:
                    executor.shutdown(wait=True)

        ordered = [results_map[i] for i in sorted(results_map)]
        on_done(ordered)

    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t
