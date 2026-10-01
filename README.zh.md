# Figma to Illustrator Editable Text

[English](README.md) · 繁體中文

`figma-to-illustrator-editable-text` 是一個 Figma 插件匯出診斷與 Illustrator 匯入修復 Skill，目標是保留可編輯文字與原始檔案。

適用於包含 SVG、伴隨 JSX、字體 metadata 與圖片資料夾的匯出流程。這是診斷與修復指南，不是一鍵補丁工具，也不保證所有設計都能無損轉換。

## 它能做什麼

- 先讀插件說明，再決定正常匯入或補丁修復方式。
- 提供唯讀 Python 工具，檢查 SVG 結構、字體資料、圖片連結、文字濾鏡與漸層風險。
- 區分缺少字型、占位字體名稱、文字濾鏡、圖片連結與漸層填色問題。
- 保留原檔，在獨立副本進行修復。
- 近似漸層、移除陰影或替換字型前，先取得使用者同意。
- 檢查可編輯文字、字體、圖片、填色與工作區域。
- 確認 AI 儲存成功並重新開啟後，才回報完成。

## 快速開始

### 安裝到 Codex

```bash
git clone https://github.com/Xuanwinnie/figma-to-illustrator-editable-text.git \
  ~/.codex/skills/figma-to-illustrator-editable-text
```

### 安裝到 Claude Code

```bash
git clone https://github.com/Xuanwinnie/figma-to-illustrator-editable-text.git \
  ~/.claude/skills/figma-to-illustrator-editable-text
```

必要時重新載入 skills 或重新啟動對應 AI 工具，再提供解壓縮資料夾或完整 ZIP。安裝 skill 不會自動取得 Illustrator 操作權限；助理仍需要可用的本機檔案與應用程式操作工具。

```text
使用 figma-to-illustrator-editable-text 處理我提供的 Figma 插件匯出資料。保留可編輯文字與原檔；若需要近似漸層、移除陰影或替換字型，先問我。另存新 AI 並重新開啟驗證；尚未完成的步驟請明確告知。
```

不想安裝時，也可以使用下方直接讀取 GitHub 的提示詞，前提是助理能存取儲存庫與你的檔案。

## 使用流程

### 執行唯讀檢查

需要 Python 3，不需額外套件。在 repository 資料夾執行，替換成你的實際路徑：

```bash
python3 scripts/inspect_export.py '/path/to/export-folder' \
  --svg 'Page_1_RGB.svg' --output '/path/to/new-report.json'
```

多個 SVG 時必須指定 `--svg`。工具不執行 JSX、不修改設計、不下載圖片，也不覆蓋報告。檢查完成不代表字型已安裝、Illustrator 顯示正確或 AI 已存檔。詳細參數與限制見 [檢查工具說明](references/diagnostic-tool.md)。

### 匯入與修復

```text
匯出資料夾或 ZIP ＋ 插件說明
        ↓
檢查 SVG、JSX、字體資料與圖片
        ↓
依插件正常流程匯入 Illustrator
        ↓
辨識問題並在副本測試修復
        ↓
向使用者確認外觀取捨
        ↓
驗證文字、字體、圖片、填色與工作區域
        ↓
另存新 AI 並重新開啟驗證
```

## 可直接複製的使用指令

### 下次直接複製這一行，不必先安裝

提供資料夾路徑或附上完整 ZIP，再貼上這一行。若助理無法讀取 skill，應先告知，不要假裝已載入。

```text
請先完整讀取 https://github.com/Xuanwinnie/figma-to-illustrator-editable-text/blob/main/SKILL.md，並依需要讀取其中連結的案例紀錄，再處理我提供的 Figma 插件匯出資料夾；若尚未提供資料夾路徑或 ZIP，先向我索取，不要猜測。保留可編輯文字與原檔；若需要近似漸層、移除陰影或替換字型，先問我。完成後另存新的 AI 檔，確認存檔成功並重新開啟驗證；若有步驟無法完成，明確告知，不要宣稱已完成。
```

### 只診斷，不修改

```text
使用 figma-to-illustrator-editable-text 診斷這份匯出資料的缺字、字體替換、圖片遺失或顏色異常。先說明證據與修復方案，暫時不要修改檔案。
```

## 核心輸出

流程能完成時，交付另存並重新開啟驗證過的 AI，以及驗證摘要。摘要包含修復項目、可編輯文字範圍、已知外觀差異與尚未完成事項。不能把不存在的 AI 當成已完成檔案提供。

## 補丁問題與優化紀錄

[案例紀錄](references/observed-failures.md) 包含占位字體、文字濾鏡造成缺字、圖片嵌入、漸層文字變黑、匯入 ID 不可靠、空白文字框、重跑腳本衝突與儲存失敗。

紀錄會區分已觀察的修復、近似方案與尚未完成的驗證。本次案例雖然恢復文字與圖片顯示，但沒有確認最終 AI 存檔；原生漸層與陰影也未完整恢復。

## Repository 結構

```text
figma-to-illustrator-editable-text/
├── SKILL.md
├── references/
│   ├── diagnostic-tool.md
│   └── observed-failures.md
├── scripts/
│   └── inspect_export.py
├── tests/
│   └── test_inspect_export.py
├── README.md
└── README.zh.md
```

## 限制

- 可編輯文字與精確外觀可能需要取捨。逐字顏色只是漸層近似，修改文字後可能需要重新計算。
- 移除文字濾鏡可能恢復顯示，但會改變陰影或其他效果。
- 相容性取決於匯出內容、插件版本、字型與 Illustrator 版本；案例中的數量不能當成通用預設值。
- 不附本次專案綁定的補丁腳本、設計、圖片或字型檔。
- 目前自動化只完成唯讀檢查；通用修復腳本與 AI 重新開啟驗證尚未實作。

## 測試

```bash
python3 -B -m unittest discover -s tests -v
```

測試使用匿名合成資料，不附私人設計素材或客戶匯出包。

## License

本 repository 尚未指定授權條款；公開可讀不等於自動授予再散布權限。第三方插件、字型與設計素材的使用權限需另外確認。
