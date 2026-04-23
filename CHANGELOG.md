# Changelog

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
