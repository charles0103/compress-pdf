import os
import threading
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog
import customtkinter as ctk
from tkinterdnd2 import DND_FILES, TkinterDnD

from core.compressor import CompressOptions, CompressResult, compress_batch, analyze_file
from core.pptx_compressor import analyze_pptx
from utils.file_utils import format_size, size_delta_str
from utils.settings import load_settings, save_settings
from gui.widgets import DropZone, FileListItem, AnimatedBorderFrame, GradientDivider, CTkSplitter, VirtualFileList


DPI_OPTIONS = [
    "300 DPI（印刷）",
    "200 DPI（高品質）",
    "150 DPI（一般文件）",
    "96 DPI（螢幕）",
    "72 DPI（網頁）",
]
_DPI_MAP = {opt: int(opt.split()[0]) for opt in DPI_OPTIONS}


class MainWindow(ctk.CTk, TkinterDnD.DnDWrapper):
    """PDF 壓縮工具主視窗。"""

    def __init__(self):
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self)

        self.title("PDF 壓縮工具")
        self.geometry("1100x740")
        self.minsize(960, 720)
        self.resizable(True, True)

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self._file_paths: list[str] = []
        self._is_running = False
        self._cancel_requested = False
        self._load_cancelled = False
        self._last_results: list = []
        self._last_opts = None
        self._compress_start_time: str = ""

        self._build_ui()
        self._load_settings()

        # 整個視窗與 DropZone 都接受拖放
        self.drop_target_register(DND_FILES)
        self.dnd_bind("<<Drop>>", self._on_drop)
        self._drop_zone.drop_target_register(DND_FILES)
        self._drop_zone.dnd_bind("<<DragEnter>>", lambda _: self._drop_zone.start_scan())
        self._drop_zone.dnd_bind("<<DragLeave>>", lambda _: self._drop_zone.stop_scan())
        self._drop_zone.dnd_bind("<<Drop>>", self._on_drop_with_stop)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── UI 建構 ──────────────────────────────────────────────────

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_main_layout()

    def _build_main_layout(self):
        # 左欄：DropZone、選項、輸出、動作、進度
        # 右欄：上 已選檔案 / 下 壓縮結果（垂直可拖）
        self._main_split = CTkSplitter(
            self, orient="horizontal",
            a_initial=440, a_min=380, b_min=360,
        )
        self._main_split.grid(row=1, column=0, sticky="nsew", padx=16, pady=(8, 14))

        left  = self._main_split.pane_a
        right = self._main_split.pane_b

        left.grid_columnconfigure(0, weight=1)
        self._build_drop_zone(left, row=0)
        self._build_options(left, row=1)
        self._build_output_row(left, row=2)
        self._build_action_row(left, row=3)

        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(0, weight=1)
        self._right_split = CTkSplitter(
            right, orient="vertical",
            a_initial=320, a_min=160, b_min=140,
        )
        self._right_split.grid(row=0, column=0, sticky="nsew", padx=(8, 0))

        top    = self._right_split.pane_a
        bottom = self._right_split.pane_b
        top.grid_columnconfigure(0, weight=1)
        top.grid_rowconfigure(0, weight=1)
        bottom.grid_columnconfigure(0, weight=1)
        bottom.grid_rowconfigure(0, weight=1)

        self._build_file_list(top)
        self._build_results(bottom)

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 0))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="PDF 壓縮工具",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=("gray10", "#00D1FF"),
        ).grid(row=0, column=0, sticky="w")

        self._theme_btn = ctk.CTkButton(
            header,
            text="🌙",
            width=36, height=28,
            fg_color="transparent",
            hover_color=("gray80", "#0D2530"),
            text_color=("gray10", "#888888"),
            border_width=1,
            border_color=("gray70", "#2E2E2E"),
            command=self._toggle_theme,
        )
        self._theme_btn.grid(row=0, column=1, sticky="e")

        self._divider = GradientDivider(header)
        self._divider.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 2))

    def _build_drop_zone(self, parent, row: int):
        self._drop_zone = DropZone(parent, on_click=self._browse_files)
        self._drop_zone.grid(row=row, column=0, sticky="ew", padx=(0, 8), pady=(0, 4))

    def _build_file_list(self, parent):
        self._file_list_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self._file_list_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self._file_list_frame.grid_columnconfigure(0, weight=1)
        self._file_list_frame.grid_rowconfigure(1, weight=1)

        header_row = ctk.CTkFrame(self._file_list_frame, fg_color="transparent")
        header_row.grid(row=0, column=0, sticky="ew", pady=(4, 2))
        header_row.grid_columnconfigure(0, weight=1)

        self._file_count_label = ctk.CTkLabel(
            header_row,
            text="已選檔案",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=("gray40", "#555555"),
        )
        self._file_count_label.grid(row=0, column=0, sticky="w")

        self._btn_clear_all = ctk.CTkButton(
            header_row,
            text="全部清除",
            width=70, height=22,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color="transparent",
            hover_color=("gray80", "#1A2A30"),
            text_color=("gray30", "#888888"),
            border_width=1,
            border_color=("gray70", "#2E2E2E"),
            command=self._clear_or_cancel_load,
        )
        self._btn_clear_all.grid(row=0, column=1, sticky="e")

        self._file_list = VirtualFileList(
            self._file_list_frame,
            on_remove=self._remove_file,
        )
        self._file_list.grid(row=1, column=0, sticky="nsew", pady=(0, 0))

    def _build_options(self, parent, row: int):
        opt_frame = AnimatedBorderFrame(
            parent,
            fg_color=("gray94", "#232323"),
            border_width=1,
            border_color=("gray75", "#2E2E2E"),
            corner_radius=10,
        )
        opt_frame.grid(row=row, column=0, sticky="ew", pady=(2, 0))
        opt_frame.grid_columnconfigure((0, 1), weight=1)

        # 壓縮模式
        ctk.CTkLabel(
            opt_frame, text="壓縮模式",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=("gray30", "#888888"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(6, 2))
        self._mode_var = tk.IntVar(value=1)
        _mode_labels = ["無失真", "圖片優化", "高壓縮"]
        self._mode_seg = ctk.CTkSegmentedButton(
            opt_frame,
            values=_mode_labels,
            selected_color=("gray30", "#00A8CC"),
            selected_hover_color=("gray20", "#008FAD"),
            unselected_color=("gray80", "#1A1A1A"),
            unselected_hover_color=("gray70", "#1A3040"),
            text_color=("gray10", "#FFFFFF"),
            text_color_disabled=("gray60", "#555555"),
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self._on_mode_seg_change,
        )
        self._mode_seg.set(_mode_labels[0])
        self._mode_seg.grid(row=1, column=0, columnspan=2, sticky="ew",
                            padx=12, pady=(0, 2))

        # 壓縮等級（pikepdf 9+ 已自動最佳化，此 slider 僅保留 UI 一致性）
        ctk.CTkLabel(
            opt_frame, text="壓縮等級（自動）",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=("gray30", "#888888"),
        ).grid(row=2, column=0, sticky="w", padx=12, pady=(3, 0))
        self._level_label = ctk.CTkLabel(
            opt_frame, text="9",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=("gray30", "#00D1FF"),
        )
        self._level_label.grid(row=2, column=1, sticky="e", padx=12)

        self._level_slider = ctk.CTkSlider(
            opt_frame, from_=1, to=9, number_of_steps=8,
            button_color=("gray55", "#00D1FF"),
            button_hover_color=("gray40", "#008FAD"),
            progress_color=("gray55", "#00A8CC"),
            command=self._on_level_change,
            state="disabled",
        )
        self._level_slider.set(9)
        self._level_slider.grid(row=3, column=0, columnspan=2, sticky="ew",
                                padx=12, pady=(1, 4))

        # 圖片解析度（僅對超過目標 DPI 的圖片降採樣，不會升採樣）
        ctk.CTkLabel(
            opt_frame, text="圖片解析度（降採樣上限）",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=("gray30", "#888888"),
        ).grid(row=4, column=0, sticky="w", padx=12, pady=(2, 0))
        self._dpi_menu = ctk.CTkOptionMenu(
            opt_frame, values=DPI_OPTIONS, width=160,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=("gray80", "#1A1A1A"),
            button_color=("gray65", "#2E2E2E"),
            button_hover_color=("gray55", "#004D66"),
            text_color=("gray10", "#00D1FF"),
            dropdown_fg_color=("gray90", "#1A1A1A"),
            dropdown_text_color=("gray10", "#BBBBBB"),
            dropdown_hover_color=("gray80", "#0D2530"),
            command=lambda _: None,
        )
        self._dpi_menu.set("150 DPI（一般文件）")
        self._dpi_menu.grid(row=4, column=1, sticky="e", padx=12, pady=(2, 0))

        # 圖片品質（越低壓縮率越高）
        ctk.CTkLabel(
            opt_frame, text="圖片品質（越低檔案越小）",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=("gray30", "#888888"),
        ).grid(row=5, column=0, sticky="w", padx=12, pady=(4, 0))
        self._quality_label = ctk.CTkLabel(
            opt_frame, text="75",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=("gray30", "#00D1FF"),
        )
        self._quality_label.grid(row=5, column=1, sticky="e", padx=12)

        self._quality_slider = ctk.CTkSlider(
            opt_frame, from_=50, to=95, number_of_steps=45,
            button_color=("gray55", "#00D1FF"),
            button_hover_color=("gray40", "#008FAD"),
            progress_color=("gray55", "#00A8CC"),
            command=self._on_quality_change,
        )
        self._quality_slider.set(75)
        self._quality_slider.grid(row=6, column=0, columnspan=2, sticky="ew",
                                  padx=12, pady=(1, 5))

        # 保留原始日期
        self._preserve_dates_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            opt_frame,
            text="保留原始檔案建立/修改日期",
            variable=self._preserve_dates_var,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            border_color=("gray55", "#2E2E2E"),
            fg_color=("gray30", "#00D1FF"),
            hover_color=("gray40", "#008FAD"),
            checkmark_color=("white", "#001A22"),
        ).grid(row=7, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 2))

        # 保留原始檔名
        self._keep_filename_var = tk.BooleanVar(value=False)
        self._keep_filename_cb = ctk.CTkCheckBox(
            opt_frame,
            text="保留原始檔名（輸出至 compressed/ 子資料夾）",
            variable=self._keep_filename_var,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            border_color=("gray55", "#2E2E2E"),
            fg_color=("gray30", "#00D1FF"),
            hover_color=("gray40", "#008FAD"),
            checkmark_color=("white", "#001A22"),
            command=self._on_keep_filename_change,
        )
        self._keep_filename_cb.grid(row=8, column=0, columnspan=2, sticky="w",
                                    padx=12, pady=(0, 2))

        # 並行壓縮執行緒
        ctk.CTkLabel(
            opt_frame, text="並行壓縮執行緒",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=("gray30", "#888888"),
        ).grid(row=9, column=0, columnspan=2, sticky="w", padx=12, pady=(3, 1))
        _worker_opts = ["1（順序）", "2", "4", "自動"]
        self._workers_seg = ctk.CTkSegmentedButton(
            opt_frame,
            values=_worker_opts,
            selected_color=("gray30", "#00A8CC"),
            selected_hover_color=("gray20", "#008FAD"),
            unselected_color=("gray80", "#1A1A1A"),
            unselected_hover_color=("gray70", "#1A3040"),
            text_color=("gray10", "#FFFFFF"),
            font=ctk.CTkFont(family="Segoe UI", size=12),
            command=lambda _: None,
        )
        self._workers_seg.set("1（順序）")
        self._workers_seg.grid(row=10, column=0, columnspan=2, sticky="ew",
                               padx=12, pady=(0, 2))

        # 格式篩選
        ctk.CTkLabel(
            opt_frame, text="壓縮格式",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=("gray30", "#888888"),
        ).grid(row=11, column=0, columnspan=2, sticky="w", padx=12, pady=(2, 1))

        fmt_row = ctk.CTkFrame(opt_frame, fg_color="transparent")
        fmt_row.grid(row=12, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 6))

        _cb_kw = dict(
            font=ctk.CTkFont(family="Segoe UI", size=12),
            border_color=("gray55", "#2E2E2E"),
            fg_color=("gray30", "#00D1FF"),
            hover_color=("gray40", "#008FAD"),
            checkmark_color=("white", "#001A22"),
        )
        self._fmt_pdf_var = tk.BooleanVar(value=True)
        self._fmt_jpg_var = tk.BooleanVar(value=True)
        self._fmt_pptx_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(fmt_row, text="PDF",  variable=self._fmt_pdf_var,  command=self._refresh_list_dim, **_cb_kw).grid(row=0, column=0, padx=(0, 16))
        ctk.CTkCheckBox(fmt_row, text="JPG",  variable=self._fmt_jpg_var,  command=self._refresh_list_dim, **_cb_kw).grid(row=0, column=1, padx=(0, 16))
        ctk.CTkCheckBox(fmt_row, text="PPTX", variable=self._fmt_pptx_var, command=self._refresh_list_dim, **_cb_kw).grid(row=0, column=2)

        self._on_mode_change()

    def _build_output_row(self, parent, row: int):
        row_frame = ctk.CTkFrame(parent, fg_color="transparent")
        row_frame.grid(row=row, column=0, sticky="ew", padx=(0, 8), pady=(5, 0))
        row_frame.grid_columnconfigure(0, weight=1)
        row = row_frame  # 保留原本變數名以最少化下方修改

        ctk.CTkLabel(
            row, text="輸出資料夾",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=("gray30", "#888888"),
        ).grid(row=0, column=0, sticky="w")
        inner = ctk.CTkFrame(row, fg_color="transparent")
        inner.grid(row=1, column=0, sticky="ew")
        inner.grid_columnconfigure(0, weight=1)

        self._output_dir_var = tk.StringVar(value="（與原始檔案相同目錄）")
        ctk.CTkEntry(
            inner,
            textvariable=self._output_dir_var,
            state="readonly",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color=("gray90", "#1A1A1A"),
            border_color=("gray70", "#2E2E2E"),
            text_color=("gray20", "#888888"),
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))

        ctk.CTkButton(
            inner, text="瀏覽", width=60,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=("gray75", "#1A3040"),
            hover_color=("gray65", "#004D66"),
            border_width=1,
            border_color=("gray55", "#00D1FF"),
            text_color=("gray10", "#00D1FF"),
            command=self._browse_output,
        ).grid(row=0, column=1)

        ctk.CTkButton(
            inner, text="清除", width=60,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color="transparent",
            hover_color=("gray80", "#2A1515"),
            border_width=1,
            border_color=("gray70", "#2E2E2E"),
            text_color=("gray30", "#666666"),
            command=lambda: self._output_dir_var.set("（與原始檔案相同目錄）"),
        ).grid(row=0, column=2, padx=(4, 0))

        hint_row = ctk.CTkFrame(row_frame, fg_color="transparent")
        hint_row.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        hint_row.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hint_row, text="輸出檔名樣板",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=("gray30", "#888888"),
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            hint_row,
            text="{name} 原檔名  {date} 日期  {index} 序號",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=("gray55", "#444444"),
        ).grid(row=0, column=1, sticky="e")

        self._filename_template_var = tk.StringVar(value="")
        ctk.CTkEntry(
            row_frame,
            textvariable=self._filename_template_var,
            placeholder_text="空白 = {name}_compressed（預設）",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color=("gray90", "#1A1A1A"),
            border_color=("gray70", "#2E2E2E"),
            text_color=("gray10", "#CCCCCC"),
        ).grid(row=3, column=0, sticky="ew", pady=(2, 0))

    def _build_action_row(self, parent, row: int):
        row_frame = ctk.CTkFrame(parent, fg_color="transparent")
        row_frame.grid(row=row, column=0, sticky="ew", padx=(0, 8), pady=(6, 0))
        row_frame.grid_columnconfigure(0, weight=1)
        row_frame.grid_columnconfigure(1, weight=0)
        row = row_frame

        self._btn_analyze = ctk.CTkButton(
            row, text="📊 分析圖片", height=36,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=("gray80", "#0D1F26"),
            hover_color=("gray70", "#163040"),
            border_width=1,
            border_color=("gray55", "#00D1FF"),
            text_color=("gray10", "#00D1FF"),
            command=self._analyze_files,
        )
        self._btn_analyze.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self._btn_start = ctk.CTkButton(
            row, text="開始壓縮", height=36,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color=("gray25", "#003D4D"),
            hover_color=("gray15", "#005566"),
            border_width=1,
            border_color=("gray40", "#00D1FF"),
            text_color=("white", "#00D1FF"),
            command=self._start_compress,
        )
        self._btn_start.grid(row=0, column=1, sticky="ew")

        self._progress_bar = ctk.CTkProgressBar(
            row,
            progress_color=("gray40", "#00D1FF"),
            fg_color=("gray80", "#1A1A1A"),
            border_width=1,
            border_color=("gray70", "#2E2E2E"),
        )
        self._progress_bar.set(0)
        self._progress_bar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        self._progress_label = ctk.CTkLabel(
            row, text="",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=("gray50", "#555555"),
        )
        self._progress_label.grid(row=2, column=0, sticky="w", pady=(2, 6))

        self._progress_pct_label = ctk.CTkLabel(
            row, text="",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=("gray50", "#00A8CC"),
        )
        self._progress_pct_label.grid(row=2, column=1, sticky="e", pady=(2, 6))

    def _build_results(self, parent):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=(2, 0))
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        header_row = ctk.CTkFrame(frame, fg_color="transparent")
        header_row.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        header_row.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header_row, text="壓縮結果",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=("gray40", "#555555"),
        ).grid(row=0, column=0, sticky="w")

        self._btn_export = ctk.CTkButton(
            header_row,
            text="📋 匯出日誌",
            width=90, height=22,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color="transparent",
            hover_color=("gray80", "#1A2A30"),
            text_color=("gray30", "#888888"),
            border_width=1,
            border_color=("gray70", "#2E2E2E"),
            state="disabled",
            command=self._export_log,
        )
        self._btn_export.grid(row=0, column=1, sticky="e")

        self._result_box = ctk.CTkTextbox(
            frame,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=("gray92", "#111111"),
            border_width=1,
            border_color=("gray75", "#2E2E2E"),
            text_color=("gray10", "#AAAAAA"),
            scrollbar_button_color=("gray70", "#2E2E2E"),
            scrollbar_button_hover_color=("gray60", "#00D1FF"),
            state="disabled",
        )
        self._result_box.grid(row=1, column=0, sticky="nsew")

    # ── 設定持久化 ───────────────────────────────────────────────

    def _load_settings(self):
        s = load_settings()
        self._mode_var.set(s["mode"])
        _mode_label_map = {1: "無失真", 2: "圖片優化", 3: "高壓縮"}
        self._mode_seg.set(_mode_label_map.get(s["mode"], "無失真"))
        self._dpi_menu.set(s["dpi"])
        self._quality_slider.set(s["quality"])
        self._quality_label.configure(text=str(s["quality"]))
        self._preserve_dates_var.set(s["preserve_dates"])
        self._keep_filename_var.set(s["keep_filename"])
        self._fmt_pdf_var.set(s["fmt_pdf"])
        self._fmt_jpg_var.set(s["fmt_jpg"])
        self._fmt_pptx_var.set(s["fmt_pptx"])
        self._filename_template_var.set(s.get("filename_template", ""))
        self._workers_seg.set(s.get("max_workers", "1（順序）"))
        if s["output_dir"]:
            self._output_dir_var.set(s["output_dir"])
        theme = s.get("theme", "System")
        ctk.set_appearance_mode(theme)
        self._theme_btn.configure(text="☀️" if theme == "Dark" else "🌙")
        self._divider._draw()
        self._on_mode_change()
        self._on_keep_filename_change()

    def _save_settings(self):
        save_settings({
            "mode": self._mode_var.get(),
            "dpi": self._dpi_menu.get(),
            "quality": int(round(self._quality_slider.get())),
            "preserve_dates": self._preserve_dates_var.get(),
            "keep_filename": self._keep_filename_var.get(),
            "output_dir": self._output_dir_var.get(),
            "theme": ctk.get_appearance_mode(),
            "fmt_pdf": self._fmt_pdf_var.get(),
            "fmt_jpg": self._fmt_jpg_var.get(),
            "fmt_pptx": self._fmt_pptx_var.get(),
            "filename_template": self._filename_template_var.get().strip(),
            "max_workers": self._workers_seg.get(),
        })

    def _on_close(self):
        self._save_settings()
        self.destroy()

    # ── 事件處理 ─────────────────────────────────────────────────

    def _toggle_theme(self):
        current = ctk.get_appearance_mode()
        new_mode = "Dark" if current == "Light" else "Light"
        ctk.set_appearance_mode(new_mode)
        self._theme_btn.configure(text="☀️" if new_mode == "Dark" else "🌙")
        self._divider._draw()
    def _on_mode_seg_change(self, label: str):
        mapping = {"無失真": 1, "圖片優化": 2, "高壓縮": 3}
        self._mode_var.set(mapping.get(label, 1))
        self._on_mode_change()

    def _on_mode_change(self):
        mode = self._mode_var.get()
        dpi_state = "normal" if mode >= 2 else "disabled"
        quality_state = "normal" if mode == 3 else "disabled"
        self._dpi_menu.configure(state=dpi_state)
        self._quality_slider.configure(state=quality_state)

    def _on_level_change(self, val):
        self._level_label.configure(text=str(int(round(float(val)))))

    def _on_quality_change(self, val):
        self._quality_label.configure(text=str(int(round(float(val)))))

    def _on_keep_filename_change(self):
        if self._keep_filename_var.get():
            if self._output_dir_var.get() == "（與原始檔案相同目錄）":
                self._output_dir_var.set("（自動建立 compressed/ 子資料夾）")
        else:
            if self._output_dir_var.get() == "（自動建立 compressed/ 子資料夾）":
                self._output_dir_var.set("（與原始檔案相同目錄）")

    def _browse_files(self):
        paths = filedialog.askopenfilenames(
            title="選擇檔案",
            filetypes=[
                ("支援的檔案", "*.pdf *.jpg *.jpeg *.pptx"),
                ("PDF 檔案", "*.pdf"),
                ("JPEG 圖檔", "*.jpg *.jpeg"),
                ("PowerPoint", "*.pptx"),
                ("所有檔案", "*.*"),
            ],
        )
        if paths:
            self._load_files_async(list(paths), check_folders=False)

    def _browse_output(self):
        folder = filedialog.askdirectory(title="選擇輸出資料夾")
        if folder:
            self._output_dir_var.set(folder)

    def _on_drop(self, event):
        raw = event.data or ""
        try:
            paths = self.tk.splitlist(raw)
        except Exception:
            paths = [p.strip("{}") for p in raw.split()]
        cleaned = [p.strip() for p in paths if p.strip()]
        if cleaned:
            self._load_files_async(cleaned, check_folders=True)

    def _on_drop_with_stop(self, event):
        self._drop_zone.stop_scan()
        self._on_drop(event)

    def _add_file(self, path: str, size_bytes: int | None = None,
                  defer_refresh: bool = False):
        if path in self._file_paths:
            return
        if size_bytes is None and not os.path.isfile(path):
            return
        if size_bytes is None:
            try:
                size_bytes = os.path.getsize(path)
            except Exception as exc:
                self._append_result(f"⚠️  無法載入 {os.path.basename(path)}：{exc}\n")
                return
        if not self._file_list.add_entry(path, size_bytes):
            return
        self._file_paths.append(path)
        if not defer_refresh:
            self._update_file_count()

    def _update_file_count(self):
        n = len(self._file_paths)
        if n == 0:
            self._file_count_label.configure(text="已選檔案")
        else:
            total_mb = self._file_list.total_size() / 1024 ** 2
            size_str = f"{total_mb:.1f} MB" if total_mb < 1024 else f"{total_mb / 1024:.2f} GB"
            self._file_count_label.configure(text=f"已選檔案  共 {n} 個  /  {size_str}")
        self._refresh_list_dim()

    def _refresh_list_dim(self):
        allowed = set()
        if self._fmt_pdf_var.get():
            allowed.add(".pdf")
        if self._fmt_jpg_var.get():
            allowed.update({".jpg", ".jpeg"})
        if self._fmt_pptx_var.get():
            allowed.add(".pptx")
        all_checked = len(allowed) == 4  # pdf + jpg + jpeg + pptx
        if all_checked:
            self._file_list.set_dimmed_paths(set())
        else:
            dimmed = {p for p in self._file_paths
                      if Path(p).suffix.lower() not in allowed}
            self._file_list.set_dimmed_paths(dimmed)

    # ── 非同步批次載入（避免網路磁碟 stat 阻塞 GUI）───────────────────

    _LOAD_BATCH_SIZE = 10
    _VALID_EXTS = (".pdf", ".jpg", ".jpeg", ".pptx")

    def _load_files_async(self, raw_paths: list[str], check_folders: bool):
        """背景執行緒讀取 metadata，分批送回主執行緒建立 widget。

        check_folders=True 時（拖放）才在 worker 內檢查是否為資料夾，
        因為網路磁碟 isdir() 也會耗時。
        """
        seen = set(self._file_paths)
        candidates: list[str] = []
        unknown: list[str] = []
        for p in raw_paths:
            if p in seen:
                continue
            seen.add(p)
            if p.lower().endswith(self._VALID_EXTS):
                candidates.append(p)
            elif check_folders:
                unknown.append(p)

        total = len(candidates)
        if total == 0 and not unknown:
            return

        self._load_cancelled = False
        if total > 0:
            self._set_loading_status(f"載入中  0 / {total} …")
            self.update_idletasks()  # 立即重繪 label，避免被後續批次蓋過去

        batch_done = threading.Event()
        batch_done.set()  # 第一個 batch 不需等待

        def submit_batch(batch, processed):
            batch_done.clear()
            self.after(0, self._consume_loaded_batch, batch, processed, total, batch_done)
            # 等主執行緒處理完才繼續，避免事件佇列堆積導致按鈕點擊被卡住
            batch_done.wait(timeout=2.0)

        def worker():
            has_folder = False
            for p in unknown:
                if self._load_cancelled:
                    break
                try:
                    if os.path.isdir(p):
                        has_folder = True
                        break
                except Exception:
                    pass

            batch: list[tuple[str, int]] = []
            processed = 0
            for p in candidates:
                if self._load_cancelled:
                    break
                try:
                    size = os.path.getsize(p)
                except Exception:
                    continue
                batch.append((p, size))
                processed += 1
                if len(batch) >= self._LOAD_BATCH_SIZE:
                    submit_batch(batch, processed)
                    batch = []
            if batch and not self._load_cancelled:
                submit_batch(batch, processed)

            self.after(0, self._finish_loading, has_folder, self._load_cancelled)

        threading.Thread(target=worker, daemon=True).start()

    def _consume_loaded_batch(self, batch: list[tuple[str, int]], done: int, total: int,
                              batch_done=None):
        try:
            # update() 而非 update_idletasks()：強制處理待處理的點擊事件，
            # 否則在快速 SSD 上 worker 連續排批次，主執行緒一直在 widget for-loop，
            # 取消按鈕的點擊事件被卡在佇列裡無法處理
            self.update()
            if self._load_cancelled:
                return
            if done < total:
                self._set_loading_status(f"載入中  {done} / {total} …")
            for path, size in batch:
                if self._load_cancelled:
                    break
                self._add_file(path, size_bytes=size, defer_refresh=True)
            # 批次結束才更新一次計數與 dim
            self._update_file_count()
        finally:
            if batch_done is not None:
                batch_done.set()

    def _finish_loading(self, has_folder: bool, cancelled: bool = False):
        self._set_loading_status("")
        if cancelled:
            self._append_result("⏹  使用者取消載入。\n")
        if has_folder:
            self._append_result("⚠️  不支援拖入資料夾，請直接拖入檔案。\n")

    def _set_loading_status(self, text: str):
        # 顯示在 DropZone 上：青色字、清晰可見、就在使用者剛剛操作的位置
        self._is_loading = bool(text)
        self._set_clear_button_mode(cancel=self._is_loading)
        if text:
            self._drop_zone.show_loading(f"⏳  {text}")
        else:
            self._drop_zone.reset_idle()
        self._progress_label.configure(text=text)

    def _remove_file(self, path: str):
        if path in self._file_paths:
            self._file_paths.remove(path)
        self._file_list.remove_entry(path)
        self._update_file_count()

    def _clear_files(self):
        self._file_paths.clear()
        self._file_list.clear()
        self._update_file_count()

    def _clear_or_cancel_load(self):
        if self._loading_in_progress():
            self._load_cancelled = True
        else:
            self._clear_files()

    def _loading_in_progress(self) -> bool:
        return getattr(self, "_is_loading", False)

    def _set_clear_button_mode(self, cancel: bool):
        if cancel:
            self._btn_clear_all.configure(
                text="取消載入",
                text_color=("white", "#FF8899"),
                border_color=("gray40", "#FF5577"),
                hover_color=("gray15", "#5A1520"),
            )
        else:
            self._btn_clear_all.configure(
                text="全部清除",
                text_color=("gray30", "#888888"),
                border_color=("gray70", "#2E2E2E"),
                hover_color=("gray80", "#1A2A30"),
            )

    def _analyze_files(self):
        """分析選取檔案的圖片解析度（PDF 顯示詳細資訊，JPG 顯示基本資訊）"""
        if not self._file_paths:
            self._append_result("⚠️  請先選擇至少一個檔案。\n")
            return

        self._clear_results()
        self._append_result("📊 圖片解析度分析\n")
        self._append_result("─" * 30 + "\n")

        for path in self._file_paths:
            name = os.path.basename(path)
            ext = os.path.splitext(path)[1].lower()

            if ext in (".jpg", ".jpeg"):
                self._analyze_jpg(path, name)
                continue

            if ext == ".pptx":
                self._analyze_pptx(path, name)
                continue

            result = analyze_file(path)
            if result is None:
                self._append_result(f"❌ 無法分析：{name}\n")
                continue

            self._append_result(f"\n📄 {name}\n")
            self._append_result(f"   頁數：{result.page_count}，圖片數：{result.total_images}\n")

            if result.dpi_distribution:
                self._append_result("   DPI 分佈：\n")
                for dpi in sorted(result.dpi_distribution.keys(), reverse=True):
                    count = result.dpi_distribution[dpi]
                    self._append_result(f"     {dpi} DPI：{count} 張\n")

            if result.images:
                avg_dpi = sum(img.dpi for img in result.images) / len(result.images)
                self._append_result(f"   平均估算 DPI：{avg_dpi:.0f}\n")

        self._append_result("\n" + "─" * 30 + "\n")
        self._append_result("💡 建議：設定低於平均 DPI 的目標解析度可獲得較佳壓縮效果\n")

    def _analyze_jpg(self, path: str, name: str) -> None:
        try:
            from PIL import Image
            img = Image.open(path)
            w, h = img.size
            dpi_info = img.info.get("dpi") or img.info.get("DPI")
            if isinstance(dpi_info, (tuple, list)):
                dpi_str = f"{dpi_info[0]:.0f} DPI"
            elif dpi_info:
                dpi_str = f"{dpi_info:.0f} DPI"
            else:
                dpi_str = "未知"
            size_mb = os.path.getsize(path) / 1024 ** 2
            self._append_result(f"\n🖼️  {name}\n")
            self._append_result(f"   尺寸：{w} × {h} px，DPI：{dpi_str}，大小：{size_mb:.1f} MB\n")
        except Exception as exc:
            self._append_result(f"❌ 無法分析：{name}（{exc}）\n")

    def _analyze_pptx(self, path: str, name: str) -> None:
        try:
            info = analyze_pptx(path)
            size_mb = os.path.getsize(path) / 1024 ** 2
            media_mb = info["total_media_bytes"] / 1024 ** 2
            self._append_result(f"\n📊 {name}\n")
            self._append_result(f"   檔案大小：{size_mb:.1f} MB\n")
            self._append_result(
                f"   媒體圖片：JPEG {info['jpeg']} 張 / PNG {info['png']} 張"
                f" / 其他 {info['other']} 個\n"
            )
            self._append_result(f"   媒體總大小：{media_mb:.1f} MB\n")
        except Exception as exc:
            self._append_result(f"❌ 無法分析：{name}（{exc}）\n")

    def _start_compress(self):
        if self._is_running:
            # 第二次點擊 = 取消
            self._cancel_requested = True
            self._btn_start.configure(state="disabled", text="正在停止…")
            self._append_result("\n⏹  使用者要求停止，將在當前檔案完成後中止剩餘批次。\n")
            return
        if not self._file_paths:
            self._append_result("⚠️  請先選擇至少一個檔案。\n")
            return

        allowed_exts: set[str] = set()
        if self._fmt_pdf_var.get():
            allowed_exts.add(".pdf")
        if self._fmt_jpg_var.get():
            allowed_exts.update({".jpg", ".jpeg"})
        if self._fmt_pptx_var.get():
            allowed_exts.add(".pptx")

        active_paths = [p for p in self._file_paths
                        if Path(p).suffix.lower() in allowed_exts]
        if not active_paths:
            self._append_result("⚠️  沒有符合已勾選格式的檔案，請至少勾選一種格式。\n")
            return

        output_dir = self._output_dir_var.get()
        if output_dir in ("（與原始檔案相同目錄）", "（自動建立 compressed/ 子資料夾）"):
            output_dir = ""

        _workers_map = {"1（順序）": 1, "2": 2, "4": 4,
                        "自動": os.cpu_count() or 4}
        max_workers = _workers_map.get(self._workers_seg.get(), 1)

        opts = CompressOptions(
            mode=self._mode_var.get(),
            level=int(round(self._level_slider.get())),
            dpi=_DPI_MAP.get(self._dpi_menu.get(), 150),
            quality=int(round(self._quality_slider.get())),
            output_dir=output_dir,
            preserve_dates=self._preserve_dates_var.get(),
            keep_filename=self._keep_filename_var.get(),
            filename_template=self._filename_template_var.get().strip(),
        )

        self._last_opts = opts
        self._last_results = []
        self._last_wall_elapsed = 0.0
        self._compress_start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._batch_start_ts = time.perf_counter()
        self._btn_export.configure(state="disabled",
                                   text_color=("gray30", "#888888"),
                                   border_color=("gray70", "#2E2E2E"))

        self._is_running = True
        self._cancel_requested = False
        # 「停止壓縮」狀態：紅色邊框，仍可按
        self._btn_start.configure(
            state="normal",
            text="⏹  停止壓縮",
            fg_color=("gray25", "#3D0D14"),
            hover_color=("gray15", "#5A1520"),
            border_color=("gray40", "#FF5577"),
            text_color=("white", "#FF8899"),
        )
        self._progress_bar.set(0)
        self._progress_pct_label.configure(text="")
        self._clear_results()

        compress_batch(
            file_paths=active_paths,
            opts=opts,
            on_progress=self._on_file_done,
            on_done=self._on_batch_done,
            should_cancel=lambda: self._cancel_requested,
            max_workers=max_workers,
        )

    def _on_file_done(self, done: int, total: int, result: CompressResult):
        self.after(0, self._update_progress, done, total, result)

    def _update_progress(self, done: int, total: int, result: CompressResult):
        pct = done / total
        self._progress_bar.set(pct)
        self._progress_label.configure(text=f"{done} / {total} 個檔案")
        self._progress_pct_label.configure(text=f"{pct:.0%}")

        name = os.path.basename(result.input_path)
        elapsed = f"{result.elapsed:.1f}s"
        if result.success:
            before = format_size(result.size_before)
            after = format_size(result.size_after)
            delta = size_delta_str(result.size_before, result.size_after)
            out_dir = os.path.dirname(result.output_path)
            self._append_result(
                f"✅  {name}\n"
                f"    {before} → {after}  ({delta})  {elapsed}\n"
                f"    輸出：{out_dir}\n"
            )
        else:
            self._append_result(f"❌  {name}  {elapsed}\n    錯誤：{result.error}\n")

    def _on_batch_done(self, results: list[CompressResult]):
        self.after(0, self._finish_batch, results)

    def _finish_batch(self, results: list[CompressResult]):
        cancelled = self._cancel_requested
        self._is_running = False
        self._cancel_requested = False
        self._last_results = results
        # 還原按鈕為「開始壓縮」外觀
        self._btn_start.configure(
            state="normal",
            text="開始壓縮",
            fg_color=("gray25", "#003D4D"),
            hover_color=("gray15", "#005566"),
            border_color=("gray40", "#00D1FF"),
            text_color=("white", "#00D1FF"),
        )
        ok = sum(1 for r in results if r.success)
        total_planned = len(self._file_paths)
        wall_elapsed = time.perf_counter() - getattr(self, "_batch_start_ts", 0)
        self._last_wall_elapsed = wall_elapsed
        cpu_elapsed = sum(r.elapsed for r in results)
        total_saved = sum(
            r.size_before - r.size_after
            for r in results if r.success and r.size_after > 0
        )
        saved_str = f"  節省 {format_size(total_saved)}" if total_saved > 0 else ""
        parallel = cpu_elapsed > wall_elapsed * 1.2  # 並行時 CPU 總和遠大於壁鐘時間
        time_str = (f"實際耗時 {wall_elapsed:.1f}s  CPU {cpu_elapsed:.1f}s"
                    if parallel else f"耗時 {wall_elapsed:.1f}s")

        if cancelled:
            self._progress_label.configure(
                text=f"已停止：完成 {ok}/{len(results)} 個（共 {total_planned} 個）"
            )
            self._append_result(
                f"\n{'─' * 30}\n"
                f"⏹  已停止  {ok}/{len(results)} 個成功"
                f"  {time_str}{saved_str}\n"
            )
        else:
            self._progress_label.configure(text=f"完成：{ok}/{len(results)} 個成功")
            self._append_result(
                f"\n{'─' * 30}\n"
                f"✔  完成 {ok}/{len(results)} 個成功"
                f"  {time_str}{saved_str}\n"
            )
        self._btn_export.configure(
            state="normal",
            text_color=("gray10", "#00D1FF"),
            border_color=("gray55", "#00D1FF"),
        )

    def _generate_log_text(self) -> str:
        mode_names = {1: "無失真（模式 1）", 2: "圖片優化（模式 2）", 3: "高壓縮（模式 3）"}
        opts = self._last_opts
        lines = [
            "PDF 壓縮工具 - 壓縮日誌",
            "=" * 40,
            f"時間：{self._compress_start_time}",
        ]
        if opts:
            lines.append(f"壓縮模式：{mode_names.get(opts.mode, str(opts.mode))}")
            if opts.mode >= 2:
                lines.append(f"圖片解析度：{opts.dpi} DPI")
            if opts.mode == 3:
                lines.append(f"圖片品質：{opts.quality}")
        lines += ["", "[壓縮結果]"]

        total_saved = 0
        ratios = []
        for r in self._last_results:
            name = os.path.basename(r.input_path)
            if r.success:
                before = format_size(r.size_before)
                after = format_size(r.size_after)
                delta = size_delta_str(r.size_before, r.size_after)
                out_dir = os.path.dirname(r.output_path)
                elapsed = f"{r.elapsed:.1f}s"
                lines.append(f"✅  {name}")
                lines.append(f"    {before} → {after}  ({delta})  {elapsed}")
                lines.append(f"    輸出：{out_dir}")
                saved = r.size_before - r.size_after
                total_saved += saved
                if r.size_before > 0:
                    ratios.append(saved / r.size_before * 100)
            else:
                elapsed = f"{r.elapsed:.1f}s"
                lines.append(f"❌  {name}  {elapsed}")
                lines.append(f"    錯誤：{r.error}")

        ok = sum(1 for r in self._last_results if r.success)
        total = len(self._last_results)
        cpu_elapsed = sum(r.elapsed for r in self._last_results)
        wall_elapsed = getattr(self, "_last_wall_elapsed", 0.0)
        lines += ["", "[統計摘要]", f"成功：{ok} / {total}"]
        if total_saved > 0:
            avg_ratio = sum(ratios) / len(ratios) if ratios else 0
            lines.append(f"總計節省：{format_size(total_saved)}（平均 -{avg_ratio:.0f}%）")
        lines.append(f"實際耗時：{wall_elapsed:.1f}s")
        if cpu_elapsed > wall_elapsed * 1.2:
            lines.append(f"CPU 總時間：{cpu_elapsed:.1f}s（並行壓縮）")

        return "\n".join(lines) + "\n"

    def _export_log(self):
        if not self._last_results:
            return
        default_name = f"compress_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        path = filedialog.asksaveasfilename(
            title="儲存壓縮日誌",
            defaultextension=".txt",
            filetypes=[("文字檔案", "*.txt"), ("所有檔案", "*.*")],
            initialfile=default_name,
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self._generate_log_text())

    def _clear_results(self):
        self._result_box.configure(state="normal")
        self._result_box.delete("1.0", "end")
        self._result_box.configure(state="disabled")

    def _append_result(self, text: str):
        self._result_box.configure(state="normal")
        self._result_box.insert("end", text)
        self._result_box.see("end")
        self._result_box.configure(state="disabled")
