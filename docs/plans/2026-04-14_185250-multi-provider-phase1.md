# ai-translator Multi-Provider Phase 1 Implementation Plan

> **For Hermes:** Follow strict TDD for code changes. Write the failing test first, run it to confirm failure, then implement the minimum code to pass.

**Goal:** Refactor `ai_translator.py` so the existing Claude-based behavior is preserved while introducing a provider abstraction, stable cache keys, a dedicated response parser, and a working `--no-cache` flag.

**Architecture:** Keep the project single-file for now to minimize churn. Introduce small internal abstractions inside `ai_translator.py`: `LLMProvider`, `ClaudeCLIProvider`, parser helpers, and cache metadata helpers. Add a new `tests/` directory so Phase 1 changes are protected by repeatable tests before Phase 2 adds HTTP support.

**Tech Stack:** Python 3.10+, `pytest`, standard library only.

---

## Current Context

- The project currently has no `tests/` directory.
- `ai_translator.py` contains provider logic, parsing logic, cache logic, and CLI logic in one file.
- Cache keys currently use Python `hash()`, which is not stable across processes.
- `--no-cache` is exposed in the CLI but is ignored at runtime.
- The user prefers larger changes to start with a written implementation plan in `docs/` before coding.

## Desired Phase 1 Outcome

After this phase:

- Existing default CLI behavior still uses Claude CLI.
- `Translator` delegates model calls through a provider object.
- Cache keys are stable and include provider/model/prompt-related dimensions.
- JSON parsing is extracted into a dedicated helper with predictable fallbacks.
- `--no-cache` truly bypasses cache reads and writes.
- Tests cover cache key stability, parser behavior, provider delegation, and no-cache behavior.

## Files Likely to Change

- Modify: `ai_translator.py`
- Create: `tests/test_cache.py`
- Create: `tests/test_parser.py`
- Create: `tests/test_translator.py`
- Modify later in follow-up phase: `README.md`, `pyproject.toml`

---

### Task 1: Add test scaffolding and pytest dependency

**Objective:** Create a runnable test baseline before refactoring production code.

**Files:**
- Modify: `pyproject.toml`
- Create: `tests/test_cache.py`

**Step 1: Write failing test**

Create `tests/test_cache.py` with a smoke test that imports `TranslationCache` from `ai_translator`.

```python
from pathlib import Path
from ai_translator import TranslationCache


def test_translation_cache_can_be_imported(tmp_path: Path):
    cache = TranslationCache(tmp_path)
    assert cache is not None
```

**Step 2: Run test to verify failure**

Run:

```bash
pytest tests/test_cache.py::test_translation_cache_can_be_imported -v
```

Expected initially: may fail because `pytest` is not installed in the project environment.

**Step 3: Add minimal test dependency support**

Update `pyproject.toml` to include a `dev` dependency group or minimal pytest dependency path for local test runs.

**Step 4: Run test to verify pass**

Run:

```bash
pytest tests/test_cache.py::test_translation_cache_can_be_imported -v
```

Expected: PASS.

---

### Task 2: Capture the current cache-key bug in a failing test

**Objective:** Prove the new cache key must be deterministic and provider-aware.

**Files:**
- Modify: `tests/test_cache.py`
- Modify later: `ai_translator.py`

**Step 1: Write failing test**

Add tests that assert:

- keys are stable for the same inputs
- keys differ when provider changes
- keys differ when model changes
- keys differ when prompt version or max length changes

Suggested test shape:

```python
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

    assert key1 != key2
```

**Step 2: Run test to verify failure**

Run:

```bash
pytest tests/test_cache.py -v
```

Expected: FAIL because the current `_make_key()` signature does not accept those fields.

**Step 3: Write minimal implementation**

Update `TranslationCache` to:

- compute a stable context digest using `hashlib.sha256`
- accept provider/model/prompt_version/max_length
- build a structured key string

**Step 4: Run tests to verify pass**

Run:

```bash
pytest tests/test_cache.py -v
```

Expected: PASS.

---

### Task 3: Add parser tests before extracting parser logic

**Objective:** Lock down the desired parsing behavior before moving code.

**Files:**
- Create: `tests/test_parser.py`
- Modify later: `ai_translator.py`

**Step 1: Write failing tests**

Add tests for:

- direct JSON string parsing
- fenced JSON block parsing
- surrounding prose with embedded JSON object
- invalid output raising a parse error

Suggested cases:

```python
def test_parse_translations_accepts_raw_json():
    output = '{"電源板": "power-board"}'
    assert parse_translation_response(output) == {"電源板": "power-board"}


def test_parse_translations_accepts_fenced_json():
    output = '```json\n{"電源板": "power-board"}\n```'
    assert parse_translation_response(output) == {"電源板": "power-board"}
```

**Step 2: Run test to verify failure**

Run:

```bash
pytest tests/test_parser.py -v
```

Expected: FAIL because `parse_translation_response` does not exist yet.

**Step 3: Write minimal implementation**

Add a parser helper in `ai_translator.py` that:

1. tries `json.loads(output)`
2. tries fenced JSON extraction
3. tries locating a JSON object in surrounding prose
4. raises `ValueError` if parsing fails

**Step 4: Run test to verify pass**

Run:

```bash
pytest tests/test_parser.py -v
```

Expected: PASS.

---

### Task 4: Add provider delegation tests before refactoring Translator

**Objective:** Prove `Translator` can work through an injected provider without changing public behavior.

**Files:**
- Create: `tests/test_translator.py`
- Modify later: `ai_translator.py`

**Step 1: Write failing test**

Create a fake provider and assert `Translator.batch_translate()` consumes it.

```python
class FakeProvider:
    provider_name = "fake"
    model_name = "fake-model"

    def __init__(self, response: str):
        self.response = response
        self.prompts = []

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
```

**Step 2: Run test to verify failure**

Run:

```bash
pytest tests/test_translator.py::test_translator_uses_injected_provider -v
```

Expected: FAIL because `Translator` does not accept a `provider` argument yet.

**Step 3: Write minimal implementation**

Inside `ai_translator.py`:

- add `LLMProvider` base class
- add `ClaudeCLIProvider`
- let `Translator.__init__()` accept `provider: Optional[LLMProvider] = None`
- default to `ClaudeCLIProvider()` when provider is omitted
- make `batch_translate()` call `self.provider.generate(prompt)`

**Step 4: Run test to verify pass**

Run:

```bash
pytest tests/test_translator.py::test_translator_uses_injected_provider -v
```

Expected: PASS.

---

### Task 5: Add no-cache behavior tests before wiring the flag

**Objective:** Make `--no-cache` and runtime cache bypass behavior real.

**Files:**
- Modify: `tests/test_translator.py`
- Modify later: `ai_translator.py`

**Step 1: Write failing tests**

Add tests for:

- `use_cache=False` should call the provider twice for repeated translations
- `use_cache=True` should call the provider once and reuse cache

Suggested shape:

```python
def test_translator_can_disable_cache(tmp_path: Path):
    provider = FakeProvider('{"電源板": "power board"}')
    translator = Translator(cache_dir=tmp_path, provider=provider, use_cache=False)

    translator.batch_translate(["電源板"])
    translator.batch_translate(["電源板"])

    assert len(provider.prompts) == 2
```

**Step 2: Run test to verify failure**

Run:

```bash
pytest tests/test_translator.py -v
```

Expected: FAIL because `use_cache` is not implemented.

**Step 3: Write minimal implementation**

- Add `use_cache: bool = True` to `Translator`
- Bypass cache reads/writes when disabled
- Pass `use_cache=not args.no_cache` from CLI

**Step 4: Run test to verify pass**

Run:

```bash
pytest tests/test_translator.py -v
```

Expected: PASS.

---

### Task 6: Update CLI wiring without changing default user behavior

**Objective:** Preserve current UX while connecting the new runtime behavior.

**Files:**
- Modify: `ai_translator.py`

**Step 1: Write failing test**

If practical, add a CLI-level test using `subprocess` or direct `main()` argument patching to verify `--no-cache` influences translator construction. If not practical in this repository, document the runtime verification instead and cover behavior through `Translator` tests.

**Step 2: Run test to verify failure**

Run the relevant targeted test.

**Step 3: Write minimal implementation**

- Keep the existing CLI flags
- Pass `use_cache=not args.no_cache` into `Translator`
- Preserve default behavior when `--no-cache` is absent

**Step 4: Run tests to verify pass**

Run:

```bash
pytest tests/test_translator.py -v
```

Expected: PASS.

---

### Task 7: Run the full suite and manual smoke checks

**Objective:** Confirm the refactor works end-to-end.

**Files:**
- Modify if needed: `README.md` only if behavior/documentation diverges during implementation

**Step 1: Run full automated tests**

```bash
pytest tests/ -q
```

Expected: all tests pass.

**Step 2: Run a manual import smoke test**

```bash
python - <<'PY'
from ai_translator import Translator, ClaudeCLIProvider
print(Translator)
print(ClaudeCLIProvider)
PY
```

Expected: both symbols import successfully.

**Step 3: Run a cache persistence smoke test**

Use a fake provider in a small inline script to ensure repeated translations hit cache when enabled.

**Step 4: Review diff for scope control**

```bash
git diff -- ai_translator.py tests/ pyproject.toml docs/
```

Expected: Phase 1 stays focused on internal refactor + tests.

---

## Risks and Tradeoffs

- Keeping everything in `ai_translator.py` minimizes churn now, but increases file size temporarily.
- Parser extraction may reveal previously hidden edge cases in Claude output formatting.
- If pytest is not already available in the execution environment, local validation must first install or expose it.
- We should not add HTTP provider logic in this phase; that would dilute the scope and reduce reviewability.

## Verification Checklist

- [ ] `Translator` still defaults to Claude CLI when no provider is passed
- [ ] cache key no longer uses Python `hash()`
- [ ] cache key includes provider/model/prompt-sensitive dimensions
- [ ] parser handles raw JSON, fenced JSON, and embedded JSON
- [ ] `--no-cache` actually disables cache reads and writes
- [ ] tests exist and pass
- [ ] no HTTP provider logic added yet

## Follow-up After Phase 1

1. Add `HTTPProvider` with `protocol=openai`
2. Add CLI flags for provider/model/base-url/api-key/timeout
3. Update README and package metadata from Claude-only to multi-provider
4. Run a real Lemonade integration smoke test against `http://localhost:13305/v1`
