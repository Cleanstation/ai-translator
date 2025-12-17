# ai-translator

AI 翻譯工具，使用 Claude 將中文翻譯為英文。支援批次翻譯、JSON 快取和多種輸出格式。

## 功能特色

- **批次翻譯**：一次翻譯多個文字，減少 API 呼叫
- **JSON 快取**：避免重複翻譯相同內容
- **Context 支援**：提供背景資訊讓翻譯更準確
- **多種輸出格式**：kebab-case、snake_case、camelCase 等

## 安裝

### 系統需求

- Python 3.10+
- [Claude Code CLI](https://github.com/anthropics/claude-code) 已安裝並設定

### 使用 uv（推薦）

```bash
# 作為 Git submodule 加入專案（放在專案根目錄）
git submodule add https://github.com/Cleanstation/ai-translator.git ai-translator

# 執行
cd ai-translator
uv run ai-translator "測試"
```

### 使用 pip

```bash
pip install -e .
ai-translator "測試"
```

## 用法

### 命令列

```bash
# 單一翻譯
ai-translator "測試流程"

# 批次翻譯
ai-translator "電源板" "顯示板" "成品測試"

# 指定輸出格式
ai-translator --format snake_case "測試流程"

# 帶 context（提供背景資訊）
ai-translator --context "這是 FCT 測試文件" "電源板測試"

# 從檔案載入 context
ai-translator --context-file project.context.md "電源板測試"

# 輸出 JSON 格式
ai-translator --json "測試項目"
```

### Python API

```python
from ai_translator import Translator

# 基本使用
translator = Translator()
result = translator.translate("測試流程")
print(result)  # test-flow

# 帶 context 的翻譯
translator = Translator(context="這是廚餘機產品的 FCT 測試文件")
results = translator.batch_translate(["電源板", "顯示板", "成品測試"])
print(results)
# {'電源板': 'power-board', '顯示板': 'display-board', '成品測試': 'final-test'}

# 指定輸出格式
translator = Translator(output_format="snake_case")
result = translator.translate("電源板測試")
print(result)  # power_board_test
```

## 命令列選項

| 選項 | 說明 |
|------|------|
| `-c, --context <text>` | 提供給 AI 的背景資訊 |
| `-cf, --context-file <file>` | 從檔案載入 context |
| `-f, --format <format>` | 輸出格式（預設: kebab-case） |
| `-l, --max-length <n>` | 最大輸出長度（預設: 30） |
| `--cache-dir <dir>` | 快取目錄 |
| `-j, --json` | 輸出 JSON 格式 |
| `--no-cache` | 不使用快取 |

### 輸出格式

| 格式 | 範例 |
|------|------|
| `kebab-case` | power-board-test |
| `snake_case` | power_board_test |
| `camelCase` | powerBoardTest |
| `PascalCase` | PowerBoardTest |
| `lowercase` | powerboardtest |
| `UPPERCASE` | POWER_BOARD_TEST |

## Context 自動載入

腳本會自動搜尋以下檔案作為 context（按優先順序）：

1. `--context` 參數直接提供
2. `--context-file` 指定的檔案
3. 環境變數 `AI_TRANSLATOR_CONTEXT`
4. 工作目錄下的 `.context.md`、`.context.txt`、`CONTEXT.md`、`context.md`

### Context 範例

`.context.md`:
```markdown
# 專案背景

這是廚餘機產品的技術文件。

## 術語對照
- 電源板 (Power Board)：負責電源管理的 PCB
- 顯示板 (Display Board)：負責 UI 顯示的 PCB
- FCT：功能電路測試 (Functional Circuit Test)
- 成品測試：整機組裝後的驗證測試
```

## 快取

翻譯結果會儲存在 `.ai-translator-cache/translations.json`。

清除快取：
```bash
rm -rf .ai-translator-cache/
```

## 授權

MIT License
