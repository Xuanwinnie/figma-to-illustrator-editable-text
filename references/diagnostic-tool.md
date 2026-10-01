# 唯讀匯出檢查工具

`scripts/inspect_export.py` 是第一階段的自動化檢查，不是修復腳本。使用 Python 3 標準函式庫，無需另外安裝套件；不連網、不執行 JSX、不修改 SVG、AI、圖片或字型。

## 使用方式

從 skill 資料夾執行，將範例路徑換成使用者實際提供的路徑：

```bash
python3 scripts/inspect_export.py '/path/to/export-folder' \
  --svg 'Page_1_RGB.svg' \
  --output '/path/to/new-report.json'
```

- 資料夾只有一個 SVG 時可以省略 `--svg`；多個 SVG 時必須指定，避免檢查到舊版或修正版。
- 也可把單一 SVG 當作第一個參數。
- 預設尋找同資料夾的 `01-create-artboards-and-merge-text.jsx`，只解析其中 `BAKED_FIGMA_META` 的 JSON。不同檔名使用 `--jsx '/path/to/companion.jsx'`。
- 有 `fonts.txt` 時一併讀取需求清單；不判定字型已安裝。
- 不指定 `--output` 時只輸出到終端。指定時僅建立新報告，不自動建立父資料夾，且拒絕覆蓋任何既有檔案。
- SVG 需為 UTF-8，大小不超過 256 MiB；metadata／manifest 不超過 8 MiB。拒絕 DTD 和自訂實體，超出支援格式時明確停止。

## 報告內容

| 欄位 | 用途與邊界 |
|---|---|
| `summary` | SVG 文字、空白文字、圖片、frame 標記、漸層及 metadata 的數量；不是 Illustrator 內的驗證結果 |
| `svg_fonts` | SVG 及行內 style 宣告／繼承的字體名稱 |
| `metadata_fonts` | metadata 中的字體系列與樣式需求，不等於可用的 PostScript 名稱 |
| `font_manifest` | fonts.txt 的需求清單 |
| `findings` | 錯誤、相容性風險與需要人工確認的項目，包含代碼、級別及數量 |
| `not_verified` | 字型安裝、圖片外觀、可編輯性、AI 存檔與重新開檔等尚未驗證的事項 |

重複 ID、缺少內部引用目標、圖片連結不存在或嵌入資料格式錯誤會列為 `error`。文字濾鏡、文字漸層與可能的 Arial 占位名稱只列為 `warning`，不能自動推論它們已經造成缺字或變色。

Exit code：`0` 代表檢查完成且未找到結構錯誤（仍可能有 warning）；`2` 代表報告中有 error；`1` 代表無法完成檢查或寫出報告。**任何 exit code 都不代表 Illustrator 修復完成。**

## 安全與限制

- 不讀取匯出資料夾外的圖片，包含向外的相對路徑與符號連結；外部網址不會被下載。
- 報告不包含文字文案、圖片 base64 或來源絕對路徑，但檔名與字體名稱仍可能透露專案資訊；報告留在本地，公開上傳前仍應檢查與匿名化。
- 圖片存在與 base64 合法，不代表圖片像素有效或 Illustrator 顯示正確。
- CSS 選擇器、外部樣式與完整渲染規則不在支援範圍；發現 `<style>` 會標示統計可能不完整。
- frame 計數依 `FRAME__` 群組標記，不會猜測真正的工作區域數量或尺寸。
- metadata 對應只使用明確 ID，空白文字不計入未對應警告；不以文案／位置猜測，也不自動選字型或修改外觀。

## 測試

```bash
python3 -B -m unittest discover -s tests -v
```

測試資料都是匿名合成資料。包含字體對應、filter／漸層風險、圖片狀態、空白文字、ID 重複、DTD／非 UTF-8 拒絕、JSX 不執行、報告隱私、重複分析一致及拒絕覆蓋。實際匯出包的報告不應加入 repo。
