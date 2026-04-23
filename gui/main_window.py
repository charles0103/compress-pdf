import os
import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk
from tkinterdnd2 import DND_FILES, TkinterDnD

from core.compressor import CompressOptions, CompressResult, compress_batch, analyze_file
from utils.file_utils import format_size, size_delta_str
from gui.widgets import DropZone, FileListItem


DPI_OPTIONS = ["300 DPI", "200 DPI", "150 DPI", "96 DPI", "72 DPI"]
_DPI_MAP = {opt: int(opt.split()[0]) for opt in DPI_OPTIONS}


class MainWindow(ctk.CTk, TkinterDnD.DnDWrapper):
    """PDF 壓縮工具主視窗。"""

    def __init__(self):
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self)

        self.title("PDF 壓縮工具")
        self.geometry("620x900")
        self.minsize(520, 680)
        self.resizable(True, True)

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self._file_paths: list[str] = []
        self._file_items: dict[str, FileListItem] = {}
        self._is_running = False

        self._build_ui()

        # 整個視窗與 DropZone 都接受拖放
        self.drop_target_register(DND_FILES)
        self.dnd_bind("<<Drop>>", self._on_drop)
        self._drop_zone.drop_target_register(DND_FILES)
        self._drop_zone.dnd_bind("<<Drop>>", self._on_drop)

    # ── UI 建構 ──────────────────────────────────────────────────

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_drop_zone()
        self._build_file_list()
        self._build_options()
        self._build_output_row()
        self._build_action_row()
        self._build_results()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 0))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="PDF 壓縮工具",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, sticky="w")

        self._theme_btn = ctk.CTkButton(
            header,
            text="🌙",
            width=36,
            height=28,
            fg_color="transparent",
            hover_color=("gray80", "gray30"),
            command=self._toggle_theme,
        )
        self._theme_btn.grid(row=0, column=1, sticky="e")

    def _build_drop_zone(self):
        self._drop_zone = DropZone(self, on_click=self._browse_files)
        self._drop_zone.grid(row=1, column=0, sticky="ew", padx=16, pady=(10, 4))

    def _build_file_list(self):
        self._file_list_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._file_list_frame.grid(row=2, column=0, sticky="ew", padx=16, pady=0)
        self._file_list_frame.grid_columnconfigure(0, weight=1)
        self._file_list_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self._file_list_frame,
            text="已選檔案",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray60"),
        ).grid(row=0, column=0, sticky="w", pady=(4, 2))

        self._list_scroll = ctk.CTkScrollableFrame(
            self._file_list_frame, height=180, fg_color=("gray92", "gray16")
        )
        self._list_scroll.grid(row=1, column=0, sticky="nsew", pady=(0, 4))
        self._list_scroll.grid_columnconfigure(0, weight=1)

    def _build_options(self):
        opt_frame = ctk.CTkFrame(self)
        opt_frame.grid(row=3, column=0, sticky="ew", padx=16, pady=(10, 0))
        opt_frame.grid_columnconfigure((0, 1), weight=1)

        # 壓縮模式
        ctk.CTkLabel(opt_frame, text="壓縮模式", font=ctk.CTkFont(size=12)).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(10, 4)
        )
        self._mode_var = tk.IntVar(value=1)
        modes = [("無失真", 1), ("圖片優化", 2), ("高壓縮", 3)]
        mode_row = ctk.CTkFrame(opt_frame, fg_color="transparent")
        mode_row.grid(row=1, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 6))
        for label, val in modes:
            ctk.CTkRadioButton(
                mode_row,
                text=label,
                variable=self._mode_var,
                value=val,
                command=self._on_mode_change,
            ).pack(side="left", padx=8)

        # 壓縮等級（pikepdf 9+ 已自動最佳化，此 slider 僅保留 UI 一致性）
        ctk.CTkLabel(
            opt_frame, text="壓縮等級（自動）", font=ctk.CTkFont(size=12)
        ).grid(row=2, column=0, sticky="w", padx=12, pady=(6, 0))
        self._level_label = ctk.CTkLabel(opt_frame, text="9", font=ctk.CTkFont(size=12))
        self._level_label.grid(row=2, column=1, sticky="e", padx=12)

        self._level_slider = ctk.CTkSlider(
            opt_frame, from_=1, to=9, number_of_steps=8,
            command=self._on_level_change,
            state="disabled",
        )
        self._level_slider.set(9)
        self._level_slider.grid(row=3, column=0, columnspan=2, sticky="ew", padx=12, pady=(2, 8))

        # 圖片解析度（僅對超過目標 DPI 的圖片降採樣，不會升採樣）
        ctk.CTkLabel(
            opt_frame, text="圖片解析度（降採樣上限）", font=ctk.CTkFont(size=12)
        ).grid(row=4, column=0, sticky="w", padx=12, pady=(4, 0))
        self._dpi_menu = ctk.CTkOptionMenu(
            opt_frame, values=DPI_OPTIONS, width=120,
            command=lambda _: None,
        )
        self._dpi_menu.set("150 DPI")
        self._dpi_menu.grid(row=4, column=1, sticky="e", padx=12, pady=(4, 0))

        # 圖片品質（越低壓縮率越高）
        ctk.CTkLabel(
            opt_frame, text="圖片品質（越低檔案越小）", font=ctk.CTkFont(size=12)
        ).grid(row=5, column=0, sticky="w", padx=12, pady=(8, 0))
        self._quality_label = ctk.CTkLabel(opt_frame, text="75", font=ctk.CTkFont(size=12))
        self._quality_label.grid(row=5, column=1, sticky="e", padx=12)

        self._quality_slider = ctk.CTkSlider(
            opt_frame, from_=50, to=95, number_of_steps=45,
            command=self._on_quality_change,
        )
        self._quality_slider.set(75)
        self._quality_slider.grid(row=6, column=0, columnspan=2, sticky="ew", padx=12, pady=(2, 10))

        # 保留原始日期
        self._preserve_dates_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            opt_frame,
            text="保留原始檔案建立/修改日期",
            variable=self._preserve_dates_var,
            font=ctk.CTkFont(size=12),
        ).grid(row=7, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 4))

        # 保留原始檔名
        self._keep_filename_var = tk.BooleanVar(value=False)
        self._keep_filename_cb = ctk.CTkCheckBox(
            opt_frame,
            text="保留原始檔名（輸出至 compressed/ 子資料夾）",
            variable=self._keep_filename_var,
            font=ctk.CTkFont(size=12),
            command=self._on_keep_filename_change,
        )
        self._keep_filename_cb.grid(row=8, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 10))

        self._on_mode_change()

    def _build_output_row(self):
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.grid(row=4, column=0, sticky="ew", padx=16, pady=(8, 0))
        row.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(row, text="輸出資料夾", font=ctk.CTkFont(size=12)).grid(
            row=0, column=0, sticky="w"
        )
        inner = ctk.CTkFrame(row, fg_color="transparent")
        inner.grid(row=1, column=0, sticky="ew")
        inner.grid_columnconfigure(0, weight=1)

        self._output_dir_var = tk.StringVar(value="（與原始檔案相同目錄）")
        ctk.CTkEntry(
            inner,
            textvariable=self._output_dir_var,
            state="readonly",
            font=ctk.CTkFont(size=11),
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))

        ctk.CTkButton(
            inner, text="瀏覽", width=60, command=self._browse_output
        ).grid(row=0, column=1)

        ctk.CTkButton(
            inner, text="清除", width=60,
            fg_color="transparent",
            border_width=1,
            command=lambda: self._output_dir_var.set("（與原始檔案相同目錄）"),
        ).grid(row=0, column=2, padx=(4, 0))

    def _build_action_row(self):
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.grid(row=5, column=0, sticky="ew", padx=16, pady=(12, 0))
        row.grid_columnconfigure(0, weight=1)
        row.grid_columnconfigure(1, weight=0)

        self._btn_analyze = ctk.CTkButton(
            row, text="📊 分析圖片", height=36,
            font=ctk.CTkFont(size=12),
            command=self._analyze_files,
        )
        self._btn_analyze.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self._btn_start = ctk.CTkButton(
            row, text="開始壓縮", height=36,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._start_compress,
        )
        self._btn_start.grid(row=0, column=1, sticky="ew")

        self._progress_bar = ctk.CTkProgressBar(row)
        self._progress_bar.set(0)
        self._progress_bar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        self._progress_label = ctk.CTkLabel(
            row, text="", font=ctk.CTkFont(size=11), text_color=("gray50", "gray50")
        )
        self._progress_label.grid(row=2, column=0, columnspan=2, sticky="w", pady=(2, 0))

    def _build_results(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=6, column=0, sticky="nsew", padx=16, pady=(10, 14))
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(6, weight=0)

        ctk.CTkLabel(
            frame, text="壓縮結果",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray60"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))

        self._result_box = ctk.CTkTextbox(
            frame, height=100, font=ctk.CTkFont(family="Consolas", size=11),
            state="disabled",
        )
        self._result_box.grid(row=1, column=0, sticky="ew")

    # ── 事件處理 ─────────────────────────────────────────────────

    def _toggle_theme(self):
        current = ctk.get_appearance_mode()
        new_mode = "Dark" if current == "Light" else "Light"
        ctk.set_appearance_mode(new_mode)
        self._theme_btn.configure(text="☀️" if new_mode == "Dark" else "🌙")

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
        # 勾選保留原始檔名時，提示使用者輸出目錄的行為
        if self._keep_filename_var.get():
            output_dir = self._output_dir_var.get()
            if output_dir == "（與原始檔案相同目錄）":
                self._output_dir_var.set("（自動建立 compressed/ 子資料夾）")

    def _browse_files(self):
        paths = filedialog.askopenfilenames(
            title="選擇 PDF 檔案",
            filetypes=[("PDF 檔案", "*.pdf"), ("所有檔案", "*.*")],
        )
        for p in paths:
            self._add_file(p)

    def _browse_output(self):
        folder = filedialog.askdirectory(title="選擇輸出資料夾")
        if folder:
            self._output_dir_var.set(folder)

    def _on_drop(self, event):
        raw = event.data or ""
        try:
            paths = self.tk.splitlist(raw)
        except Exception:
            # splitlist 失敗時手動清理大括號後以空白分割
            paths = [p.strip("{}") for p in raw.split()]
        for p in paths:
            p = p.strip()
            if p.lower().endswith(".pdf") and os.path.isfile(p):
                self._add_file(p)

    def _add_file(self, path: str):
        if path in self._file_paths:
            return
        if not os.path.isfile(path):
            return
        try:
            item = FileListItem(
                self._list_scroll,
                file_path=path,
                on_remove=self._remove_file,
            )
        except Exception as exc:
            self._append_result(f"⚠️  無法載入 {os.path.basename(path)}：{exc}\n")
            return
        self._file_paths.append(path)
        item.grid(
            row=len(self._file_items),
            column=0,
            sticky="ew",
            pady=2,
        )
        self._file_items[path] = item
        self._list_scroll.grid_columnconfigure(0, weight=1)

    def _remove_file(self, path: str):
        if path in self._file_items:
            self._file_items[path].destroy()
            del self._file_items[path]
        if path in self._file_paths:
            self._file_paths.remove(path)

    def _analyze_files(self):
        """分析選取的 PDF 檔案圖片解析度"""
        if not self._file_paths:
            self._append_result("⚠️  請先選擇至少一個 PDF 檔案。\n")
            return

        self._clear_results()
        self._append_result("📊 圖片解析度分析\n")
        self._append_result("─" * 30 + "\n")

        for path in self._file_paths:
            result = analyze_file(path)
            if result is None:
                self._append_result(f"❌ 無法分析：{os.path.basename(path)}\n")
                continue

            name = os.path.basename(path)
            self._append_result(f"\n📄 {name}\n")
            self._append_result(f"   頁數：{result.page_count}，圖片數：{result.total_images}\n")

            if result.dpi_distribution:
                self._append_result("   DPI 分佈：\n")
                for dpi in sorted(result.dpi_distribution.keys(), reverse=True):
                    count = result.dpi_distribution[dpi]
                    self._append_result(f"     {dpi} DPI：{count} 張\n")

            # 計算平均 DPI
            total_px = sum(img.width * img.height for img in result.images)
            if result.images:
                avg_dpi = sum(img.dpi for img in result.images) / len(result.images)
                self._append_result(f"   平均估算 DPI：{avg_dpi:.0f}\n")

        self._append_result("\n" + "─" * 30 + "\n")
        self._append_result("💡 建議：設定低於平均 DPI 的目標解析度可獲得較佳壓縮效果\n")

    def _start_compress(self):
        if self._is_running:
            return
        if not self._file_paths:
            self._append_result("⚠️  請先選擇至少一個 PDF 檔案。\n")
            return

        output_dir = self._output_dir_var.get()
        if output_dir in ("（與原始檔案相同目錄）", "（自動建立 compressed/ 子資料夾）"):
            output_dir = ""

        opts = CompressOptions(
            mode=self._mode_var.get(),
            level=int(round(self._level_slider.get())),
            dpi=_DPI_MAP.get(self._dpi_menu.get(), 150),
            quality=int(round(self._quality_slider.get())),
            output_dir=output_dir,
            preserve_dates=self._preserve_dates_var.get(),
            keep_filename=self._keep_filename_var.get(),
        )

        self._is_running = True
        self._btn_start.configure(state="disabled", text="壓縮中…")
        self._progress_bar.set(0)
        self._clear_results()

        compress_batch(
            file_paths=list(self._file_paths),
            opts=opts,
            on_progress=self._on_file_done,
            on_done=self._on_batch_done,
        )

    def _on_file_done(self, done: int, total: int, result: CompressResult):
        self.after(0, self._update_progress, done, total, result)

    def _update_progress(self, done: int, total: int, result: CompressResult):
        self._progress_bar.set(done / total)
        self._progress_label.configure(text=f"{done} / {total} 個檔案")

        name = os.path.basename(result.input_path)
        if result.success:
            before = format_size(result.size_before)
            after = format_size(result.size_after)
            delta = size_delta_str(result.size_before, result.size_after)
            out_dir = os.path.dirname(result.output_path)
            self._append_result(
                f"✅  {name}\n"
                f"    {before} → {after}  ({delta})\n"
                f"    輸出：{out_dir}\n"
            )
        else:
            self._append_result(f"❌  {name}\n    錯誤：{result.error}\n")

    def _on_batch_done(self, results: list[CompressResult]):
        self.after(0, self._finish_batch, results)

    def _finish_batch(self, results: list[CompressResult]):
        self._is_running = False
        self._btn_start.configure(state="normal", text="開始壓縮")
        ok = sum(1 for r in results if r.success)
        self._progress_label.configure(text=f"完成：{ok}/{len(results)} 個成功")

    def _clear_results(self):
        self._result_box.configure(state="normal")
        self._result_box.delete("1.0", "end")
        self._result_box.configure(state="disabled")

    def _append_result(self, text: str):
        self._result_box.configure(state="normal")
        self._result_box.insert("end", text)
        self._result_box.see("end")
        self._result_box.configure(state="disabled")
