import json
import os

_PLACEHOLDERS = {"（與原始檔案相同目錄）", "（自動建立 compressed/ 子資料夾）"}

_SETTINGS_DIR = os.path.join(os.getenv("APPDATA", os.path.expanduser("~")), "compress-pdf")
_SETTINGS_PATH = os.path.join(_SETTINGS_DIR, "settings.json")

_DEFAULTS: dict = {
    "mode": 1,
    "dpi": "150 DPI（一般文件）",
    "quality": 75,
    "preserve_dates": True,
    "keep_filename": False,
    "output_dir": "",
    "theme": "System",
    "fmt_pdf": True,
    "fmt_jpg": True,
    "fmt_pptx": True,
    "filename_template": "",
    "max_workers": "1（順序）",
}


def load_settings() -> dict:
    try:
        with open(_SETTINGS_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return {**_DEFAULTS, **data}
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(_DEFAULTS)


def save_settings(settings: dict) -> None:
    os.makedirs(_SETTINGS_DIR, exist_ok=True)
    clean = {k: v for k, v in settings.items() if v not in _PLACEHOLDERS}
    with open(_SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(clean, f, ensure_ascii=False, indent=2)
