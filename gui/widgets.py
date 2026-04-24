import os
import customtkinter as ctk


class FileListItem(ctk.CTkFrame):
    """檔案列表中的單一條目，顯示檔名、大小，及移除按鈕。"""

    def __init__(self, master, file_path: str, on_remove, **kwargs):
        super().__init__(master, **kwargs)
        self.file_path = file_path
        self.configure(fg_color=("gray90", "gray20"), corner_radius=6)

        name = os.path.basename(file_path)
        size_mb = os.path.getsize(file_path) / 1024 ** 2

        self.label = ctk.CTkLabel(
            self,
            text=f"  {name}  ({size_mb:.1f} MB)",
            anchor="w",
            font=ctk.CTkFont(size=12),
        )
        self.label.pack(side="left", fill="x", expand=True, padx=(6, 0), pady=4)

        self.btn_remove = ctk.CTkButton(
            self,
            text="✕",
            width=28,
            height=24,
            fg_color="transparent",
            hover_color=("gray80", "gray30"),
            text_color=("gray20", "gray80"),
            command=lambda: on_remove(file_path),
        )
        self.btn_remove.pack(side="right", padx=4, pady=4)


class DropZone(ctk.CTkButton):
    """
    拖放 / 點擊選檔區域。

    使用 CTkButton 而非 CTkFrame：
    CTkFrame 以內部 canvas 渲染，Python 層的 bind("<Button-1>") 無法接收
    滑鼠事件；CTkButton 的 command 參數天然支援點擊，不需額外 binding。
    """

    def __init__(self, master, on_click, **kwargs):
        super().__init__(
            master,
            text="📂  將 PDF 拖放至此，或點擊選擇檔案",
            command=on_click,
            fg_color=("gray85", "gray17"),
            hover_color=("gray78", "gray22"),
            border_color=("gray70", "gray40"),
            border_width=2,
            corner_radius=10,
            font=ctk.CTkFont(size=13),
            text_color=("gray40", "gray60"),
            height=64,
            **kwargs,
        )
