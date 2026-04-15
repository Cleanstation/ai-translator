from pathlib import Path

from ai_translator import Translator


class FakeProvider:
    provider_name = "fake"
    model_name = "fake-model"

    def __init__(self, response: str, endpoint_fingerprint: str = "fake|local"):
        self.response = response
        self.prompts = []
        self.endpoint_fingerprint = endpoint_fingerprint

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.response


def test_translator_uses_injected_provider(tmp_path: Path):
    provider = FakeProvider('{"電源板": "power board"}')
    translator = Translator(
        cache_dir=tmp_path,
        provider=provider,
        context=None,
        output_format="kebab-case",
    )

    result = translator.batch_translate(["電源板"])

    assert result == {"電源板": "power-board"}
    assert len(provider.prompts) == 1


def test_translator_can_disable_cache(tmp_path: Path):
    provider = FakeProvider('{"電源板": "power board"}')
    translator = Translator(
        cache_dir=tmp_path,
        provider=provider,
        use_cache=False,
    )

    translator.batch_translate(["電源板"])
    translator.batch_translate(["電源板"])

    assert len(provider.prompts) == 2


def test_translator_uses_cache_by_default(tmp_path: Path):
    provider = FakeProvider('{"電源板": "power board"}')
    translator = Translator(
        cache_dir=tmp_path,
        provider=provider,
    )

    translator.batch_translate(["電源板"])
    translator.batch_translate(["電源板"])

    assert len(provider.prompts) == 1


def test_translator_cache_distinguishes_provider_endpoints(tmp_path: Path):
    provider1 = FakeProvider(
        '{"電源板": "power board"}',
        endpoint_fingerprint="openai|http://localhost:13305/v1",
    )
    translator1 = Translator(cache_dir=tmp_path, provider=provider1)
    result1 = translator1.batch_translate(["電源板"])

    provider2 = FakeProvider(
        '{"電源板": "board power"}',
        endpoint_fingerprint="openai|http://127.0.0.1:13305/v1",
    )
    translator2 = Translator(cache_dir=tmp_path, provider=provider2)
    result2 = translator2.batch_translate(["電源板"])

    assert result1 == {"電源板": "power-board"}
    assert result2 == {"電源板": "board-power"}
    assert len(provider1.prompts) == 1
    assert len(provider2.prompts) == 1


def test_translator_loads_agents_md_as_project_context(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "AGENTS.md").write_text("# Project Agent Notes\nImportant glossary", encoding="utf-8")

    translator = Translator(cache_dir=tmp_path / ".cache", provider=FakeProvider('{"測試": "test"}'))

    assert translator.context is not None
    assert "# From AGENTS.md" in translator.context
    assert "Important glossary" in translator.context
