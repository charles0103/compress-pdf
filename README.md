# PDF 壓縮工具

> Windows 桌面應用程式 — 批次壓縮 PDF / JPG / PPTX，並可解除 PDF 密碼。

以 Python + customtkinter 打造的現代化 GUI 工具，支援拖放、批次處理、多核心並行壓縮，並針對掃描型文件提供精準的 DPI 降採樣。

![版本](https://img.shields.io/badge/version-v1.1-00D1FF) ![平台](https://img.shields.io/badge/platform-Windows-blue)

---

## ✨ 主要功能

- **四種處理模式**：解除密碼、無失真、圖片優化、高壓縮
- **多格式支援**：PDF、JPG / JPEG、PPTX（`.ppt` 舊格式請先另存為 `.pptx`）
- **拖放操作**：可拖入單檔、多檔或整個資料夾（僅第一層）
- **批次與並行**：背景執行緒處理，支援多進程並行壓縮（繞過 GIL）
- **虛擬化檔案清單**：可順暢處理數千個檔案（385 檔載入 30s → 3s）
- **圖片分析**：壓縮前先分析 PDF / JPG / PPTX 內嵌圖片的 DPI 分佈
- **壓縮日誌**：完成後可一鍵匯出 UTF-8 日誌，含設定快照與統計摘要
- **設定記憶**：所有選項自動存入 `%APPDATA%\compress-pdf\settings.json`
- **保留檔案時間戳**：還原原始建立 / 修改時間（Windows API）
- **深色 / 淺色 / 系統主題**，科技感 HUD 視覺風格

---

## 📥 下載安裝（一般使用者）

前往 [Releases](https://github.com/charles0103/compress-pdf/releases/latest) 下載最新版安裝程式：

1. 下載 `PDF壓縮工具_Setup_v{版本}.exe`
2. 執行後依指示安裝（會建立開始功能表與桌面捷徑）
3. 啟動「PDF 壓縮工具」即可使用

> 免安裝 Python 環境，下載即用。

---

## 🗜️ 壓縮模式

| 模式 | 說明 | 適用情境 |
|------|------|----------|
| 🔓 解除密碼 | 開啟加密 PDF 並輸出無密碼版本（不壓縮） | 移除權限限制或開啟密碼 |
| 無失真 | pikepdf 重壓 stream，畫質完全一致 | 文字型 PDF、已最佳化的掃描檔 |
| 圖片優化 | 僅對超過目標 DPI 的圖片降採樣（JPEG 品質固定 95） | 高解析度掃描文件、相機直出 PDF |
| 高壓縮 | 所有圖片以指定品質（50–95）重編碼 + 降採樣 | 純分享、不需精準輸出 |

> ⚠️ 解除密碼功能需提供**正確密碼**，無法破解；請確認您擁有合法處理該檔案的權限。

完整功能說明請見 [`功能說明文件.md`](功能說明文件.md)。

---

## 🛠️ 開發者指南

### 環境需求

- Python 3.13
- Windows（時間戳還原與打包流程依賴 Windows API）

### 安裝與執行

```bash
# 安裝依賴
pip install -r requirements.txt

# 執行應用程式
python main.py
```

### 主要依賴

| 套件 | 用途 |
|------|------|
| pikepdf ≥ 8 | PDF stream 壓縮、圖片 CTM 計算 |
| customtkinter ≥ 5.2 | 現代化 tkinter 主題與元件 |
| tkinterdnd2 ≥ 0.3 | 拖放支援 |
| Pillow | 圖片重採樣（隨 pikepdf 自動安裝） |

### 專案結構

```
main.py                    # 入口：初始化 customtkinter，啟動 MainWindow
gui/
  main_window.py           # 主視窗：UI 建構、事件處理、批次壓縮流程
  widgets.py               # DropZone、VirtualFileList、PasswordDialog 等元件
core/
  compressor.py            # CompressOptions、CompressResult、compress_file/batch
  decrypt.py               # pikepdf 解除 PDF 密碼
  lossless.py              # pikepdf 無失真壓縮
  image_optimizer.py       # pikepdf + Pillow 圖片重採樣
  jpg_compressor.py        # Pillow JPEG 壓縮
  pptx_compressor.py       # zipfile + Pillow PPTX 媒體壓縮
utils/
  file_utils.py            # 路徑生成、大小格式化、時間戳還原
  settings.py              # JSON 設定讀寫
```

---

## 📦 打包與發布

```bash
# 步驟一：PyInstaller 打包（產出 dist/PDF壓縮工具/）
pyinstaller build.spec --clean --noconfirm

# 步驟二：用 Inno Setup Compiler 開啟 installer.iss，按 F9 編譯
#         產出 installer_output/PDF壓縮工具_Setup_v{版本}.exe

# 步驟三：上傳至 GitHub Releases
```

詳細流程與升版需修改的位置請見 [`CLAUDE.md`](CLAUDE.md)。

---

## 📄 授權

本專案由 Charles 開發。
