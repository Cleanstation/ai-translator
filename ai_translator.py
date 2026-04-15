#!/usr/bin/env python3
"""
ai_translator.py - 通用 AI 翻譯模組

提供中文到英文的翻譯功能，支援：
- 批次翻譯（減少 API 呼叫）
- JSON 快取（避免重複翻譯）
- 自訂 context（提供背景資訊給 AI）
- 多種輸出格式（kebab-case、snake_case、camelCase 等）
- 可插拔 provider（Claude CLI / HTTP）

Context 提供方式：
1. 直接傳入字串
2. 從檔案讀取（.context.md 或 .context.txt）
3. 從環境變數讀取
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request as urllib_request
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

OutputFormat = Literal["kebab-case", "snake_case", "camelCase", "PascalCase", "lowercase", "UPPERCASE"]

OPENAI_PROTOCOL = "openai"
ANTHROPIC_PROTOCOL = "anthropic"
OPENAI_CHAT_COMPLETIONS_PATH = "/chat/completions"
ANTHROPIC_MESSAGES_PATH = "/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


@dataclass
class TranslationConfig:
    """翻譯設定"""

    output_format: OutputFormat = "kebab-case"
    max_length: int = 30
    cache_dir: Optional[Path] = None
    context: Optional[str] = None
    context_file: Optional[Path] = None
    use_cache: bool = True
    prompt_version: str = "v1"
    provider: str = "claude-cli"
    protocol: str = OPENAI_PROTOCOL
    model: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    timeout: int = 120


class LLMProvider:
    """LLM provider 介面"""

    provider_name = "unknown"
    model_name = "default"
    endpoint_fingerprint = "local"

    def generate(self, prompt: str) -> str:
        raise NotImplementedError


class ClaudeCLIProvider(LLMProvider):
    """以 Claude CLI 為 backend 的 provider"""

    provider_name = "claude-cli"
    model_name = "claude-default"
    endpoint_fingerprint = "claude-cli"

    def __init__(self, timeout: int = 120):
        self.timeout = timeout

    def generate(self, prompt: str) -> str:
        try:
            result = subprocess.run(
                ["claude", "--print", prompt],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("Claude 呼叫超時") from exc
        except Exception as exc:
            raise RuntimeError(f"Claude 呼叫失敗: {exc}") from exc

        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            raise RuntimeError(f"Claude 呼叫失敗: {stderr}")

        return result.stdout.strip()


class HTTPProvider(LLMProvider):
    """以 HTTP API 為 backend 的 provider。"""

    provider_name = "http"

    def __init__(
        self,
        protocol: str,
        base_url: str,
        model: str,
        api_key: Optional[str] = None,
        timeout: int = 120,
    ):
        normalized_protocol = protocol.strip().lower()
        if normalized_protocol not in {OPENAI_PROTOCOL, ANTHROPIC_PROTOCOL}:
            raise ValueError(f"不支援的 protocol: {protocol}")
        if not base_url:
            raise ValueError("HTTP provider 需要 --base-url 或 AI_TRANSLATOR_BASE_URL")
        if not model:
            raise ValueError("HTTP provider 需要 --model 或 AI_TRANSLATOR_MODEL")

        self.protocol = normalized_protocol
        self.base_url = base_url.rstrip("/")
        self.model_name = model
        self.api_key = api_key
        self.timeout = timeout
        self.endpoint_fingerprint = f"{self.protocol}|{self.base_url}"

    def _build_url(self) -> str:
        if self.protocol == OPENAI_PROTOCOL:
            return f"{self.base_url}{OPENAI_CHAT_COMPLETIONS_PATH}"
        if self.base_url.endswith("/v1"):
            return f"{self.base_url}/messages"
        return f"{self.base_url}{ANTHROPIC_MESSAGES_PATH}"

    def _build_headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            if self.protocol == ANTHROPIC_PROTOCOL:
                headers["x-api-key"] = self.api_key
        if self.protocol == ANTHROPIC_PROTOCOL:
            headers["anthropic-version"] = ANTHROPIC_VERSION
        return headers

    def _build_payload(self, prompt: str) -> dict:
        if self.protocol == OPENAI_PROTOCOL:
            return {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
            }
        return {
            "model": self.model_name,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
        }

    @staticmethod
    def _extract_text_blocks(content) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str):
                        parts.append(text)
            return "".join(parts).strip()
        return ""

    def _parse_response_text(self, data: dict) -> str:
        if self.protocol == OPENAI_PROTOCOL:
            choices = data.get("choices") or []
            if not choices:
                raise RuntimeError("OpenAI provider 回應缺少 choices")
            message = choices[0].get("message") or {}
            text = self._extract_text_blocks(message.get("content"))
            if not text:
                raise RuntimeError("OpenAI provider 回應缺少 message.content")
            return text

        content = data.get("content") or []
        text = self._extract_text_blocks(content)
        if not text:
            raise RuntimeError("Anthropic provider 回應缺少 content.text")
        return text

    def generate(self, prompt: str) -> str:
        payload = json.dumps(self._build_payload(prompt), ensure_ascii=False).encode("utf-8")
        request = urllib_request.Request(
            self._build_url(),
            data=payload,
            headers=self._build_headers(),
            method="POST",
        )

        try:
            with urllib_request.urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP provider 請求失敗: {exc.code} {error_body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"HTTP provider 無法連線: {exc.reason}") from exc
        except Exception as exc:
            raise RuntimeError(f"HTTP provider 請求失敗: {exc}") from exc

        try:
            data = json.loads(body)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"HTTP provider 回應不是合法 JSON: {body[:200]}") from exc

        if not isinstance(data, dict):
            raise RuntimeError("HTTP provider 回應格式錯誤: 預期 JSON 物件")

        return self._parse_response_text(data)


def _load_json_object(text: str) -> dict[str, str]:
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("LLM output is not a JSON object")
    return parsed


def _extract_first_json_object(text: str) -> Optional[str]:
    start = text.find("{")
    while start != -1:
        depth = 0
        in_string = False
        escape = False

        for index in range(start, len(text)):
            char = text[index]

            if escape:
                escape = False
                continue

            if char == "\\":
                escape = True
                continue

            if char == '"':
                in_string = not in_string
                continue

            if in_string:
                continue

            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start:index + 1]

        start = text.find("{", start + 1)

    return None


def parse_translation_response(output: str) -> dict[str, str]:
    """解析 LLM 回應中的翻譯 JSON。"""

    cleaned = output.strip()
    if not cleaned:
        raise ValueError("空的 LLM 回應")

    try:
        return _load_json_object(cleaned)
    except (json.JSONDecodeError, ValueError):
        pass

    fenced_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL | re.IGNORECASE)
    if fenced_match:
        try:
            return _load_json_object(fenced_match.group(1))
        except (json.JSONDecodeError, ValueError):
            pass

    embedded_json = _extract_first_json_object(cleaned)
    if embedded_json:
        try:
            return _load_json_object(embedded_json)
        except (json.JSONDecodeError, ValueError):
            pass

    raise ValueError(f"無法解析 AI 回應: {cleaned[:200]}")


class TranslationCache:
    """翻譯快取管理"""

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_file = cache_dir / "translations.json"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self):
        """載入快取"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except Exception:
                self._data = {}
        else:
            self._data = {}

    def _save(self):
        """儲存快取"""
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _context_digest(context: Optional[str]) -> str:
        return hashlib.sha256((context or "").encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _endpoint_digest(endpoint: Optional[str]) -> str:
        return hashlib.sha256((endpoint or "").encode("utf-8")).hexdigest()[:16]

    def _make_key(
        self,
        text: str,
        context: Optional[str],
        output_format: str,
        provider: str = "claude-cli",
        model: str = "claude-default",
        prompt_version: str = "v1",
        max_length: int = 30,
        endpoint: Optional[str] = None,
    ) -> str:
        """生成穩定且 provider-aware 的快取 key。"""
        context_digest = self._context_digest(context)
        endpoint_digest = self._endpoint_digest(endpoint)
        return "|".join(
            [
                provider,
                model,
                output_format,
                str(max_length),
                prompt_version,
                endpoint_digest,
                context_digest,
                text,
            ]
        )

    def get(
        self,
        text: str,
        context: Optional[str],
        output_format: str,
        provider: str = "claude-cli",
        model: str = "claude-default",
        prompt_version: str = "v1",
        max_length: int = 30,
        endpoint: Optional[str] = None,
    ) -> Optional[str]:
        key = self._make_key(text, context, output_format, provider, model, prompt_version, max_length, endpoint)
        return self._data.get(key)

    def set(
        self,
        text: str,
        context: Optional[str],
        output_format: str,
        translation: str,
        provider: str = "claude-cli",
        model: str = "claude-default",
        prompt_version: str = "v1",
        max_length: int = 30,
        endpoint: Optional[str] = None,
    ):
        key = self._make_key(text, context, output_format, provider, model, prompt_version, max_length, endpoint)
        self._data[key] = translation
        self._save()

    def set_batch(
        self,
        translations: dict[str, str],
        context: Optional[str],
        output_format: str,
        provider: str = "claude-cli",
        model: str = "claude-default",
        prompt_version: str = "v1",
        max_length: int = 30,
        endpoint: Optional[str] = None,
    ):
        for text, translation in translations.items():
            key = self._make_key(text, context, output_format, provider, model, prompt_version, max_length, endpoint)
            self._data[key] = translation
        self._save()


class Translator:
    """AI 翻譯器"""

    def __init__(
        self,
        context: Optional[str] = None,
        context_file: Optional[Path] = None,
        cache_dir: Optional[Path] = None,
        output_format: OutputFormat = "kebab-case",
        max_length: int = 30,
        provider: Optional[LLMProvider] = None,
        use_cache: bool = True,
        prompt_version: str = "v1",
    ):
        self.output_format = output_format
        self.max_length = max_length
        self.use_cache = use_cache
        self.prompt_version = prompt_version
        self.provider = provider or ClaudeCLIProvider()
        self.context = self._load_context(context, context_file)

        if cache_dir is None:
            cache_dir = Path.cwd() / ".ai-translator-cache"
        self.cache = TranslationCache(cache_dir)

    @property
    def provider_name(self) -> str:
        return getattr(self.provider, "provider_name", self.provider.__class__.__name__)

    @property
    def model_name(self) -> str:
        return getattr(self.provider, "model_name", "default")

    @property
    def endpoint_fingerprint(self) -> str:
        return getattr(self.provider, "endpoint_fingerprint", self.provider_name)

    def _load_context(self, context: Optional[str], context_file: Optional[Path]) -> Optional[str]:
        """載入 context"""
        collected_context = []

        if context:
            collected_context.append(context)

        if context_file:
            context_path = Path(context_file)
            if context_path.exists():
                collected_context.append(f"# From {context_file}\n{context_path.read_text(encoding='utf-8')}")

        env_context = os.environ.get("AI_TRANSLATOR_CONTEXT")
        if env_context:
            collected_context.append(env_context)

        cwd = Path.cwd()
        for pattern in [".context.md", ".context.txt", "CONTEXT.md", "context.md"]:
            context_path = cwd / pattern
            if context_path.exists():
                content = context_path.read_text(encoding="utf-8")
                collected_context.append(f"# From {pattern}\n{content}")
                break

        for agent_doc_name in ["AGENTS.md", "AGENTS.local.md", "CLAUDE.local.md", "CLAUDE.md"]:
            agent_doc = cwd / agent_doc_name
            if not agent_doc.exists():
                continue
            content = agent_doc.read_text(encoding="utf-8")
            if len(content) > 2000:
                content = content[:2000] + "\n...(truncated)"
            collected_context.append(f"# From {agent_doc_name} (project guidance)\n{content}")

        readme_md = cwd / "README.md"
        if readme_md.exists():
            content = readme_md.read_text(encoding="utf-8")
            if len(content) > 1500:
                content = content[:1500] + "\n...(truncated)"
            collected_context.append(f"# From README.md\n{content}")

        docs_dir = cwd / "docs"
        if docs_dir.exists() and docs_dir.is_dir():
            docs_content = []
            for md_file in sorted(docs_dir.glob("*.md"))[:5]:
                content = md_file.read_text(encoding="utf-8")
                if len(content) > 500:
                    content = content[:500] + "\n...(truncated)"
                docs_content.append(f"## {md_file.name}\n{content}")
            if docs_content:
                collected_context.append("# From docs/\n" + "\n\n".join(docs_content))

        return "\n\n---\n\n".join(collected_context) if collected_context else None

    def _format_output(self, text: str) -> str:
        text = text.strip().lower()
        text = re.sub(r'["\']', "", text)
        text = re.sub(r"\s+", " ", text)

        if self.output_format == "kebab-case":
            return re.sub(r"[\s_]+", "-", text)
        if self.output_format == "snake_case":
            return re.sub(r"[\s-]+", "_", text)
        if self.output_format == "camelCase":
            words = re.split(r"[\s_-]+", text)
            return words[0] + "".join(w.capitalize() for w in words[1:])
        if self.output_format == "PascalCase":
            words = re.split(r"[\s_-]+", text)
            return "".join(w.capitalize() for w in words)
        if self.output_format == "lowercase":
            return re.sub(r"[\s_-]+", "", text)
        if self.output_format == "UPPERCASE":
            return re.sub(r"[\s_-]+", "_", text).upper()
        return text

    def _build_prompt(self, texts: list[str]) -> str:
        format_instructions = {
            "kebab-case": "kebab-case（小寫字母和連字號，如 power-board-test）",
            "snake_case": "snake_case（小寫字母和底線，如 power_board_test）",
            "camelCase": "camelCase（駝峰命名，如 powerBoardTest）",
            "PascalCase": "PascalCase（大駝峰命名，如 PowerBoardTest）",
            "lowercase": "lowercase（純小寫無分隔，如 powerboardtest）",
            "UPPERCASE": "UPPERCASE（純大寫底線分隔，如 POWER_BOARD_TEST）",
        }

        format_desc = format_instructions.get(self.output_format, self.output_format)
        texts_list = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(texts))

        prompt = f"""將以下中文文字翻譯為簡短的英文。

要求：
- 使用 {format_desc} 格式
- 每個翻譯不超過 {self.max_length} 個字元
- 翻譯應簡潔且具有描述性
- 輸出格式為 JSON 物件，key 是原始中文，value 是英文翻譯
- 只輸出 JSON，不要有其他文字
"""

        if self.context:
            prompt += f"""
背景資訊（請參考以下 context 來理解專業術語和領域知識）：
---
{self.context}
---
"""

        prompt += f"""
需要翻譯的文字：
{texts_list}"""
        return prompt

    def translate(self, text: str) -> str:
        results = self.batch_translate([text])
        return results.get(text, "translation-failed")

    def batch_translate(self, texts: list[str]) -> dict[str, str]:
        if not texts:
            return {}

        results: dict[str, str] = {}
        texts_to_translate: list[str] = []

        for text in texts:
            cached = None
            if self.use_cache:
                cached = self.cache.get(
                    text=text,
                    context=self.context,
                    output_format=self.output_format,
                    provider=self.provider_name,
                    model=self.model_name,
                    prompt_version=self.prompt_version,
                    max_length=self.max_length,
                    endpoint=self.endpoint_fingerprint,
                )
            if cached:
                results[text] = cached
            else:
                texts_to_translate.append(text)

        if not texts_to_translate:
            return results

        print(f"[AI] 批次翻譯 {len(texts_to_translate)} 個項目...", file=sys.stderr)

        prompt = self._build_prompt(texts_to_translate)

        try:
            output = self.provider.generate(prompt)
            translations = parse_translation_response(output)

            for text in texts_to_translate:
                translated = translations.get(text)
                if translated is None:
                    results[text] = "translation-failed"
                    continue

                formatted = self._format_output(str(translated))
                if len(formatted) <= self.max_length + 10:
                    results[text] = formatted
                else:
                    results[text] = formatted[:self.max_length]

            if self.use_cache:
                new_translations = {
                    text: translation
                    for text, translation in results.items()
                    if text in texts_to_translate and translation != "translation-failed"
                }
                if new_translations:
                    self.cache.set_batch(
                        translations=new_translations,
                        context=self.context,
                        output_format=self.output_format,
                        provider=self.provider_name,
                        model=self.model_name,
                        prompt_version=self.prompt_version,
                        max_length=self.max_length,
                        endpoint=self.endpoint_fingerprint,
                    )

            return results
        except ValueError as exc:
            print(f"[ERROR] JSON 解析失敗: {exc}", file=sys.stderr)
        except Exception as exc:
            print(f"[ERROR] 翻譯失敗: {exc}", file=sys.stderr)

        return {**results, **{t: "translation-failed" for t in texts_to_translate}}


def _env_default(name: str, fallback: Optional[str] = None) -> Optional[str]:
    return os.environ.get(name, fallback)


def _env_int(name: str, fallback: int) -> int:
    value = os.environ.get(name)
    if value is None or value == "":
        return fallback
    try:
        return int(value)
    except ValueError:
        return fallback


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="AI 翻譯工具 - 中文轉英文",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例：
  # 維持預設 Claude CLI 行為
  python ai_translator.py --provider claude-cli "測試流程"

  # OpenAI-compatible HTTP 服務
  python ai_translator.py --provider http --protocol openai \
    --base-url http://localhost:13305/v1 \
    --model user.gemma-4-26B-A4B-it-GGUF \
    "測試流程"

  # Anthropic-compatible HTTP 服務
  python ai_translator.py --provider http --protocol anthropic \
    --base-url http://localhost:13305 \
    --model user.gemma-4-26B-A4B-it-GGUF \
    "測試流程"

  或設定環境變數：
  AI_TRANSLATOR_PROVIDER, AI_TRANSLATOR_PROTOCOL, AI_TRANSLATOR_MODEL,
  AI_TRANSLATOR_BASE_URL, AI_TRANSLATOR_API_KEY, AI_TRANSLATOR_TIMEOUT
        """,
    )

    parser.add_argument("texts", nargs="+", help="要翻譯的中文文字")
    parser.add_argument("--context", "-c", help="提供給 AI 的背景資訊")
    parser.add_argument("--context-file", "-cf", type=Path, help="從檔案載入 context")
    parser.add_argument(
        "--format",
        "-f",
        choices=["kebab-case", "snake_case", "camelCase", "PascalCase", "lowercase", "UPPERCASE"],
        default="kebab-case",
        help="輸出格式（預設: kebab-case）",
    )
    parser.add_argument("--max-length", "-l", type=int, default=30, help="最大輸出長度（預設: 30）")
    parser.add_argument("--cache-dir", type=Path, help="快取目錄")
    parser.add_argument("--json", "-j", action="store_true", help="輸出 JSON 格式")
    parser.add_argument("--no-cache", action="store_true", help="不使用快取")
    parser.add_argument(
        "--provider",
        choices=["claude-cli", "http"],
        default=_env_default("AI_TRANSLATOR_PROVIDER", "claude-cli"),
        help="LLM provider（預設: claude-cli）",
    )
    parser.add_argument(
        "--protocol",
        choices=[OPENAI_PROTOCOL, ANTHROPIC_PROTOCOL],
        default=_env_default("AI_TRANSLATOR_PROTOCOL", OPENAI_PROTOCOL),
        help="HTTP provider 使用的 protocol（預設: openai）",
    )
    parser.add_argument("--model", default=_env_default("AI_TRANSLATOR_MODEL"), help="模型名稱")
    parser.add_argument("--base-url", default=_env_default("AI_TRANSLATOR_BASE_URL"), help="HTTP provider base URL")
    parser.add_argument("--api-key", default=_env_default("AI_TRANSLATOR_API_KEY"), help="HTTP provider API key")
    parser.add_argument(
        "--timeout",
        type=int,
        default=_env_int("AI_TRANSLATOR_TIMEOUT", 120),
        help="provider timeout（秒，預設: 120）",
    )
    return parser


def create_provider_from_args(args) -> LLMProvider:
    if args.provider == "claude-cli":
        return ClaudeCLIProvider(timeout=args.timeout)
    return HTTPProvider(
        protocol=args.protocol,
        base_url=args.base_url,
        model=args.model,
        api_key=args.api_key,
        timeout=args.timeout,
    )


def main(argv: Optional[list[str]] = None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        provider = create_provider_from_args(args)
    except ValueError as exc:
        parser.error(str(exc))

    translator = Translator(
        context=args.context,
        context_file=args.context_file,
        cache_dir=args.cache_dir,
        output_format=args.format,
        max_length=args.max_length,
        use_cache=not args.no_cache,
        provider=provider,
    )

    results = translator.batch_translate(args.texts)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for original, translated in results.items():
            print(f"{original} → {translated}")


if __name__ == "__main__":
    main()
