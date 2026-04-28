import ctypes
import ctypes.wintypes
import os
import sys


def format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / 1024 ** 2:.1f} MB"


def size_delta_str(before: int, after: int) -> str:
    if before == 0:
        return ""
    pct = (before - after) / before * 100
    sign = "-" if pct >= 0 else "+"
    return f"{sign}{abs(pct):.1f}%"


def default_output_path(
    input_path: str,
    output_dir: str | None = None,
    keep_filename: bool = False,
    filename_template: str = "",
    file_index: int = 1,
) -> str:
    from datetime import date

    src_dir = os.path.dirname(input_path)
    filename = os.path.basename(input_path)
    base = os.path.splitext(filename)[0]
    ext = os.path.splitext(filename)[1]

    if filename_template:
        today = date.today().strftime("%Y%m%d")
        out_base = (filename_template
                    .replace("{name}", base)
                    .replace("{date}", today)
                    .replace("{index}", str(file_index)))
        out_name = out_base + ext
    elif keep_filename:
        out_name = filename
    else:
        out_name = f"{base}_compressed{ext}"

    if output_dir:
        folder = output_dir
    elif keep_filename or out_name == filename:
        folder = os.path.join(src_dir, "compressed")
    else:
        folder = src_dir

    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, out_name)


def preserve_timestamps(src_path: str, dst_path: str) -> None:
    """將 src_path 的建立時間與修改時間複製到 dst_path。"""
    src_stat = os.stat(src_path)
    # 修改時間與存取時間（跨平台）
    os.utime(dst_path, (src_stat.st_atime, src_stat.st_mtime))
    # 建立時間只有 Windows 支援
    if sys.platform == "win32":
        _set_creation_time_windows(dst_path, src_stat.st_ctime)


def _unix_to_filetime(unix_ts: float) -> ctypes.wintypes.FILETIME:
    """將 Unix timestamp 轉換為 Windows FILETIME（自 1601-01-01 起的 100 奈秒數）。"""
    # 1601-01-01 到 1970-01-01 的 100 奈秒差值
    EPOCH_DIFF = 116_444_736_000_000_000
    value = int(unix_ts * 10_000_000) + EPOCH_DIFF
    return ctypes.wintypes.FILETIME(value & 0xFFFF_FFFF, value >> 32)


def _set_creation_time_windows(path: str, ctime: float) -> None:
    GENERIC_WRITE = 0x4000_0000
    OPEN_EXISTING = 3
    FILE_FLAG_BACKUP_SEMANTICS = 0x0200_0000

    handle = ctypes.windll.kernel32.CreateFileW(
        path,
        GENERIC_WRITE,
        0,
        None,
        OPEN_EXISTING,
        FILE_FLAG_BACKUP_SEMANTICS,
        None,
    )
    INVALID_HANDLE = ctypes.wintypes.HANDLE(-1).value
    if handle == INVALID_HANDLE:
        return
    try:
        ft = _unix_to_filetime(ctime)
        ctypes.windll.kernel32.SetFileTime(
            handle,
            ctypes.byref(ft),  # creation time
            None,              # access time（不動）
            None,              # write time（已由 os.utime 設定）
        )
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)
