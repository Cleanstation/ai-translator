#!/usr/bin/env python3
"""
ai_translator.py - 通用 AI 翻譯模組

提供中文到英文的翻譯功能，支援：
- 批次翻譯（減少 API 呼叫）
- JSON 快取（避免重複翻譯）
- 自訂 context（提供背景資訊給 AI）
- 多種輸出格式（kebab-case、snake_case、camelCase 等）

Context 提供方式：
1. 直接傳入字串
2. 從檔案讀取（.context.md 或 .context.txt）
3. 從環境變數讀取

用法範例：
    from ai_translator import Translator

    # 基本使用
    translator = Translator()
    result = translator.translate("測試流程", output_format="kebab-case")

    # 帶 context 的翻譯
    translator = Translator(context="這是一個廚餘機產品的 FCT 測試文件")
    results = translator.batch_translate(["電源板", "顯示板", "成品測試"])

    # 從檔案載入 context
    translator = Translator(context_file="project.context.md")

CLI 用法：
    # 單一翻譯
    python ai_translator.py "測試流程"

    # 批次翻譯
    python ai_translator.py "電源板" "顯示板" "成品測試"

    # 帶 context
    python ai_translator.py --context "FCT 測試相關" "電源板測試"

    # 從檔案載入 context
    python ai_translator.py --context-file project.context.md "電源板測試"

    # 指定輸出格式
    python ai_translator.py --format snake_case "測試流程"
"""

import os
import re
import sys
import json
import subprocess
import argparse
from pathlib import Path
from typing import Optional, Literal
from dataclasses import dataclass

# 輸出格式類型
OutputFormat = Literal["kebab-case", "snake_case", "camelCase", "PascalCase", "lowercase", "UPPERCASE"]


@dataclass
class TranslationConfig:
    """翻譯設定"""
    output_format: OutputFormat = "kebab-case"
    max_length: int = 30
    cache_dir: Optional[Path] = None
    context: Optional[str] = None
    context_file: Optional[Path] = None


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
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self._data = json.load(f)
            except:
                self._data = {}
        else:
            self._data = {}

    def _save(self):
        """儲存快取"""
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def _make_key(self, text: str, context: Optional[str], output_format: str) -> str:
        """生成快取 key（包含 context hash 以區分不同 context 的翻譯）"""
        context_hash = hash(context or "") % 10000
        return f"{output_format}|{context_hash}|{text}"

    def get(self, text: str, context: Optional[str], output_format: str) -> Optional[str]:
        """取得快取值"""
        key = self._make_key(text, context, output_format)
        return self._data.get(key)

    def set(self, text: str, context: Optional[str], output_format: str, translation: str):
        """設定快取值"""
        key = self._make_key(text, context, output_format)
        self._data[key] = translation
        self._save()

    def set_batch(self, translations: dict, context: Optional[str], output_format: str):
        """批次設定快取"""
        for text, translation in translations.items():
            key = self._make_key(text, context, output_format)
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
        max_length: int = 30
    ):
        """
        初始化翻譯器

        Args:
            context: 直接提供的 context 字串
            context_file: context 檔案路徑
            cache_dir: 快取目錄（預設為 .ai-translator-cache）
            output_format: 輸出格式
            max_length: 最大輸出長度
        """
        self.output_format = output_format
        self.max_length = max_length

        # 載入 context
        self.context = self._load_context(context, context_file)

        # 初始化快取
        if cache_dir is None:
            cache_dir = Path.cwd() / ".ai-translator-cache"
        self.cache = TranslationCache(cache_dir)

    def _load_context(self, context: Optional[str], context_file: Optional[Path]) -> Optional[str]:
        """載入 context

        自動搜尋順序：
        1. 直接提供的 context 字串
        2. 指定的 context_file
        3. 環境變數 AI_TRANSLATOR_CONTEXT
        4. 自動收集專案文件：
           - .context.md / .context.txt / CONTEXT.md
           - CLAUDE.md（專案描述）
           - README.md（專案說明）
           - docs/*.md（文件目錄）
        """
        collected_context = []

        # 優先使用直接提供的 context
        if context:
            collected_context.append(context)

        # 從指定檔案載入
        if context_file:
            context_path = Path(context_file)
            if context_path.exists():
                collected_context.append(f"# From {context_file}\n{context_path.read_text(encoding='utf-8')}")

        # 從環境變數載入
        env_context = os.environ.get('AI_TRANSLATOR_CONTEXT')
        if env_context:
            collected_context.append(env_context)

        # 自動搜尋專案 context 檔案
        cwd = Path.cwd()

        # 專用 context 檔案（優先）
        for pattern in ['.context.md', '.context.txt', 'CONTEXT.md', 'context.md']:
            context_path = cwd / pattern
            if context_path.exists():
                content = context_path.read_text(encoding='utf-8')
                collected_context.append(f"# From {pattern}\n{content}")
                break  # 只載入一個專用 context 檔

        # CLAUDE.md（通常包含專案描述和術語）
        claude_md = cwd / 'CLAUDE.md'
        if claude_md.exists():
            content = claude_md.read_text(encoding='utf-8')
            # 只取前 2000 字作為 context，避免太長
            if len(content) > 2000:
                content = content[:2000] + "\n...(truncated)"
            collected_context.append(f"# From CLAUDE.md (project description)\n{content}")

        # README.md
        readme_md = cwd / 'README.md'
        if readme_md.exists():
            content = readme_md.read_text(encoding='utf-8')
            # 只取前 1500 字
            if len(content) > 1500:
                content = content[:1500] + "\n...(truncated)"
            collected_context.append(f"# From README.md\n{content}")

        # docs/ 目錄下的 markdown 檔案
        docs_dir = cwd / 'docs'
        if docs_dir.exists() and docs_dir.is_dir():
            docs_content = []
            for md_file in sorted(docs_dir.glob('*.md'))[:5]:  # 最多 5 個檔案
                content = md_file.read_text(encoding='utf-8')
                # 每個檔案取前 500 字
                if len(content) > 500:
                    content = content[:500] + "\n...(truncated)"
                docs_content.append(f"## {md_file.name}\n{content}")
            if docs_content:
                collected_context.append(f"# From docs/\n" + "\n\n".join(docs_content))

        return "\n\n---\n\n".join(collected_context) if collected_context else None

    def _format_output(self, text: str) -> str:
        """格式化輸出"""
        # 先清理文字
        text = text.strip().lower()
        text = re.sub(r'["\']', '', text)
        text = re.sub(r'\s+', ' ', text)

        if self.output_format == "kebab-case":
            return re.sub(r'[\s_]+', '-', text)
        elif self.output_format == "snake_case":
            return re.sub(r'[\s-]+', '_', text)
        elif self.output_format == "camelCase":
            words = re.split(r'[\s_-]+', text)
            return words[0] + ''.join(w.capitalize() for w in words[1:])
        elif self.output_format == "PascalCase":
            words = re.split(r'[\s_-]+', text)
            return ''.join(w.capitalize() for w in words)
        elif self.output_format == "lowercase":
            return re.sub(r'[\s_-]+', '', text)
        elif self.output_format == "UPPERCASE":
            return re.sub(r'[\s_-]+', '_', text).upper()
        else:
            return text

    def _build_prompt(self, texts: list[str]) -> str:
        """建立翻譯 prompt"""
        format_instructions = {
            "kebab-case": "kebab-case（小寫字母和連字號，如 power-board-test）",
            "snake_case": "snake_case（小寫字母和底線，如 power_board_test）",
            "camelCase": "camelCase（駝峰命名，如 powerBoardTest）",
            "PascalCase": "PascalCase（大駝峰命名，如 PowerBoardTest）",
            "lowercase": "lowercase（純小寫無分隔，如 powerboardtest）",
            "UPPERCASE": "UPPERCASE（純大寫底線分隔，如 POWER_BOARD_TEST）",
        }

        format_desc = format_instructions.get(self.output_format, self.output_format)

        texts_list = "\n".join(f"{i+1}. {t}" for i, t in enumerate(texts))

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
        """
        翻譯單一文字

        Args:
            text: 要翻譯的中文文字

        Returns:
            翻譯後的英文
        """
        results = self.batch_translate([text])
        return results.get(text, "translation-failed")

    def batch_translate(self, texts: list[str]) -> dict[str, str]:
        """
        批次翻譯多個文字

        Args:
            texts: 要翻譯的中文文字列表

        Returns:
            dict: {原始文字: 翻譯結果}
        """
        if not texts:
            return {}

        # 檢查快取
        results = {}
        texts_to_translate = []

        for text in texts:
            cached = self.cache.get(text, self.context, self.output_format)
            if cached:
                results[text] = cached
            else:
                texts_to_translate.append(text)

        # 如果全部都有快取，直接返回
        if not texts_to_translate:
            return results

        # 呼叫 AI 翻譯
        print(f"[AI] 批次翻譯 {len(texts_to_translate)} 個項目...", file=sys.stderr)

        prompt = self._build_prompt(texts_to_translate)

        try:
            result = subprocess.run(
                ['claude', '--print', prompt],
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode != 0:
                print(f"[ERROR] Claude 呼叫失敗: {result.stderr}", file=sys.stderr)
                return {**results, **{t: "translation-failed" for t in texts_to_translate}}

            # 解析 JSON 結果
            output = result.stdout.strip()

            # 嘗試從輸出中提取 JSON
            json_match = re.search(r'\{[^{}]*\}', output, re.DOTALL)
            if json_match:
                translations = json.loads(json_match.group())

                # 格式化並驗證結果
                for original, translated in translations.items():
                    formatted = self._format_output(translated)
                    if len(formatted) <= self.max_length + 10:  # 允許一點彈性
                        results[original] = formatted
                    else:
                        results[original] = formatted[:self.max_length]

                # 儲存到快取
                new_translations = {k: v for k, v in results.items() if k in texts_to_translate}
                self.cache.set_batch(new_translations, self.context, self.output_format)

                return results
            else:
                print(f"[ERROR] 無法解析 AI 回應: {output[:200]}", file=sys.stderr)
                return {**results, **{t: "translation-failed" for t in texts_to_translate}}

        except subprocess.TimeoutExpired:
            print("[ERROR] Claude 呼叫超時", file=sys.stderr)
            return {**results, **{t: "translation-failed" for t in texts_to_translate}}
        except json.JSONDecodeError as e:
            print(f"[ERROR] JSON 解析失敗: {e}", file=sys.stderr)
            return {**results, **{t: "translation-failed" for t in texts_to_translate}}
        except Exception as e:
            print(f"[ERROR] 翻譯失敗: {e}", file=sys.stderr)
            return {**results, **{t: "translation-failed" for t in texts_to_translate}}


def main():
    """CLI 入口"""
    parser = argparse.ArgumentParser(
        description="AI 翻譯工具 - 中文轉英文",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例：
  # 單一翻譯
  python ai_translator.py "測試流程"

  # 批次翻譯
  python ai_translator.py "電源板" "顯示板" "成品測試"

  # 帶 context
  python ai_translator.py --context "FCT 測試文件" "電源板測試"

  # 從檔案載入 context
  python ai_translator.py --context-file project.context.md "電源板測試"

  # 指定輸出格式
  python ai_translator.py --format snake_case "測試流程"

Context 自動載入：
  腳本會自動搜尋以下檔案作為 context：
  - .context.md
  - .context.txt
  - CONTEXT.md
  - context.md

  或設定環境變數：AI_TRANSLATOR_CONTEXT
        """
    )

    parser.add_argument(
        'texts',
        nargs='+',
        help='要翻譯的中文文字'
    )

    parser.add_argument(
        '--context', '-c',
        help='提供給 AI 的背景資訊'
    )

    parser.add_argument(
        '--context-file', '-cf',
        type=Path,
        help='從檔案載入 context'
    )

    parser.add_argument(
        '--format', '-f',
        choices=['kebab-case', 'snake_case', 'camelCase', 'PascalCase', 'lowercase', 'UPPERCASE'],
        default='kebab-case',
        help='輸出格式（預設: kebab-case）'
    )

    parser.add_argument(
        '--max-length', '-l',
        type=int,
        default=30,
        help='最大輸出長度（預設: 30）'
    )

    parser.add_argument(
        '--cache-dir',
        type=Path,
        help='快取目錄'
    )

    parser.add_argument(
        '--json', '-j',
        action='store_true',
        help='輸出 JSON 格式'
    )

    parser.add_argument(
        '--no-cache',
        action='store_true',
        help='不使用快取'
    )

    args = parser.parse_args()

    # 初始化翻譯器
    translator = Translator(
        context=args.context,
        context_file=args.context_file,
        cache_dir=args.cache_dir,
        output_format=args.format,
        max_length=args.max_length
    )

    # 執行翻譯
    results = translator.batch_translate(args.texts)

    # 輸出結果
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for original, translated in results.items():
            print(f"{original} → {translated}")


if __name__ == "__main__":
    main()
