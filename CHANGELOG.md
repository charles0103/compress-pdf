# Changelog

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
