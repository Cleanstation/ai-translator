# ai-translator Claude Code 指引

## 專案概述

ai-translator 是一個將中文翻譯為簡短英文名稱的工具，專為程式碼命名、檔案命名、測試項目命名等場景設計。

目前支援：
- `claude-cli` provider
- `http` provider
  - OpenAI-compatible API
  - Anthropic-compatible API

## 核心功能

1. **批次翻譯**：一次翻譯多個文字，減少 API 呼叫
2. **JSON 快取**：避免重複翻譯，儲存在 `.ai-translator-cache/translations.json`
3. **Context 支援**：提供背景資訊讓 AI 理解專業術語
4. **多種輸出格式**：kebab-case、snake_case、camelCase 等
5. **多 provider**：Claude CLI 與 HTTP API 可切換

## 檔案結構

```text
ai-translator/
├── ai_translator.py    # 主程式（含 Translator、provider、parser、CLI）
├── tests/              # pytest 測試
├── docs/               # 架構分析與 implementation plans
├── pyproject.toml      # Python 專案設定
├── README.md           # 使用說明
└── CLAUDE.md           # 本文件
```

## 核心類別 / 函式

### Translator

主要翻譯類別，提供：
- `translate(text)` - 翻譯單一文字
- `batch_translate(texts)` - 批次翻譯多個文字

### Provider

- `LLMProvider` - provider 介面
- `ClaudeCLIProvider` - 透過 `claude --print` 呼叫模型
- `HTTPProvider` - 透過 HTTP 呼叫 OpenAI-compatible / Anthropic-compatible API

### 其他重要元件

- `TranslationCache` - 快取管理
- `parse_translation_response()` - 從模型輸出萃取 JSON 翻譯結果
- `build_arg_parser()` - CLI 參數定義
- `create_provider_from_args()` - 依 CLI / env 建立 provider

## 使用方式

### 作為 Git Submodule

```bash
git submodule add https://github.com/Cleanstation/ai-translator.git ai-translator
cd ai-translator && uv run ai-translator "測試"
```

### 作為 Python 模組

```python
from ai_translator import HTTPProvider, Translator

provider = HTTPProvider(
    protocol="openai",
    base_url="http://localhost:13305/v1",
    model="user.gemma-4-26B-A4B-it-GGUF",
)
translator = Translator(context="專案背景資訊", provider=provider)
result = translator.translate("電源板測試")
```

## 依賴

- Python 3.10+
- 若使用預設 provider：Claude Code CLI
- 若使用 HTTP provider：可連線的 API 服務
- 測試：`pytest`

## 修改注意事項

1. `_build_prompt()` 定義翻譯 prompt 格式
2. `_format_output()` 處理各種輸出格式
3. cache key 已包含 provider / model / endpoint fingerprint / prompt_version 等資訊，避免多來源污染
4. OpenAI-compatible provider 預期 `base_url` 已含 `/v1`
5. Anthropic-compatible provider 預期 `base_url` 為 root URL，程式會補 `/v1/messages`
6. 若要新增更多 provider，優先保持 `Translator` 與 transport 解耦
