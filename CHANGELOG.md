# Changelog

### 🐛 2026-04-30 - 修正啟動畫面中文顯示為豆腐方塊
**影響範圍**: `tools/make_splash.py`、`splash.png`
**解決**: 原本字型優先序 Segoe UI 不含 CJK 字形，「壓縮工具」「載入中」皆無法渲染；改為依用途切換字型 — 中文文字使用微軟正黑體（msjhbd.ttc / msjh.ttc），英文保留 Segoe UI
**成果**: ✅ 啟動畫面中文字正確顯示

### ✨ 2026-04-30 - 新增 Splash Screen 啟動畫面
**影響範圍**: `main.py`、`build.spec`、`tools/make_splash.py`、`splash.png`
**解決**: PyInstaller onedir 首次啟動需 4–5 秒（Defender 掃描 + 檔案系統冷快取 + Python 初始化）；新增 `Splash()` 設定，exe 啟動時立即顯示 480×300 載入畫面（深色青藍主題、含「PDF 壓縮工具」標題與「載入中」提示），主視窗就緒後 100ms 透過 `pyi_splash.close()` 關閉
**成果**: ✅ 使用者按下 exe 後 0.5 秒內看到啟動畫面，避免「沒反應」誤判而重複點擊

### 📦 2026-04-30 - 安裝程式發行者改為公司名稱
**影響範圍**: `installer.iss`
**解決**: `AppPublisher` 由 `Charles` 改為 `FU RONG DEVELOPMENT`
**成果**: ✅ 重新編譯後「程式和功能」與安裝程式 UI 顯示公司名稱

### 🐛 2026-04-30 - 修正 build.bat 在 Windows 執行出現「命令語法不正確」
**影響範圍**: `build.bat`、新增 `.gitattributes`
**解決**: `build.bat` 行尾被 git 自動轉為 LF，cmd.exe 解析時將多行指令連成一行而報錯；轉回 CRLF 並新增 `.gitattributes` 強制 `.bat` / `.cmd` / `.ps1` / `.iss` 永遠保持 CRLF
**成果**: ✅ `.\build.bat` 可在 PowerShell 與 cmd 正常執行

### ✨ 2026-04-30 - UI 新增「使用說明」對話框
**影響範圍**: `gui/main_window.py`
**解決**: 標題列右上角新增「❓ 使用說明」按鈕，點擊開啟 `CTkToplevel` 視窗，內含可捲動的 `CTkTextbox` 顯示使用導覽（快速開始、三種壓縮模式適用情境、DPI / 品質建議、檔名樣板範例、並行壓縮建議、FAQ）；重複點擊不會開多個視窗
**成果**: ✅ 新使用者可透過 UI 直接查閱操作說明，不需翻閱外部文件

### 🐛 2026-04-30 - 修正「程式和功能」中卸載項目沒有套用應用程式 icon
**影響範圍**: `installer.iss`
**解決**: `SetupIconFile` 只控制安裝程式 exe 自身的圖示，與 Windows「程式和功能」列表無關；補上 `UninstallDisplayIcon={app}\{#AppExeName}` 與 `UninstallDisplayName`，讓卸載清單讀取 exe 內嵌圖示
**成果**: ✅ 重新編譯安裝程式後，「程式和功能」中正確顯示 PDF 圖示（需先卸載舊版再重裝以更新註冊表）

### 📦 2026-04-29 - 新增 Inno Setup 安裝程式設定 + 更換應用程式 icon
**影響範圍**: `installer.iss`、`app.ico`
**解決**: 建立 Inno Setup 安裝腳本，將 onedir 打包結果封裝成單一安裝程式 exe；更換應用程式 icon 為 PDF 下載圖示
**成果**: ✅ 可產生 `PDF壓縮工具_Setup_v1.0.exe` 安裝程式，支援開始功能表與桌面捷徑


### 🐛 2026-04-29 - 修正其他電腦執行 exe 時 LoadLibrary 失敗
**影響範圍**: `build.spec`
**解決**: `python313.dll` 的 import table 中有 `python3.dll`（stable ABI DLL），原本打包設定未收集此檔案，導致無 Python 環境的電腦出現「Failed to load Python DLL」錯誤；在 `build.spec` 明確將 `python3.dll` 與 `python313.dll` 加入 `binaries`
**成果**: ✅ 其他 Windows 11 電腦可正常執行打包後的 exe

### 📝 2026-04-29 - 功能說明文件更新
**影響範圍**: `功能說明文件.md`
**解決**: 補上拖曳資料夾說明、移除已實作的 P1-3（資料夾支援）、P2-8（檔名樣板）、P2-9（並行壓縮）、剩餘項目重新編號
**成果**: ✅ 文件與目前實作同步

### ✨ 2026-04-29 - 拖曳資料夾支援（僅第一層）
**影響範圍**: `gui/main_window.py`、`gui/widgets.py`
**解決**:
- 拖入資料夾時改以 `os.listdir()` 掃描第一層符合副檔名的檔案（不遞迴），彈出 `tkinter.messagebox.askyesno` 確認對話框，顯示數量後由使用者決定是否加入
- 資料夾內無可壓縮檔案時改顯示具體提示，而非舊訊息「不支援拖入資料夾」
- DropZone 閒置提示文字加入「或資料夾」
**成果**: ✅ 支援拖入資料夾，確認提示防止誤加入大量檔案

### 📦 2026-04-28 - exe 打包準備 + 應用程式 icon
**影響範圍**: `main.py`、`requirements.txt`、`gui/main_window.py`、`build.spec`、`build.bat`、`tools/make_icon.py`、`app.ico`
**解決**:
- `main.py` 加上 `sys.frozen` 偵測，exe 與開發模式都正確設 `sys.path`
- 移除未使用的 `pymupdf` 依賴（節省打包約 200MB），補上 `Pillow`
- 新增 `build.spec`：collect_all tkinterdnd2/customtkinter/pikepdf、hidden_import `pikepdf.models.ctm`、排除 PyQt/matplotlib 等冗餘依賴、`console=False`、onedir 模式（並行壓縮效率最佳）
- 新增 `build.bat` 一鍵打包腳本
- 新增 `tools/make_icon.py` 程式化產生多解析度 `app.ico`（青藍 #00D1FF 主題色，「PDF」字樣 + 壓縮箭頭）
- `MainWindow` 新增 `_apply_window_icon()`，視窗左上角載入 `app.ico`
**成果**: ✅ 打包 exe 啟動不缺資源、ProcessPoolExecutor 並行壓縮可正常運作、視窗與 exe 統一 icon

### ✨ 2026-04-28 - 檔名樣板 UI 簡化 + 停止壓縮真正中斷 + 輸出資料夾邏輯修正
**影響範圍**: `gui/main_window.py`、`core/compressor.py`、`utils/file_utils.py`
**解決**:
- 檔名樣板輸入區新增三顆插入按鈕（`+ 原檔名` / `+ 日期` / `+ 序號`），點擊在游標位置插入對應佔位符；下方加上即時預覽列
- 並行壓縮停止邏輯：取消後立即 `executor.shutdown(wait=False, cancel_futures=True)` 並 `break`，不再等所有執行中的子程序跑完；新增 `CancelledError` 處理
- `default_output_path` 拆解為「決定檔名」與「決定資料夾」兩步：`keep_filename=True` 或產生的檔名與原檔名相同 → 走 `compressed/` 子資料夾；避免 template 凌駕 keep_filename 的子資料夾承諾、避免覆蓋原檔
- 「清除」按鈕改為依 `keep_filename` checkbox 狀態顯示對應 placeholder
- 視窗 geometry 740→770、minsize 720→750，補上預覽列佔用空間
**成果**: ✅ 樣板輸入零學習成本、停止壓縮真的會停、輸出位置與 UI 文字一致

### 🐛 2026-04-28 - 修正底部進度文字被裁切
**影響範圍**: `gui/main_window.py`
**解決**: 預設視窗高度 720→740、最小高度 680→720，確保壓縮完成後進度標籤不被裁切
**成果**: ✅ 進度文字完整顯示，無多餘空白

### ✨ 2026-04-28 - 輸出檔名樣板 + 多進程並行壓縮
**影響範圍**: `core/compressor.py`、`gui/main_window.py`、`utils/file_utils.py`、`utils/settings.py`、`main.py`
**解決**:
- `default_output_path` 新增 `filename_template` / `file_index` 參數，支援 `{name}` `{date}` `{index}` 佔位符
- `CompressOptions` 新增 `filename_template`、`file_index`；`compress_batch` 新增 `max_workers` 參數
- 並行壓縮改用 `ProcessPoolExecutor`（真正多進程，繞過 GIL），`ThreadPoolExecutor` 因 GIL 限制對 CPU 密集壓縮無效
- 模組頂層新增 `_compress_process_worker`（pickle 序列化要求）；`main.py` 加入 `freeze_support()`
- GUI 選項區新增「並行壓縮執行緒」分段按鈕（1 順序 / 2 / 4 / 自動）及「輸出檔名樣板」輸入框
- 壓縮結果區與匯出日誌統一顯示實際壁鐘耗時；並行時額外顯示 CPU 總時間
- 修正日誌匯出時重新計算耗時導致數值錯誤（改存 `_last_wall_elapsed`）
- 左欄版面改為固定顯示（移除捲動框），縮減選項面板 ~60px 間距，最小視窗高度調整為 680px，進度標籤補底部 padding
**成果**: ✅ 多核心機器並行壓縮實際加速；檔名可自訂；壓縮耗時統計正確；左欄全部功能無需捲動

### ✨ 2026-04-28 - 虛擬化檔案清單（10× 載入提速）
**影響範圍**: `gui/widgets.py`、`gui/main_window.py`
**解決**: 新增 `VirtualFileList` widget，內部用 `tk.Canvas + CTkScrollbar` 自行管理捲動，僅 render 可視範圍 + buffer 共 ~10-20 個 `FileListItem`；資料層 `_entries` 持有全部檔案資訊，捲動／resize 時動態建立／銷毀 widget。`MainWindow` 移除 `_file_items` 字典與 `_refresh_scrollbar` 相關邏輯，全面委派給虛擬清單 API
**成果**: ✅ 385 檔載入時間 SSD 30s→3s、網路磁碟 71s→6s；可順暢處理數千個檔案
**詳細**: [changelogs/2026-04/04-28-virtual-file-list.md](changelogs/2026-04/04-28-virtual-file-list.md)

### 🐛 2026-04-28 - 修正 SSD 載入大量檔案無法取消
**影響範圍**: `gui/main_window.py`
**解決**:
- `_consume_loaded_batch` 改用 `update()` 取代 `update_idletasks()`，強制處理待處理的點擊事件（前者只跑重繪、不處理 user input）
- batch for-loop 內加 `_load_cancelled` 檢查，cancel 中途點下立即停止建立 widget
**成果**: ✅ 本地 SSD 載入 385 個檔案也能即時取消

### ✨ 2026-04-28 - 載入大量檔案可即時取消
**影響範圍**: `gui/main_window.py`
**解決**:
- 載入期間「全部清除」按鈕自動切換為「取消載入」（紅色），點下立即中止 worker，已載入的檔案保留
- worker 改為一次只排入一個 batch，透過 `threading.Event` 等主執行緒處理完才繼續，避免事件佇列堆積導致按鈕點擊被卡住
**成果**: ✅ 誤選大量檔案時可立即取消重新選擇

### 🐛 2026-04-28 - 已選檔案捲軸自動隱藏與滾動修復
**影響範圍**: `gui/main_window.py`、`gui/widgets.py`
**解決**:
- `FileListItem` 公開 `size_bytes` 屬性，標題列顯示「已選檔案 共 N 個 / 總容量」（自動切換 MB / GB）
- 改用 `configure(width=0)` 取代 `grid_remove()` 控制捲軸顯示，避免 canvas 寬度變動破壞 `CTkScrollableFrame` 內部 `create_window` 與 scrollregion 同步
- `<Configure>` binding 加上 `add="+"`，避免覆寫 `CTkScrollableFrame` 內建用來更新 scrollregion 的 handler，修正捲軸顯示但無法滾動的問題
**成果**: ✅ 內容溢出時捲軸自動出現且可正常拖動；標題列即時顯示總容量

### ✨ 2026-04-28 - 壓縮耗時記錄
**影響範圍**: `core/compressor.py`、`gui/main_window.py`
**解決**:
- `CompressResult` 新增 `elapsed: float` 欄位；`compress_batch` 以 `time.perf_counter()` 計時每個檔案
- 即時 log 與匯出日誌每筆結果後附上耗時（如 `2.3s`）
- 匯出日誌統計摘要新增「總壓縮時間」
**成果**: ✅ 可快速判斷各檔案壓縮效率

### ✨ 2026-04-28 - 壓縮格式篩選 + 進度百分比
**影響範圍**: `gui/main_window.py`、`gui/widgets.py`、`utils/settings.py`
**解決**:
- 選項區新增「壓縮格式」checkbox（PDF / JPG / PPTX），預設全勾；取消勾選後，已選檔案清單中不符合格式的條目即時變暗，壓縮時自動略過
- 格式勾選狀態寫入 `settings.json`，重啟後還原
- 進度列右側新增青色百分比 label（`0%` → `100%`），開始新批次時清空
**成果**: ✅ 可單獨壓縮指定格式；進度一目瞭然

### 🐛 2026-04-28 - 無檔案時隱藏捲軸
**影響範圍**: `gui/main_window.py`
**解決**: `CTkScrollableFrame` 捲軸預設常駐顯示；改為啟動時呼叫 `_scrollbar.grid_remove()` 初始隱藏，`_update_file_count()` 中依檔案數動態 `grid()` / `grid_remove()`
**成果**: ✅ 已選檔案區空白時不再顯示多餘捲軸

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
