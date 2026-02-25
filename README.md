# ai-translator 使用說明書

AI 翻譯工具 — 使用 Claude 將中文翻譯為簡短的英文命名，適用於程式碼變數、函式名稱、檔案名稱、CSS class 等場景。

## 目錄

- [功能特色](#功能特色)
- [系統需求](#系統需求)
- [安裝方式](#安裝方式)
- [快速開始](#快速開始)
- [命令列用法](#命令列用法)
  - [基本翻譯](#基本翻譯)
  - [批次翻譯](#批次翻譯)
  - [指定輸出格式](#指定輸出格式)
  - [提供 Context](#提供-context)
  - [JSON 輸出](#json-輸出)
  - [完整參數列表](#完整參數列表)
- [Python API 用法](#python-api-用法)
  - [基本使用](#基本使用)
  - [批次翻譯 API](#批次翻譯-api)
  - [自訂設定](#自訂設定)
  - [錯誤處理](#錯誤處理)
- [輸出格式說明](#輸出格式說明)
- [Context 系統](#context-系統)
  - [什麼是 Context](#什麼是-context)
  - [提供方式](#提供方式)
  - [自動搜尋機制](#自動搜尋機制)
  - [Context 檔案範例](#context-檔案範例)
- [快取機制](#快取機制)
- [整合到專案](#整合到專案)
  - [作為 Git Submodule](#作為-git-submodule)
  - [在 Shell Script 中使用](#在-shell-script-中使用)
  - [在 Makefile 中使用](#在-makefile-中使用)
- [常見問題](#常見問題)
- [授權](#授權)

---

## 功能特色

- **批次翻譯**：一次傳入多個文字，只呼叫一次 AI，節省時間
- **JSON 快取**：翻譯過的結果自動快取，相同文字不重複呼叫 AI
- **Context 感知**：提供專案背景資訊，讓 AI 正確理解專業術語
- **自動 Context 收集**：自動讀取 `.context.md`、`CLAUDE.md`、`README.md` 等檔案作為參考
- **6 種輸出格式**：kebab-case、snake_case、camelCase、PascalCase、lowercase、UPPERCASE
- **零外部依賴**：僅使用 Python 標準庫，無需安裝額外套件
- **雙介面**：同時支援命令列（CLI）和 Python API

---

## 系統需求

| 項目 | 需求 |
|------|------|
| Python | 3.10 或以上 |
| Claude Code CLI | 已安裝並可在終端執行 `claude` 指令 |
| 外部 pip 套件 | 無（零依賴） |

安裝 Claude Code CLI 請參考：https://github.com/anthropics/claude-code

---

## 安裝方式

### 方法一：使用 uv（推薦）

```bash
# 加入專案作為 Git submodule
git submodule add https://github.com/Cleanstation/ai-translator.git ai-translator

# 進入目錄並執行
cd ai-translator
uv run ai-translator "測試"
```

### 方法二：使用 pip

```bash
# 進入 ai-translator 目錄
cd ai-translator

# 以開發模式安裝
pip install -e .

# 之後可在任何位置執行
ai-translator "測試"
```

### 方法三：直接執行 Python 檔案

```bash
python ai-translator/ai_translator.py "測試"
```

---

## 快速開始

安裝完成後，最簡單的用法：

```bash
# 翻譯一個中文詞
ai-translator "使用者登入"
# 使用者登入 → user-login

# 翻譯多個詞
ai-translator "使用者登入" "密碼重設" "權限管理"
# 使用者登入 → user-login
# 密碼重設 → password-reset
# 權限管理 → permission-management
```

---

## 命令列用法

### 基本翻譯

```bash
ai-translator "測試流程"
# 測試流程 → test-flow
```

預設使用 `kebab-case` 格式輸出。

### 批次翻譯

一次翻譯多個文字，只需用空格隔開（各自加引號）：

```bash
ai-translator "電源板" "顯示板" "成品測試" "韌體更新"
# 電源板 → power-board
# 顯示板 → display-board
# 成品測試 → final-test
# 韌體更新 → firmware-update
```

批次翻譯只會呼叫一次 AI，效率遠高於逐一翻譯。

### 指定輸出格式

使用 `--format`（或 `-f`）指定輸出命名格式：

```bash
# snake_case — 適合 Python 變數
ai-translator -f snake_case "電源板測試"
# 電源板測試 → power_board_test

# camelCase — 適合 JavaScript
ai-translator -f camelCase "電源板測試"
# 電源板測試 → powerBoardTest

# PascalCase — 適合類別名稱
ai-translator -f PascalCase "電源板測試"
# 電源板測試 → PowerBoardTest

# UPPERCASE — 適合常數
ai-translator -f UPPERCASE "電源板測試"
# 電源板測試 → POWER_BOARD_TEST
```

### 提供 Context

Context 是背景資訊，幫助 AI 理解專業術語的正確翻譯：

```bash
# 直接提供 context 字串
ai-translator --context "這是廚餘機產品的 FCT 測試文件" "電源板"
# 電源板 → power-board

# 從檔案載入 context
ai-translator --context-file project.context.md "電源板"

# 透過環境變數設定
export AI_TRANSLATOR_CONTEXT="PCB 電路板測試相關"
ai-translator "電源板"
```

### JSON 輸出

使用 `--json`（或 `-j`）取得結構化的 JSON 輸出，方便後續程式處理：

```bash
ai-translator --json "電源板" "顯示板"
```

輸出：
```json
{
  "電源板": "power-board",
  "顯示板": "display-board"
}
```

### 完整參數列表

```
ai-translator [選項] 文字 [文字 ...]
```

| 參數 | 短寫 | 類型 | 預設值 | 說明 |
|------|------|------|--------|------|
| `文字` | — | 位置參數 | （必填） | 一或多個要翻譯的中文文字 |
| `--context` | `-c` | 字串 | — | 直接提供背景資訊 |
| `--context-file` | `-cf` | 檔案路徑 | — | 從檔案載入背景資訊 |
| `--format` | `-f` | 選擇 | `kebab-case` | 輸出格式（見[輸出格式說明](#輸出格式說明)） |
| `--max-length` | `-l` | 整數 | `30` | 翻譯結果的最大字元數 |
| `--cache-dir` | — | 目錄路徑 | `.ai-translator-cache` | 指定快取儲存目錄 |
| `--json` | `-j` | 旗標 | — | 以 JSON 格式輸出結果 |
| `--no-cache` | — | 旗標 | — | 停用快取（規劃中，尚未實作） |

---

## Python API 用法

### 基本使用

```python
from ai_translator import Translator

translator = Translator()
result = translator.translate("測試流程")
print(result)  # "test-flow"
```

### 批次翻譯 API

`batch_translate()` 回傳一個字典，key 為原始中文，value 為翻譯結果：

```python
from ai_translator import Translator

translator = Translator()
results = translator.batch_translate(["電源板", "顯示板", "成品測試"])

for original, translated in results.items():
    print(f"{original} → {translated}")
# 電源板 → power-board
# 顯示板 → display-board
# 成品測試 → final-test
```

### 自訂設定

`Translator` 建構子支援以下參數：

```python
from pathlib import Path
from ai_translator import Translator

translator = Translator(
    # 提供背景資訊，讓翻譯更準確
    context="這是廚餘機產品的 FCT 測試文件",

    # 或從檔案載入 context
    # context_file=Path("project.context.md"),

    # 輸出格式：kebab-case / snake_case / camelCase / PascalCase / lowercase / UPPERCASE
    output_format="snake_case",

    # 翻譯結果最大字元數
    max_length=40,

    # 自訂快取目錄
    cache_dir=Path(".my-cache"),
)

result = translator.translate("電源板測試")
print(result)  # "power_board_test"
```

| 參數 | 類型 | 預設值 | 說明 |
|------|------|--------|------|
| `context` | `str` | `None` | 背景資訊字串 |
| `context_file` | `Path` | `None` | 背景資訊檔案路徑 |
| `output_format` | `str` | `"kebab-case"` | 輸出命名格式 |
| `max_length` | `int` | `30` | 最大輸出字元數 |
| `cache_dir` | `Path` | `cwd/.ai-translator-cache` | 快取目錄 |

### 錯誤處理

翻譯失敗時，`translate()` 回傳 `"translation-failed"` 字串，不會拋出例外：

```python
translator = Translator()
result = translator.translate("測試")

if result == "translation-failed":
    print("翻譯失敗，請確認 Claude CLI 是否正常運作")
else:
    print(f"翻譯成功：{result}")
```

`batch_translate()` 部分失敗時，成功的項目仍會正常回傳：

```python
results = translator.batch_translate(["電源板", "顯示板"])
# 即使其中一項失敗，另一項仍可能成功
# {'電源板': 'power-board', '顯示板': 'translation-failed'}
```

---

## 輸出格式說明

| 格式 | 範例輸出 | 適用場景 |
|------|----------|----------|
| `kebab-case`（預設） | `power-board-test` | URL slug、CSS class、檔案名稱、HTML 屬性 |
| `snake_case` | `power_board_test` | Python 變數/函式、資料庫欄位、Ruby |
| `camelCase` | `powerBoardTest` | JavaScript/TypeScript 變數、Java 方法 |
| `PascalCase` | `PowerBoardTest` | 類別名稱、React 元件、C# |
| `lowercase` | `powerboardtest` | 緊湊識別符、某些 ID 欄位 |
| `UPPERCASE` | `POWER_BOARD_TEST` | 常數定義、環境變數 |

---

## Context 系統

### 什麼是 Context

Context 是提供給 AI 的背景資訊，讓它理解翻譯的語境。例如：

- 沒有 context：「板」可能翻譯為 `plate`、`board`、`panel`
- 有 context（PCB 電路板產品）：「板」會正確翻譯為 `board`

Context 對於專業術語、縮寫、產業特定用語特別重要。

### 提供方式

Context 有四種提供方式，依優先順序：

**1. 直接提供字串**（CLI 或 Python API）

```bash
ai-translator --context "PCB 電路板測試相關文件" "電源板"
```

```python
translator = Translator(context="PCB 電路板測試相關文件")
```

**2. 從檔案載入**

```bash
ai-translator --context-file .context.md "電源板"
```

```python
translator = Translator(context_file=Path(".context.md"))
```

**3. 環境變數**

```bash
export AI_TRANSLATOR_CONTEXT="PCB 電路板測試相關文件"
ai-translator "電源板"
```

**4. 自動搜尋**（無需任何設定）

工具會自動搜尋工作目錄中的檔案作為 context，見下節說明。

### 自動搜尋機制

當未明確指定 context 時，工具會自動從工作目錄收集以下檔案的內容：

| 搜尋目標 | 說明 | 限制 |
|----------|------|------|
| `.context.md` / `.context.txt` / `CONTEXT.md` / `context.md` | 專用 context 檔案（只取第一個找到的） | 完整內容 |
| `CLAUDE.md` | 專案描述與術語 | 前 2000 字元 |
| `README.md` | 專案說明文件 | 前 1500 字元 |
| `docs/*.md` | 文件目錄中的 Markdown | 最多 5 個檔案，每個前 500 字元 |

所有找到的內容會合併為完整的 context 傳給 AI。

### Context 檔案範例

建議在專案中建立 `.context.md` 檔案：

```markdown
# 專案背景

這是廚餘機產品的技術文件。

## 術語對照

- 電源板 (Power Board)：負責電源管理的 PCB
- 顯示板 (Display Board)：負責 UI 顯示的 PCB
- 控制板 (Control Board)：主控制器 PCB
- FCT：功能電路測試 (Functional Circuit Test)
- 成品測試：整機組裝後的最終驗證測試
- 老化測試 (Burn-in Test)：長時間運作穩定性測試

## 命名慣例

- 測試站名稱用 kebab-case
- 測試項目名稱用 snake_case
```

---

## 快取機制

翻譯結果會自動儲存在 `.ai-translator-cache/translations.json`，相同文字不會重複呼叫 AI。

**快取 key 規則：**

快取以 `{輸出格式}|{context hash}|{原始文字}` 為 key。這代表：

- 相同文字、相同格式、相同 context → 使用快取
- 改變輸出格式 → 重新翻譯
- 改變 context → 重新翻譯

**清除快取：**

```bash
rm -rf .ai-translator-cache/
```

**指定快取目錄：**

```bash
ai-translator --cache-dir /tmp/my-cache "測試"
```

> 提示：`.ai-translator-cache/` 已加入 `.gitignore`，不會被提交到版本控制。

---

## 整合到專案

### 作為 Git Submodule

適合需要在多個專案中共用翻譯工具的情境：

```bash
# 加入 submodule
git submodule add https://github.com/Cleanstation/ai-translator.git ai-translator

# 之後其他人 clone 專案時
git submodule update --init

# 執行翻譯
cd ai-translator && uv run ai-translator "測試"
```

### 在 Shell Script 中使用

```bash
#!/bin/bash
# translate.sh — 批次翻譯測試站名稱

TRANSLATOR="./ai-translator/ai_translator.py"
CONTEXT_FILE=".context.md"

python "$TRANSLATOR" \
    --context-file "$CONTEXT_FILE" \
    --format kebab-case \
    "電源板測試" "顯示板測試" "成品測試" "老化測試"
```

### 在 Makefile 中使用

```makefile
TRANSLATOR = cd ai-translator && uv run ai-translator

translate:
	$(TRANSLATOR) --format snake_case --json "電源板" "顯示板" > translations.json
```

---

## 常見問題

### Q: 出現 `[ERROR] Claude 呼叫失敗` 怎麼辦？

確認 Claude Code CLI 已正確安裝：

```bash
claude --version
```

若未安裝，請參考 https://github.com/anthropics/claude-code 進行安裝。

### Q: 翻譯結果不符合預期？

1. **提供 Context**：加入 `--context` 或建立 `.context.md`，讓 AI 理解專業術語
2. **清除快取**：可能使用了舊的快取結果，執行 `rm -rf .ai-translator-cache/`
3. **調整長度限制**：預設最多 30 字元，用 `--max-length 50` 放寬

### Q: 翻譯結果顯示 `translation-failed`？

可能原因：
- Claude CLI 未安裝或不在 PATH 中
- 網路連線問題（Claude CLI 需要網路）
- AI 回應格式異常（罕見，重試通常可解決）

### Q: 如何避免重複的 API 呼叫？

工具內建 JSON 快取，相同文字只會翻譯一次。若需批次翻譯，盡量用一次指令傳入多個文字：

```bash
# 好：一次呼叫
ai-translator "文字一" "文字二" "文字三"

# 不好：三次呼叫
ai-translator "文字一"
ai-translator "文字二"
ai-translator "文字三"
```

### Q: 不同專案的翻譯會互相干擾嗎？

不會。快取 key 包含 context hash，不同的 context 會產生不同的快取項目。此外，快取儲存在工作目錄的 `.ai-translator-cache/` 中，各專案各自獨立。

---

## 授權

MIT License
