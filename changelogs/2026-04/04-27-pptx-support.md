# 2026-04-27 新增 PPTX 壓縮支援與 UI 修復

## 🎯 功能概述

- 新增 PowerPoint `.pptx` 檔案壓縮功能
- 修復「保留原始檔名」勾選狀態與輸出路徑顯示不同步的問題
- 新增拖入資料夾時的提示訊息

## ⚡ 實作方案

### PPTX 壓縮（`core/pptx_compressor.py`）

`.pptx` 本質為 ZIP 包，以 Python 內建 `zipfile` + 既有 `Pillow` 處理，不需新增依賴。

- 模式 1：只以 `ZIP_DEFLATED level=9` 重新打包，不動圖片
- 模式 2：`ppt/media/` 下 JPEG 降採樣至目標 DPI（quality 92）；PNG 只降採樣不轉格式
- 模式 3：所有 JPEG 強制重編碼（使用者指定 quality）+ 降採樣；PNG 同模式 2
- 重壓後若結果變大，保留原始 bytes（`_recompress_image` 內建保護）
- 新增 `analyze_pptx()` 回傳媒體圖片統計（JPEG / PNG / 其他數量、媒體總大小）

### 路由整合（`core/compressor.py`）

- `compress_file()` 加入 `.pptx` 分支
- `.ppt` 舊格式顯示明確錯誤訊息，提示另存為 `.pptx`

### GUI 更新（`gui/main_window.py`、`gui/widgets.py`）

- 開檔對話框加入 `*.pptx` 選項
- 拖放過濾白名單加入 `.pptx`
- 拖入資料夾時在結果區顯示 `⚠️ 不支援拖入資料夾，請直接拖入檔案。`
- 分析功能加入 `_analyze_pptx()`：顯示檔案大小、媒體圖片數量、媒體總大小
- DropZone 文字更新為 `PDF / JPG / PPTX`

## 🐛 Bug 修復

### 保留原始檔名勾選狀態不同步

**根本原因**：`save_settings()` 過濾佔位文字，`output_dir` 儲存為空字串；重新啟動時 `keep_filename=True` 讀回，但輸出路徑欄位未跟著更新。

**修復**：
1. `_on_keep_filename_change()` 補加取消勾選的還原邏輯
2. `_load_settings()` 末尾呼叫 `_on_keep_filename_change()` 確保啟動時顯示同步

## ✅ 驗證結果

- `python -c "import core.pptx_compressor, core.compressor, gui.main_window"` 通過
- 保留原始檔名勾選／取消循環測試正常
- 啟動時勾選狀態與輸出路徑欄位顯示一致

## 📊 修改統計

- 新增：`core/pptx_compressor.py`（96 行）
- 修改：`core/compressor.py`（+7 行）、`gui/main_window.py`（+41/-7 行）、`gui/widgets.py`（+1/-1 行）
