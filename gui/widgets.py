import os
import tkinter as tk
import customtkinter as ctk

# Sci-fi colour constants
_CYAN        = "#00D1FF"
_CYAN_MID    = "#008FAD"
_BORDER_IDLE = "#2E2E2E"
_CARD        = "#1E1E1E"


def _lerp(c1: str, c2: str, t: float) -> str:
    r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
    r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
    return (
        f"#{int(r1 + (r2 - r1) * t):02x}"
        f"{int(g1 + (g2 - g1) * t):02x}"
        f"{int(b1 + (b2 - b1) * t):02x}"
    )


class GradientDivider(tk.Canvas):
    """青色橫向漸層分隔線（兩端淡出）。主題切換後呼叫 _draw() 刷新。"""

    def __init__(self, master, **kwargs):
        kwargs.setdefault("height", 2)
        kwargs.setdefault("highlightthickness", 0)
        kwargs.setdefault("bd", 0)
        super().__init__(master, **kwargs)
        self.bind("<Configure>", self._draw)
        self.after(50, self._draw)

    def _draw(self, _=None):
        self.delete("all")
        w = self.winfo_width()
        if w <= 1:
            return
        dark = ctk.get_appearance_mode() == "Dark"
        self.configure(bg="#212121" if dark else "#EBEBEB")
        steps = max(w, 80)
        for i in range(steps):
            t = i / steps
            alpha = 4 * t * (1 - t)
            if dark:
                g = int(0xD1 * alpha)
                b = int(0xFF * alpha)
                color = f"#00{g:02x}{b:02x}"
            else:
                v = int(220 - 160 * alpha)
                color = f"#{v:02x}{v:02x}{v:02x}"
            x1 = int(w * i / steps)
            x2 = int(w * (i + 1) / steps) + 1
            self.create_rectangle(x1, 0, x2, 2, fill=color, outline="")


class AnimatedBorderFrame(ctk.CTkFrame):
    """滑鼠懸停時邊框從暗灰平滑漸變為青色的 CTkFrame（深色模式有效）。"""

    _STEPS    = 12
    _INTERVAL = 15

    def __init__(self, master, **kwargs):
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", _BORDER_IDLE)
        super().__init__(master, **kwargs)
        self._step_n   = 0
        self._going_in = False
        self._job      = None
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _on_enter(self, _=None):
        self._going_in = True
        self._schedule()

    def _on_leave(self, _=None):
        self.after(40, self._deferred_leave)

    def _deferred_leave(self):
        mx = self.winfo_pointerx() - self.winfo_rootx()
        my = self.winfo_pointery() - self.winfo_rooty()
        if 0 <= mx < self.winfo_width() and 0 <= my < self.winfo_height():
            return
        self._going_in = False
        self._schedule()

    def _schedule(self):
        if self._job:
            self.after_cancel(self._job)
        self._tick()

    def _tick(self):
        target = self._STEPS if self._going_in else 0
        if self._step_n == target:
            return
        self._step_n += 1 if self._going_in else -1
        if ctk.get_appearance_mode() == "Dark":
            t = self._step_n / self._STEPS
            self.configure(border_color=_lerp(_BORDER_IDLE, _CYAN, t))
        self._job = self.after(self._INTERVAL, self._tick)


class CTkSplitter(ctk.CTkFrame):
    """純 CTk 雙窗格分割器，支援水平 / 垂直方向。

    使用方式：
        s = CTkSplitter(parent, orient="horizontal", a_initial=430, a_min=380, b_min=360)
        # 把內容放進 s.pane_a 與 s.pane_b
    把手 hover 時轉青色，可拖動以調整 pane_a 的尺寸；pane_b 以 weight=1 吃掉剩餘。
    """

    _GRIP_THICKNESS = 6
    _IDLE   = ("gray70", _BORDER_IDLE)
    _ACTIVE = ("gray50", _CYAN)

    def __init__(self, master, orient: str = "horizontal",
                 a_initial: int = 400, a_min: int = 200, b_min: int = 200, **kwargs):
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(master, **kwargs)
        self._orient = orient
        self._a_min  = a_min
        self._b_min  = b_min

        self.pane_a = ctk.CTkFrame(self, fg_color="transparent")
        self.pane_b = ctk.CTkFrame(self, fg_color="transparent")
        self.grip   = ctk.CTkFrame(self, fg_color=self._IDLE, corner_radius=0)

        if orient == "horizontal":
            self.grid_rowconfigure(0, weight=1)
            self.grid_columnconfigure(0, weight=0, minsize=a_initial)
            self.grid_columnconfigure(1, weight=0, minsize=self._GRIP_THICKNESS)
            self.grid_columnconfigure(2, weight=1, minsize=b_min)
            self.pane_a.grid(row=0, column=0, sticky="nsew")
            self.grip.configure(width=self._GRIP_THICKNESS, cursor="sb_h_double_arrow")
            self.grip.grid(row=0, column=1, sticky="ns")
            self.pane_b.grid(row=0, column=2, sticky="nsew")
        else:
            self.grid_columnconfigure(0, weight=1)
            self.grid_rowconfigure(0, weight=0, minsize=a_initial)
            self.grid_rowconfigure(1, weight=0, minsize=self._GRIP_THICKNESS)
            self.grid_rowconfigure(2, weight=1, minsize=b_min)
            self.pane_a.grid(row=0, column=0, sticky="nsew")
            self.grip.configure(height=self._GRIP_THICKNESS, cursor="sb_v_double_arrow")
            self.grip.grid(row=1, column=0, sticky="ew")
            self.pane_b.grid(row=2, column=0, sticky="nsew")

        self.grip.bind("<Enter>",     lambda _: self.grip.configure(fg_color=self._ACTIVE))
        self.grip.bind("<Leave>",     lambda _: self.grip.configure(fg_color=self._IDLE))
        self.grip.bind("<B1-Motion>", self._on_drag)

    def _on_drag(self, event):
        if self._orient == "horizontal":
            pos   = self.grip.winfo_rootx() + event.x - self.winfo_rootx()
            total = self.winfo_width()
            pos   = max(self._a_min, min(total - self._b_min - self._GRIP_THICKNESS, pos))
            self.grid_columnconfigure(0, minsize=pos)
        else:
            pos   = self.grip.winfo_rooty() + event.y - self.winfo_rooty()
            total = self.winfo_height()
            pos   = max(self._a_min, min(total - self._b_min - self._GRIP_THICKNESS, pos))
            self.grid_rowconfigure(0, minsize=pos)


class FileListItem(ctk.CTkFrame):
    """檔案列表中的單一條目，顯示檔名、大小與移除按鈕。"""

    def __init__(self, master, file_path: str, on_remove, size_bytes: int | None = None, **kwargs):
        super().__init__(master, **kwargs)
        self.file_path = file_path
        self.configure(
            fg_color=("gray88", _CARD),
            border_width=1,
            border_color=("gray75", _BORDER_IDLE),
            corner_radius=6,
        )

        name    = os.path.basename(file_path)
        if size_bytes is None:
            size_bytes = os.path.getsize(file_path)
        size_mb = size_bytes / 1024 ** 2

        self.label = ctk.CTkLabel(
            self,
            text=f"  {name}  ({size_mb:.1f} MB)",
            anchor="w",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=("gray20", "#BBBBBB"),
        )
        self.label.pack(side="left", fill="x", expand=True, padx=(6, 0), pady=4)

        self.btn_remove = ctk.CTkButton(
            self,
            text="✕",
            width=28, height=24,
            fg_color="transparent",
            hover_color=("gray80", "#3A1515"),
            text_color=("gray40", "#666666"),
            border_width=0,
            command=lambda: on_remove(file_path),
        )
        self.btn_remove.pack(side="right", padx=4, pady=4)


class DropZone(ctk.CTkButton):
    """拖放 / 點擊選檔區域，拖入時顯示青色掃描閃爍動畫。

    使用 CTkButton 而非 CTkFrame：CTkFrame 以內部 canvas 渲染，
    Python 層的 bind("<Button-1>") 無法接收滑鼠事件；
    CTkButton 的 command 參數天然支援點擊，不需額外 binding。
    """

    _SCAN_COLORS = [_CYAN, _CYAN_MID, "#005566", _CYAN_MID]
    _IDLE_TEXT   = "📂  將 PDF / JPG / PPTX 拖放至此，或點擊選擇檔案"
    _SCAN_TEXT   = "⬇  放開以加入檔案"

    def __init__(self, master, on_click, **kwargs):
        super().__init__(
            master,
            text=self._IDLE_TEXT,
            command=on_click,
            fg_color=("gray85", "#111111"),
            hover_color=("gray78", "#0D1F26"),
            border_color=("gray65", _CYAN),
            border_width=1,
            corner_radius=10,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=("gray40", "#777777"),
            height=64,
            **kwargs,
        )
        self._scanning  = False
        self._scan_step = 0
        self._scan_job  = None

    def start_scan(self):
        """開始拖放掃描動畫。"""
        self._scanning  = True
        self._scan_step = 0
        self._scan_cycle()

    def stop_scan(self):
        """停止掃描動畫，還原外觀。"""
        self._scanning = False
        if self._scan_job:
            self.after_cancel(self._scan_job)
            self._scan_job = None
        self.configure(
            border_color=("gray65", _CYAN),
            text=self._IDLE_TEXT,
            text_color=("gray40", "#777777"),
        )

    def show_loading(self, text: str):
        """顯示載入進度（使用青色字以確保深色模式下也清楚可見）。"""
        self._scanning = False
        if self._scan_job:
            self.after_cancel(self._scan_job)
            self._scan_job = None
        self.configure(
            border_color=("gray65", _CYAN),
            text=text,
            text_color=("gray10", _CYAN),
        )

    def reset_idle(self):
        """還原為閒置狀態文字。"""
        self.configure(
            border_color=("gray65", _CYAN),
            text=self._IDLE_TEXT,
            text_color=("gray40", "#777777"),
        )

    def _scan_cycle(self):
        if not self._scanning:
            return
        color = self._SCAN_COLORS[self._scan_step % len(self._SCAN_COLORS)]
        self.configure(
            border_color=color,
            text=self._SCAN_TEXT,
            text_color=("gray20", _CYAN),
        )
        self._scan_step += 1
        self._scan_job = self.after(160, self._scan_cycle)
