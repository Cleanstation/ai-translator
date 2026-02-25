# ai-translator Claude Code 指引

## 專案概述

ai-translator 是一個零外部依賴的中文到英文翻譯工具，透過 Claude CLI (`claude --print`) 執行翻譯。專為程式碼命名（變數、函式、檔案）場景設計，支援 6 種輸出格式、JSON 快取與自動 context 收集。

## 檔案結構

```
ai-translator/
├── ai_translator.py    # 唯一的程式碼檔案（含所有類別和 CLI 入口）
├── pyproject.toml      # 專案設定（零外部依賴，hatchling 構建）
├── README.md           # 使用者說明文件
├── CLAUDE.md           # 本文件
└── .gitignore          # 忽略 __pycache__、.ai-translator-cache/ 等
```

這是一個單檔案專案，所有邏輯都在 `ai_translator.py` 中。

## 系統需求

- Python 3.10+（僅使用 stdlib：os, re, sys, json, subprocess, argparse, pathlib, typing, dataclasses）
- Claude Code CLI 已安裝且可用（使用 `claude --print` 指令）
- 零外部 pip 依賴

## 核心架構

### TranslationConfig（dataclass，第 62 行）

翻譯設定容器：
- `output_format`: 輸出格式，預設 `"kebab-case"`
- `max_length`: 最大輸出長度，預設 `30` 字元
- `cache_dir`: 快取目錄路徑
- `context` / `context_file`: Context 來源

### TranslationCache（第 71-118 行）

JSON 快取管理：
- 快取檔案：`.ai-translator-cache/translations.json`
- Key 格式：`{output_format}|{context_hash}|{text}`（如 `kebab-case|5234|電源板測試`）
- Context hash：`hash(context or "") % 10000`，確保不同 context 的翻譯分開快取
- `set_batch()` 批次寫入只觸發一次檔案 I/O

### Translator（第 120-381 行）

主要翻譯類別：

| 方法 | 說明 |
|------|------|
| `__init__()` | 初始化格式、載入 context、建立快取 |
| `_load_context()` | 自動搜尋並收集 context（見下方） |
| `_format_output()` | 清理文字並套用輸出格式 |
| `_build_prompt()` | 組裝翻譯 prompt，要求 JSON 回應 |
| `translate(text)` | 翻譯單一文字（包裝 `batch_translate`） |
| `batch_translate(texts)` | 核心方法：快取查詢 → AI 呼叫 → 結果解析 → 快取儲存 |

### main()（第 383-488 行）

CLI 入口，使用 argparse。透過 `pyproject.toml` 的 `[project.scripts]` 註冊為 `ai-translator` 指令。

## Context 自動搜尋機制

`_load_context()` 依照以下優先順序收集 context，用 `"\n\n---\n\n"` 串接：

1. **直接提供的 `context` 字串**
2. **指定的 `context_file`**
3. **環境變數** `AI_TRANSLATOR_CONTEXT`
4. **自動搜尋專案檔案**（從 `cwd` 開始）：
   - 專用 context 檔案（只取一個）：`.context.md`、`.context.txt`、`CONTEXT.md`、`context.md`
   - `CLAUDE.md`：前 2000 字元
   - `README.md`：前 1500 字元
   - `docs/*.md`：最多 5 個檔案，每個前 500 字元

## 輸出格式

| 格式 | 範例 | 典型用途 |
|------|------|----------|
| `kebab-case`（預設） | `power-board-test` | URL slug、CSS class、檔案名 |
| `snake_case` | `power_board_test` | Python 變數、資料庫欄位 |
| `camelCase` | `powerBoardTest` | JavaScript / TypeScript |
| `PascalCase` | `PowerBoardTest` | 類別名稱 |
| `lowercase` | `powerboardtest` | 緊湊識別符 |
| `UPPERCASE` | `POWER_BOARD_TEST` | 常數、環境變數 |

`_format_output()` 先將文字小寫化、去除引號、統一空白，再套用格式轉換。

## CLI 參數

```
ai-translator [OPTIONS] TEXT [TEXT ...]
```

| 參數 | 短寫 | 預設值 | 說明 |
|------|------|--------|------|
| `texts` | — | （必填） | 一或多個中文文字 |
| `--context` | `-c` | None | 直接提供 context 字串 |
| `--context-file` | `-cf` | None | 從檔案載入 context |
| `--format` | `-f` | `kebab-case` | 輸出格式（6 種選擇） |
| `--max-length` | `-l` | `30` | 最大輸出長度 |
| `--cache-dir` | — | `.ai-translator-cache` | 自訂快取目錄 |
| `--json` | `-j` | False | 輸出 JSON 格式 |
| `--no-cache` | — | False | 不使用快取（已定義但尚未實作） |

## 錯誤處理模式

所有翻譯失敗統一回傳 `"translation-failed"` 字串：
- Claude CLI 回傳非零（`result.returncode != 0`）
- AI 回應無法解析為 JSON（用 `re.search(r'\{[^{}]*\}', output)` 提取）
- 呼叫超時（120 秒上限）
- 其他例外（catch-all `Exception`）

錯誤訊息寫入 `stderr`，格式為 `[ERROR] ...`。部分翻譯失敗不影響已成功的結果。

## 使用方式

### 作為 Git Submodule

```bash
git submodule add https://github.com/Cleanstation/ai-translator.git ai-translator
cd ai-translator && uv run ai-translator "測試"
```

### 作為 Python 模組

```python
from ai_translator import Translator

translator = Translator(
    context="專案背景資訊",
    output_format="kebab-case"
)
result = translator.translate("電源板測試")
results = translator.batch_translate(["電源板", "顯示板", "成品測試"])
```

## 修改注意事項

1. **單檔案架構**：所有邏輯在 `ai_translator.py`，勿拆分檔案除非有明確需求
2. **零依賴原則**：僅使用 Python 標準庫，不引入外部套件
3. **`_build_prompt()`**：定義 AI prompt 格式，修改會直接影響翻譯品質
4. **`_format_output()`**：處理各種命名格式轉換，新增格式需同步更新 `OutputFormat` type alias、此方法、`_build_prompt()` 中的 `format_instructions` 字典、以及 CLI 的 `--format` choices
5. **快取 key 包含 context hash**：修改 `_make_key()` 的 hash 邏輯會使現有快取失效
6. **`--no-cache` 選項**：已定義在 CLI 參數中但 `Translator` 未實作此功能
7. **AI 呼叫方式**：透過 `subprocess.run(['claude', '--print', prompt])` 執行，timeout 120 秒
8. **`max_length` 彈性**：允許翻譯超過 `max_length` 最多 10 個字元，超過才截斷
