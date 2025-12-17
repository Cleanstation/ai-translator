# ai-translator Claude Code 指引

## 專案概述

ai-translator 是一個使用 Claude 進行中文到英文翻譯的工具。專為程式碼命名、檔案命名等場景設計，支援多種輸出格式。

## 核心功能

1. **批次翻譯**：一次翻譯多個文字，減少 API 呼叫
2. **JSON 快取**：避免重複翻譯，儲存在 `.ai-translator-cache/translations.json`
3. **Context 支援**：提供背景資訊讓 AI 理解專業術語
4. **多種輸出格式**：kebab-case、snake_case、camelCase 等

## 檔案結構

```
ai-translator/
├── ai_translator.py    # 主程式（含 Translator 類別和 CLI）
├── pyproject.toml      # Python 專案設定
├── README.md           # 使用說明
└── CLAUDE.md           # 本文件
```

## 核心類別

### Translator

主要翻譯類別，提供：
- `translate(text)` - 翻譯單一文字
- `batch_translate(texts)` - 批次翻譯多個文字

### TranslationCache

快取管理類別：
- 快取 key 格式：`{output_format}|{context_hash}|{text}`
- 不同 context 的翻譯會分開快取

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
```

## 依賴

- Python 3.10+
- Claude Code CLI（用於呼叫 AI）

## 修改注意事項

1. `_build_prompt()` 方法定義了給 AI 的 prompt 格式
2. `_format_output()` 方法處理各種輸出格式的轉換
3. 快取使用 context hash 作為 key 的一部分，確保不同 context 的翻譯分開儲存
