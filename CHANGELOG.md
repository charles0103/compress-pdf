# Changelog

### ✨ 2026-04-27 - 雙窗格版面 + 停止壓縮 + 修正權限錯誤靜默問題
**影響範圍**: `gui/widgets.py`、`gui/main_window.py`、`core/compressor.py`
**解決**:
- 新增 `CTkSplitter`（純 CTk 雙窗格分割器，水平 / 垂直雙用，把手 hover 轉青色，主題自動跟隨）
- `_build_ui` 改為左右兩欄：左側放 DropZone / 選項 / 輸出 / 動作列，右側用垂直 `CTkSplitter` 上放已選檔案、下放壓縮結果
- 視窗預設 `1100×720`、最小 `960×600`；`_list_scroll` 與 `_result_box` 移除固定高度改 `sticky="nsew"` 填滿父窗格
- `compress_file` 把 `default_output_path`（內含 `os.makedirs`）與 `os.path.getsize` 包進 try/except，遇到 `PermissionError` 不再炸到 worker thread；`compress_batch` 加第二道防護
- `compress_batch` 新增 `should_cancel: Callable[[], bool]` 參數，每檔開始前檢查；`_start_compress` 按鈕改為雙態（紅色「⏹ 停止壓縮」），按下設定 `_cancel_requested` flag 停止後續檔案
**成果**: ✅ 已選檔案 / 壓縮結果可拖拉調整高度，不再被擠壓；網路磁碟權限錯誤正確顯示在結果區；長批次可中途停止

### ✨ 2026-04-27 - 已選檔案標題顯示總數
**影響範圍**: `gui/main_window.py`
**解決**: 標題 label 改為 `_file_count_label`，新增 `_update_file_count()` 在 `_add_file` / `_remove_file` / `_clear_files` 三處呼叫；有檔案時顯示「已選檔案  共 N 個」，無檔案時還原為「已選檔案」
**成果**: ✅ 使用者可一眼掌握當前選擇的檔案數量

### ⚡ 2026-04-27 - 大量檔案載入不再卡住 GUI
**影響範圍**: `gui/main_window.py`、`gui/widgets.py`
**解決**: 拖放 / 瀏覽選檔改為背景執行緒讀取 metadata（`os.path.getsize` / `isdir` 全部移到 worker），主執行緒只做字串去重與副檔名過濾；每 10 筆 widget 透過 `after(0, …)` 回主執行緒分批建立，搭配 `update_idletasks()` 強制重繪。`FileListItem` 接受 `size_bytes` 參數避免重複 stat。載入進度以青色字顯示在 DropZone（`show_loading` / `reset_idle`），同步寫入 `_progress_label`
**成果**: ✅ 從網路磁碟拖入 400 個檔案不再出現「沒有回應」；DropZone 即時顯示「⏳ 載入中 N / Total …」遞增

### 🎨 2026-04-27 - 壓縮模式選擇器改為分段按鈕
**影響範圍**: `gui/main_window.py`
**解決**: 將三個外觀相似的 `CTkRadioButton` 替換為 `CTkSegmentedButton`，選中項以青藍色填滿背景，未選中項維持深灰底，視覺對比明顯；保留 `_mode_var` 整數邏輯，設定存讀同步更新
**成果**: ✅ 使用者可立即辨識目前選擇的壓縮模式

### ♻️ 2026-04-27 - 重構降採樣邏輯，修正 PPTX 壓縮無效問題
**影響範圍**: `core/_image_utils.py`（新增）、`core/jpg_compressor.py`、`core/pptx_compressor.py`
**解決**: 新增共用模組 `_image_utils.py`，分離兩種降採樣策略：JPG 依 DPI metadata（`resample_by_dpi`）、PPTX 依像素長邊（`resample_by_max_px`）。PPTX 內嵌圖片通常不帶 DPI metadata，舊邏輯幾乎不觸發降採樣；改為以目標 DPI × 13.33 英寸換算最大像素數（16:9 寬螢幕基準），模式 2/3 現在有實際壓縮效果
**成果**: ✅ PPTX 模式 2/3 降採樣正常觸發；移除重複的 `_maybe_resample` 實作

## ✨ 2026-04-27 - 新增 PPTX 壓縮支援

新增 `core/pptx_compressor.py`，以 `zipfile` + `Pillow` 實作三種壓縮模式（ZIP 重壓、降採樣、強制重編碼），不需新增任何依賴。開檔對話框、拖放、分析功能一併更新以支援 `.pptx`；`.ppt` 舊格式顯示提示訊息。
**詳細記錄**：[changelogs/2026-04/04-27-pptx-support.md](changelogs/2026-04/04-27-pptx-support.md)

### 🐛 2026-04-27 - 修復保留原始檔名勾選狀態與輸出路徑不同步
**影響範圍**: `gui/main_window.py`
**解決**: 補加取消勾選時還原邏輯；`_load_settings()` 末尾呼叫 `_on_keep_filename_change()` 確保啟動時顯示一致
**成果**: ✅ 勾選狀態與輸出路徑欄位在所有情境下保持同步

### 💬 2026-04-27 - 拖入資料夾時顯示提示訊息
**影響範圍**: `gui/main_window.py`
**解決**: `_on_drop()` 偵測到資料夾時於結果區顯示 `⚠️ 不支援拖入資料夾，請直接拖入檔案。`
**成果**: ✅ 使用者誤拖資料夾時有明確回饋，不再靜默略過

### ✨ 2026-04-27 - 新增壓縮日誌匯出功能
**影響範圍**: `gui/main_window.py`
**解決**: 壓縮完成後在結果區標題列顯示「📋 匯出日誌」按鈕（初始 disabled，完成後啟用）；點擊後開啟儲存對話框，將當次結果輸出為 UTF-8 txt，內含時間、設定、每個檔案結果與統計摘要
**成果**: ✅ 大量檔案壓縮後可一鍵匯出當次完整日誌，重新壓縮時自動清除舊結果

### ✨ 2026-04-27 - 科技感 UI 視覺強化
**影響範圍**: `gui/widgets.py`、`gui/main_window.py`
**解決**:
- 新增 `GradientDivider`：標題下方青色漸層分隔線（`#00D1FF`，兩端淡出）
- 新增 `AnimatedBorderFrame`：滑鼠懸停時邊框 ~180ms 漸變為青色（深色模式）
- `DropZone` 拖入時邊框循環閃爍、文字改為「⬇ 放開以加入檔案」
- 按鈕、Slider、CheckBox、OptionMenu 全面改用青色 accent 配色
- 全介面字型更換為 Segoe UI
**成果**: ✅ 深色模式下呈現 HUD 科技感，淺色模式保持可讀性

### ✨ 2026-04-27 - 新增設定記憶功能
**影響範圍**: 壓縮模式、DPI、圖片品質、保留日期、保留檔名、輸出資料夾、主題
**解決**: 新增 `utils/settings.py`，關閉視窗時將所有參數儲存至 `%APPDATA%\compress-pdf\settings.json`，下次啟動自動還原
**成果**: ✅ 使用者不需每次重新設定參數，exe 打包後同樣有效

### 💄 2026-04-27 - DPI 選單顯示用途說明
**影響範圍**: 圖片解析度下拉選單
**解決**: 將 DPI 選項標籤改為附加用途說明（如 `150 DPI（一般文件）`、`72 DPI（網頁）`），協助使用者快速判斷適合的解析度
**成果**: ✅ 不需額外輔助文字即可了解各 DPI 對應情境

## ✨ 2026-04-24 - 新增 JPG 圖檔壓縮支援

新增 `core/jpg_compressor.py`，以 Pillow 實作三種壓縮模式（optimize 重編、降採樣、低品質強制重編），自動保留 EXIF。開檔對話框、拖放、分析功能一併更新以支援 `.jpg` / `.jpeg`。
**詳細記錄**：[changelogs/2026-04/04-24-jpg-support.md](changelogs/2026-04/04-24-jpg-support.md)

### ✨ 2026-04-24 - 新增全部清除按鈕
**影響範圍**: 已選檔案列表
**解決**: 在「已選檔案」標題列右側加入「全部清除」按鈕，一鍵移除所有已選檔案
**成果**: ✅ 壓縮完成後無需逐一點擊 ✕ 清除檔案

### 🐛 2026-04-24 - 修正淺色主題下按鈕圖示對比不足
**影響範圍**: 主題切換按鈕、檔案列表移除按鈕
**解決**: 加入 `text_color` 元組讓圖示顏色隨主題調整；主題切換按鈕額外加上細邊框
**成果**: ✅ 淺色與深色主題下圖示皆清晰可見

## 2026-04-23 - 修正 DPI 與圖片品質參數實際不生效

### 🐛 問題修復

- **[影響範圍]**: UI 上的圖片解析度 DPI 與圖片品質滑桿在多數情境下並未實際影響輸出檔案大小
- **根因**:
  1. DPI 估算以硬寫 Letter（8.5×11 吋）為基礎，未讀取頁面實際尺寸與圖片 CTM
  2. 當圖片尺寸未超過「整頁像素估算」時，程式碼直接 return，品質參數完全未套用
- **解決**:
  - 使用 `pikepdf.models.ctm.get_objects_with_ctm()` 取得每張圖片的真實顯示尺寸
  - 以 `effective_dpi = pixel / display_inch` 精確計算，替代 Letter 假設
  - 拆開「降採樣」與「重編碼」流程，模式 3 新增 `force_recompress=True` 讓品質滑桿對所有圖片生效
  - 新增最小尺寸門檻（64px）避免 icon 重編後變大
  - 壓縮等級 slider 改為 disabled（pikepdf 9+ 已自動處理）
- **成果**: ✅ 模式 2 的 DPI 切換、模式 3 的品質滑桿在所有 PDF 上都能實際影響輸出檔案大小
- **詳細記錄**: [changelogs/2026-04/04-23-dpi-quality-fix.md](changelogs/2026-04/04-23-dpi-quality-fix.md)

## 2026-04-23 - 新增圖片解析度分析功能

### ✨ 新增功能

- **[影響範圍]**: 幫助使用者了解 PDF 內嵌圖片的解析度
- **解決**: 新增「📊 分析圖片」按鈕，顯示 DPI 分佈與平均估算值
- **成果**: ✅ 使用者可根據分析結果選擇適當的壓縮設定

### 📋 實作內容

- `core/image_optimizer.py` - 新增 `analyze_pdf_images()` 函數與 `ImageInfo` / `PdfAnalysisResult` 資料結構
- `core/compressor.py` - 新增 `analyze_file()` 入口函數
- `gui/main_window.py` - 新增分析按鈕與 `_analyze_files()` 方法

## 2026-04-23 - UI 修正

### 🐛 問題修復

- **[影響範圍]**: 視窗高度不足，導致「已選檔案」列表被遮住
- **解決**: 增加視窗高度從 780 到 900，並將 frame 改為實例變數避免 GC
- **成果**: ✅ 檔案列表區域可見性改善

## 2026-04-23 - 初始版本

### 新增功能

- **GUI 介面**：customtkinter 現代化視窗，支援深色/淺色主題切換
- **拖放支援**：透過 tkinterdnd2 拖入 PDF 檔案
- **三種壓縮模式**：
  - 無失真模式（pikepdf，零損失）
  - 圖片優化模式（pikepdf + Pillow，DPI 重採樣）
  - 高壓縮模式（降低 DPI + JPEG 品質調整）
- **壓縮等級滑桿**：對應 pikepdf flate 壓縮
- **圖片解析度選單**：300 / 200 / 150 / 96 / 72 DPI
- **圖片品質滑桿**：50–95（JPEG quality）
- **批次處理**：多檔案背景執行緒，即時進度顯示
- **保留原始日期**：壓縮後透過 Windows API `SetFileTime` 還原建立時間與修改時間
- **輸出資料夾選擇**：可指定或與原始檔案同目錄

### 技術選型

| 功能 | 套件 |
|------|------|
| 無失真壓縮 | pikepdf 10.x |
| 圖片重採樣 | pikepdf + Pillow |
| GUI | customtkinter 5.x |
| 拖放 | tkinterdnd2 |
| 日期還原 | ctypes（Windows API） |
