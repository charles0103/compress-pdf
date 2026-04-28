# 2026-04-28 虛擬化檔案清單

## 🎯 功能概述

- 影響範圍：`gui/widgets.py`、`gui/main_window.py`
- 動機：載入 385 個檔案需 71 秒，使用者預期需處理數千個檔案
- 複雜度：中（新增 widget class + 主視窗資料層重構）

## ⚡ 實作方案

### 新增 `VirtualFileList` widget（`gui/widgets.py`）

虛擬化清單的核心設計：

- **資料層**：`_entries: list[(path, size_bytes)]` 持有全部檔案資訊
- **視圖層**：`_items: dict[idx, (FileListItem, canvas_window_id)]` 只保留可視範圍 + 上下各 3 項緩衝
- **捲動容器**：`tk.Canvas + CTkScrollbar`，scrollregion 高度 = `len(entries) * ITEM_HEIGHT`
- **render 流程**：捲動／resize 時計算 `_visible_range()`，移除離開可視區的 widget，為新進入的索引建立 widget 並 `create_window` 放入 canvas

公開 API：`add_entry / remove_entry / clear / set_dimmed_paths / get_paths / total_size / count`

### `main_window.py` 資料層重構

- 移除 `_file_items: dict[str, FileListItem]`（不再保留所有 widget 引用）
- `_list_scroll`（CTkScrollableFrame）替換為 `_file_list`（VirtualFileList）
- `_add_file / _remove_file / _clear_files` 委派給虛擬清單 API
- `_refresh_list_dim` 改為計算 dim path set 後傳給 `set_dimmed_paths()`
- 移除 `_refresh_scrollbar`、`_scrollbar_after_id`（虛擬清單自行管理捲軸顯示）

### 關鍵技術決策

- **保留 `FileListItem` 不改造**：虛擬清單內仍 create / destroy `FileListItem` 實例，犧牲 widget 重用以換取維護性簡化
- **buffer = 3**：可視範圍上下各預先 render 3 項，捲動時不會看到空白
- **ITEM_HEIGHT = 38**：FileListItem 內容 32px + pady 6px，與原本 grid pady=2 視覺一致
- **MouseWheel binding**：自行處理 Windows 滑鼠滾輪事件（`event.delta / 120`）

## ✅ 驗證結果

| 情境 | 修改前 | 修改後 |
|------|--------|--------|
| 385 檔（SSD） | 30 秒 | **3 秒** |
| 385 檔（網路磁碟） | 71 秒 | **6 秒** |
| 1000+ 檔 | 不可用 | 可正常使用 |

效能提升原因：
- widget 建立成本從 O(n) 變 O(可視範圍) ≈ 常數
- 移除每加一檔的 `_refresh_list_dim`（先前 O(n²)）
- 移除每加一檔的 `_refresh_scrollbar` callback 風暴

## 📊 修改統計

- 新增：`gui/widgets.py` `VirtualFileList` 類別（約 165 行）
- 修改：`gui/main_window.py` 資料層重構（約 -27/+13 行）
- 變更檔案數：2
