# ai-translator

AI 翻譯工具，可將中文翻譯為簡短英文名稱。適合程式碼命名、檔案命名、測試項目命名等場景。

目前支援：
- Claude CLI provider
- HTTP provider
  - OpenAI-compatible API
  - Anthropic-compatible API
- 批次翻譯
- JSON 快取
- Context 支援
- 多種輸出格式

## 功能特色

- **批次翻譯**：一次翻譯多個文字，減少 API 呼叫
- **JSON 快取**：避免重複翻譯相同內容
- **Context 支援**：提供背景資訊讓翻譯更準確
- **多 provider**：可切換 Claude CLI 或 HTTP API
- **多種輸出格式**：kebab-case、snake_case、camelCase 等

## 安裝

### 系統需求

- Python 3.10+
- 若使用預設 provider：已安裝並設定 [Claude Code CLI](https://github.com/anthropics/claude-code)
- 若使用 HTTP provider：可存取對應的 API 服務

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
# 單一翻譯（預設: Claude CLI）
ai-translator "測試流程"

# 明確指定 Claude CLI
ai-translator --provider claude-cli "測試流程"

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

### HTTP provider：OpenAI-compatible

```bash
ai-translator \
  --provider http \
  --protocol openai \
  --base-url http://localhost:13305/v1 \
  --model user.gemma-4-26B-A4B-it-GGUF \
  "測試流程"
```

### HTTP provider：Anthropic-compatible

```bash
ai-translator \
  --provider http \
  --protocol anthropic \
  --base-url http://localhost:13305 \
  --model user.gemma-4-26B-A4B-it-GGUF \
  "測試流程"
```

### 本機 Lemonade 範例

Lemonade 若走 OpenAI-compatible 路徑，通常使用 `/v1` 作為 base URL：

```bash
ai-translator \
  --provider http \
  --protocol openai \
  --base-url http://localhost:13305/v1 \
  --model user.gemma-4-26B-A4B-it-GGUF \
  --api-key "$LEMONADE_API_KEY" \
  "電源板測試"
```

若走 Anthropic-compatible 路徑，`base-url` 應填 root URL，而不是 `/v1`：

```bash
ai-translator \
  --provider http \
  --protocol anthropic \
  --base-url http://localhost:13305 \
  --model user.gemma-4-26B-A4B-it-GGUF \
  --api-key "$LEMONADE_API_KEY" \
  "電源板測試"
```

## Python API

```python
from ai_translator import HTTPProvider, Translator

# 預設 Claude CLI
translator = Translator()
print(translator.translate("測試流程"))

# HTTP provider（OpenAI-compatible）
provider = HTTPProvider(
    protocol="openai",
    base_url="http://localhost:13305/v1",
    model="user.gemma-4-26B-A4B-it-GGUF",
    api_key="YOUR_API_KEY",
)
translator = Translator(provider=provider)
print(translator.translate("電源板測試"))
```

## Documentation

Public-safe supporting documents live under `docs/`:

- `docs/README.md` — documentation index
- `docs/architecture/` — architecture notes
- `docs/integration/` — generic downstream integration guidance
- `docs/templates/` — public-safe templates and examples

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
| `--provider <name>` | provider：`claude-cli` 或 `http` |
| `--protocol <name>` | HTTP protocol：`openai` 或 `anthropic` |
| `--model <name>` | HTTP provider 模型名稱 |
| `--base-url <url>` | HTTP provider base URL |
| `--api-key <key>` | HTTP provider API key |
| `--timeout <sec>` | provider timeout |

## 環境變數

可用以下環境變數提供預設值：

- `AI_TRANSLATOR_CONTEXT`
- `AI_TRANSLATOR_PROVIDER`
- `AI_TRANSLATOR_PROTOCOL`
- `AI_TRANSLATOR_MODEL`
- `AI_TRANSLATOR_BASE_URL`
- `AI_TRANSLATOR_API_KEY`
- `AI_TRANSLATOR_TIMEOUT`

## 輸出格式

| 格式 | 範例 |
|------|------|
| `kebab-case` | power-board-test |
| `snake_case` | power_board_test |
| `camelCase` | powerBoardTest |
| `PascalCase` | PowerBoardTest |
| `lowercase` | powerboardtest |
| `UPPERCASE` | POWER_BOARD_TEST |

## Context 自動載入

腳本會自動搜尋以下內容作為 context（按優先順序）：

1. `--context` 參數直接提供
2. `--context-file` 指定的檔案
3. 環境變數 `AI_TRANSLATOR_CONTEXT`
4. 工作目錄下的 `.context.md`、`.context.txt`、`CONTEXT.md`、`context.md`
5. 工作目錄下的 `AGENTS.md`、`README.md`、`docs/*.md` 片段

## 快取

翻譯結果會儲存在 `.ai-translator-cache/translations.json`。

快取 key 會區分：
- provider
- model
- endpoint fingerprint
- output format
- prompt version
- max length
- context digest
- source text

清除快取：

```bash
rm -rf .ai-translator-cache/
```

## 測試

```bash
uv run --dev pytest tests/ -q
```

## 授權

MIT License
