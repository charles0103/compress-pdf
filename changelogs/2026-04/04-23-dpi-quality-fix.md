# 2026-04-23 修正 DPI 與圖片品質參數實際不生效的 bug

## 🎯 功能概述

- **影響範圍**：`core/image_optimizer.py`、`core/compressor.py`、`gui/main_window.py`
- **問題本質**：UI 上的「圖片解析度 DPI」與「圖片品質」兩個滑桿在多數情境下並未真正影響輸出壓縮率
- **複雜度**：中等（核心壓縮演算法重寫 + UI 文案調整）

## 🐛 問題分析

參考 pikepdf 官方文件（透過 context7 查詢）與 serena 靜態分析後，識別出兩個關鍵 bug：

### Bug 1：DPI 計算前提錯誤

原程式碼硬寫 Letter 尺寸（`_PAGE_W_IN = 8.5`、`_PAGE_H_IN = 11.0`），並假設「每張圖片都等於整頁」：

```python
max_w = int(_PAGE_W_IN * dpi)
scale = min(max_w / width if width > max_w else 1.0, ...)
```

pikepdf 官方文件明確指出：

> The pixel dimensions of the image have no effect. The image is drawn in the rectangle defined by the content stream's CTM, regardless of its pixel dimensions.

即：圖片的「顯示尺寸」由 content stream 的 CTM（Current Transformation Matrix）決定，與像素尺寸無關。實際 effective DPI 的正確公式為：

```
effective_dpi = image_pixel_width / image_display_width_in_inches
```

舊邏輯導致：
- **A4 檔案被當 Letter 估算**，多留像素沒壓到
- **頁內小縮圖無法降採樣**：一張 2000×2000 像素但只顯示 1×1 吋的縮圖，實際 2000 DPI，卻被認為「超過 150 DPI 的總頁像素 1275」而只縮到 1275×1275（仍遠超目標）

### Bug 2：品質滑桿常態失效

舊程式碼在降採樣條件不滿足時直接 return：

```python
if scale >= 1.0 and not grayscale:
    return  # 跳過整個 JPEG 重編流程
```

這代表「高壓縮」模式將品質拉到 50，若圖片尺寸沒超過頁面估算值，**品質參數完全沒套用**。只有超大解析度圖才會觸發重編碼。

## ⚡ 實作方案

### 1. 以 CTM 計算精確 effective DPI

新增 `_collect_display_sizes(pdf)`：

- 使用 `pikepdf.models.ctm.get_objects_with_ctm(page)` 取得每個圖片 XObject 的 CTM 矩陣
- 以 `math.hypot(matrix.a, matrix.b)` 計算顯示寬（考慮旋轉）
- 同一張圖多處引用時取最大顯示尺寸，避免過度降採樣
- Fallback 鏈：CTM API → mediabox → Letter 預設

`_try_compress` 改以實際顯示尺寸計算：

```python
effective_dpi = min(
    width  * 72.0 / display_w_pt,
    height * 72.0 / display_h_pt,
)
scale = (target_dpi / effective_dpi) if effective_dpi > target_dpi else 1.0
```

### 2. 拆開降採樣與重編碼流程

`optimize_images()` 新增 `force_recompress: bool` 參數：

```python
need_resize = scale < 1.0
need_recompress = force_recompress or grayscale
if not (need_resize or need_recompress):
    return
```

`compressor.py` 對應調整：
- **模式 2（圖片優化）**：`force_recompress=False`，維持僅動超大圖的語意
- **模式 3（高壓縮）**：`force_recompress=True`，所有圖片一律以指定品質重編 JPEG

### 3. 最小尺寸門檻

新增 `_MIN_RECOMPRESS_PX = 64`，小於此尺寸的 icon 略過重編碼（避免 JPEG 化後反而變大）。

### 4. UI 合理化

- **壓縮等級 slider 改為一律 disabled**：pikepdf 9+ 已移除 `flate_level` 參數，該 slider 實際無效。標籤改為「壓縮等級（自動）」。
- **解析度標籤**：改為「圖片解析度（降採樣上限）」，明確表達「只降不升」語意
- **品質標籤**：改為「圖片品質（越低檔案越小）」，避免使用者誤以為數字越大壓縮率越高

### 5. 分析函式同步修正

`analyze_pdf_images()` / `_extract_image_info()` 也採用 CTM 計算，UI 上的圖片解析度分析才會顯示真實值。

## ✅ 驗證結果

- `python -m py_compile` 所有檔案通過
- 所有核心模組 import 成功
- `optimize_images` 新簽名：`(input_path, output_path, dpi=150, quality=75, grayscale=False, force_recompress=False)`
- 當前環境 `_HAS_CTM_API = True`（pikepdf 9+ 精確路徑會生效）
- 實機測試通過（使用者確認）

### 預期使用者體感

| 設定 | 改動前 | 改動後 |
|------|--------|--------|
| 模式 2 / DPI 300 vs 72 | 檔案大小幾乎不變 | 明顯遞減 |
| 模式 3 / 品質 95 vs 50 | 小圖居多時無效 | 所有圖片都受影響 |
| A4 掃描檔 | Letter 估算偏少 | 精確按 A4 尺寸壓縮 |

## 📊 修改統計

- **修改**：3 個檔案
  - `core/image_optimizer.py`：+200 / -81（核心重寫）
  - `core/compressor.py`：+8 / -2（接線 force_recompress）
  - `gui/main_window.py`：+15 / -13（UI 文案與 level slider 狀態）
- **新增**：
  - `CLAUDE.md`：專案架構文件（提供未來 Claude Code 使用）
  - `changelogs/2026-04/04-23-dpi-quality-fix.md`（本文）
- **配置**：`.gitignore` 新增 `.claude/`、`.serena/` 排除

## 🔗 相關資源

- pikepdf CTM 文件：`pikepdf.models.ctm.get_objects_with_ctm`
- PDF 規範：圖片 XObject 為 1×1 單位方塊，由 CTM 決定實際繪製尺寸
