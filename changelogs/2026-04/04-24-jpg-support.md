# 2026-04-24 新增 JPG 圖檔壓縮支援

## 🎯 功能概述

- **影響範圍**：core 壓縮核心、GUI 檔案選取與拖放、分析功能、工具提示文字
- **新增格式**：JPEG（`.jpg`、`.jpeg`）

## ⚡ 實作方案

- `core/jpg_compressor.py`（新增）：以 Pillow 實作三種壓縮模式
  - mode 1：optimize 重編碼，quality 固定 92
  - mode 2：若原始 DPI 超過目標則降採樣，quality 92
  - mode 3：強制以使用者指定 quality 重編碼，超過 DPI 一併降採樣
  - 自動保留 EXIF metadata
  - 自動將 RGBA / P 色彩模式轉為 RGB 再存檔
- `core/compressor.py`：`compress_file()` 依副檔名路由，JPG 走 `compress_jpg()`，PDF 流程不變
- `utils/file_utils.py`：`default_output_path()` 改為保留原始副檔名（`.jpg` → `_compressed.jpg`）
- `gui/main_window.py`：
  - 開檔對話框加入 JPEG 類型篩選
  - 拖放過濾條件加入 `.jpg` / `.jpeg`
  - `_analyze_files()` 對 JPG 顯示尺寸、DPI、檔案大小；PDF 邏輯不變
  - 提示文字「PDF 檔案」→「檔案」
- `gui/widgets.py`：DropZone 提示文字加入 JPG

## ✅ 驗證結果

- 所有模組匯入語法驗證通過（`python -c "import ..."` 無錯誤）
- PDF 壓縮路徑未異動，向下相容

## 📊 修改統計

- 新增：`core/jpg_compressor.py`（49 行）
- 修改：`core/compressor.py`、`gui/main_window.py`、`gui/widgets.py`、`utils/file_utils.py`
- 共 5 個檔案，+62 / -13 行
