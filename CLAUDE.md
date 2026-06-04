# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# 安裝依賴
pip install -r requirements.txt

# 執行應用程式
python main.py
```

目前無測試套件。

## 打包與發布流程

### 步驟一：PyInstaller 打包
```bash
pyinstaller build.spec --clean --noconfirm
```
產出：`dist/PDF壓縮工具/`（整個資料夾為可攜應用程式）

### 步驟二：Inno Setup 製作安裝程式
1. 用 Inno Setup Compiler 開啟 `installer.iss`
2. 按 F9 編譯
3. 產出：`installer_output/PDF壓縮工具_Setup_v{版本}.exe`

### 步驟三：發布到 GitHub Releases
1. GitHub repo 頁面 → Releases → Draft a new release
2. Tag：`v{版本}`，Title：`PDF 壓縮工具 v{版本}`
3. 上傳 `installer_output/` 裡的 `.exe` 到 Assets
4. Publish release
5. 分享連結：`https://github.com/charles0103/compress-pdf/releases/latest`

### 升版時需修改的地方
- `installer.iss` 第 6 行 `AppVersion`
- `gui/main_window.py` header 的 `text="v{版本}"`

## Architecture

純 Python 的 Windows GUI 工具，無 web 後端。

```
main.py                    # 入口：初始化 customtkinter，啟動 MainWindow
gui/
  main_window.py           # 主視窗：UI 建構、事件處理、批次壓縮流程
  widgets.py               # DropZone（拖放區）、FileListItem（檔案列表條目）
core/
  compressor.py            # CompressOptions、CompressResult、compress_file/compress_batch
  lossless.py              # pikepdf 無失真壓縮
  image_optimizer.py       # pikepdf + Pillow 圖片重採樣（降 DPI / JPEG 重編碼）
utils/
  file_utils.py            # 路徑生成、大小格式化、Windows SetFileTime 時間戳還原
```


## 工具與 MCP 使用規範

- 程式碼探索和編輯**優先使用** Serena MCP 工具（read_file、replace_content、find_symbol、get_symbols_overview 等）
- Serena 工具為 deferred 狀態，**使用前必須先透過 ToolSearch 載入 schema**：
  ```
  ToolSearch: select:mcp__plugin_serena_serena__read_file,mcp__plugin_serena_serena__find_symbol,mcp__plugin_serena_serena__get_symbols_overview,mcp__plugin_serena_serena__search_for_pattern,mcp__plugin_serena_serena__replace_content
  ```
- Serena 已激活時，**禁止**改用標準 Read/Edit 工具；若 Serena 無法激活，才退回使用標準工具
- 大型重構時使用 Serena 的搜尋和替換功能


### 資料流

1. `MainWindow` 收集使用者設定，組成 `CompressOptions`
2. `compress_batch()` 在 daemon 執行緒逐一呼叫 `compress_file()`
3. 每個檔案完成後透過 `self.after(0, callback)` 安全回到 GUI 執行緒更新進度

### 壓縮模式

| mode | 說明 | 呼叫路徑 |
|------|------|----------|
| 0 解除密碼 | 開啟加密 PDF 並輸出無密碼版本（不壓縮） | `decrypt_pdf()` |
| 1 無失真 | pikepdf 重壓串流 | `compress_lossless()` |
| 2 圖片優化 | 降 DPI → lossless | `optimize_images()` → `compress_lossless()` |
| 3 高壓縮 | 降 DPI + 低品質 JPEG → lossless | `optimize_images()` → `compress_lossless()` |

模式 2/3 使用暫存 PDF 作中繼，完成後刪除。

### 重要實作細節

- **DropZone** 用 `CTkButton` 而非 `CTkFrame`：CTkFrame 以內部 canvas 渲染，Python 層的 `bind("<Button-1>")` 無法接收滑鼠事件，`CTkButton.command` 是唯一可靠方式。
- **pikepdf 9+** 移除了 `flate_level` / `recompress_flate`，改以 `compress_streams=True` + `ObjectStreamMode.generate` 達成最佳壓縮；`CompressOptions.level` 保留 UI 顯示用，不影響實際壓縮行為。
- **時間戳還原** 跨平台用 `os.utime()`（mtime/atime），建立時間僅 Windows 支援，透過 `ctypes.windll.kernel32.SetFileTime` 實作（`utils/file_utils.py`）。
- **image_optimizer.py** 跳過 JBIG2、CCITTFax、JPXDecode 等無法安全重編碼的格式，並以 `seen` set 避免重複處理共用圖片物件。

## Dependencies

| 套件 | 用途 |
|------|------|
| pikepdf ≥ 8 | PDF 開啟、串流壓縮、圖片物件存取 |
| pymupdf ≥ 1.24 | 宣告於 requirements，目前核心路徑未直接呼叫 |
| customtkinter ≥ 5.2 | 現代化 tkinter 主題與元件 |
| tkinterdnd2 ≥ 0.3 | 拖放支援（需在 `MainWindow.__init__` 呼叫 `TkinterDnD._require`）|
| Pillow | 圖片重採樣（`image_optimizer.py` 內部使用，未列於 requirements）|
