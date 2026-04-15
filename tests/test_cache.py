from pathlib import Path

from ai_translator import TranslationCache


def test_translation_cache_can_be_imported(tmp_path: Path):
    cache = TranslationCache(tmp_path)
    assert cache is not None


def test_cache_key_includes_provider_model_and_prompt_dimensions(tmp_path: Path):
    cache = TranslationCache(tmp_path)

    key1 = cache._make_key(
        text="電源板",
        context="context",
        output_format="kebab-case",
        provider="claude-cli",
        model="claude-default",
        prompt_version="v1",
        max_length=30,
    )
    key2 = cache._make_key(
        text="電源板",
        context="context",
        output_format="kebab-case",
        provider="http",
        model="gemma",
        prompt_version="v1",
        max_length=30,
    )
    key3 = cache._make_key(
        text="電源板",
        context="context",
        output_format="kebab-case",
        provider="claude-cli",
        model="claude-default",
        prompt_version="v2",
        max_length=30,
    )
    key4 = cache._make_key(
        text="電源板",
        context="context",
        output_format="kebab-case",
        provider="claude-cli",
        model="claude-default",
        prompt_version="v1",
        max_length=20,
    )

    assert key1 != key2
    assert key1 != key3
    assert key1 != key4
    assert key1 == cache._make_key(
        text="電源板",
        context="context",
        output_format="kebab-case",
        provider="claude-cli",
        model="claude-default",
        prompt_version="v1",
        max_length=30,
    )


def test_cache_key_distinguishes_http_endpoints(tmp_path: Path):
    cache = TranslationCache(tmp_path)

    key1 = cache._make_key(
        text="電源板",
        context="context",
        output_format="kebab-case",
        provider="http",
        model="user.gemma-4-26B-A4B-it-GGUF",
        prompt_version="v1",
        max_length=30,
        endpoint="http://localhost:13305/v1",
    )
    key2 = cache._make_key(
        text="電源板",
        context="context",
        output_format="kebab-case",
        provider="http",
        model="user.gemma-4-26B-A4B-it-GGUF",
        prompt_version="v1",
        max_length=30,
        endpoint="http://127.0.0.1:13305/v1",
    )

    assert key1 != key2
