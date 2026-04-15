# ai-translator Multi-Provider Phase 2 Implementation Plan

> **For Hermes:** Follow strict TDD for code changes. Write the failing test first, run it to confirm failure, then implement the minimum code to pass.

**Goal:** Add a real HTTP provider path to `ai_translator.py`, expose provider/protocol/model/base-url/api-key/timeout settings through CLI and environment variables, and make Lemonade reachable as the first supported local HTTP backend.

**Architecture:** Keep the code single-file for now. Add `HTTPProvider` beside `ClaudeCLIProvider`, plus a small provider factory for CLI/env settings. Support two HTTP protocols: `openai` (`/chat/completions`) and `anthropic` (`/v1/messages`). Keep `Translator` unaware of transport details; it should only receive a provider instance.

**Tech Stack:** Python 3.10+, `pytest`, standard library only (`urllib.request`, `json`, `argparse`).

---

## Current Context

- Phase 1 is complete: provider abstraction, stable cache keys, parser extraction, and `--no-cache` are implemented.
- The project still defaults to Claude CLI.
- There is no HTTP provider yet.
- README and package metadata still present the tool as Claude-only.
- Local Lemonade is already running at `localhost:13305`, with an OpenAI-compatible path observed in service logs.

## Desired Phase 2 Outcome

After this phase:

- `ai-translator` can use `--provider http`.
- `--protocol openai` works against OpenAI-compatible services such as Lemonade.
- `--protocol anthropic` works against Anthropic-compatible services.
- CLI supports `--provider --protocol --model --base-url --api-key --timeout`.
- Environment variables can provide defaults for those settings.
- Cache keys distinguish HTTP endpoint/protocol differences.
- README reflects multi-provider support and includes Lemonade examples.

## Files Likely to Change

- Modify: `ai_translator.py`
- Modify: `README.md`
- Modify: `pyproject.toml` (only if metadata needs updating now)
- Modify: `tests/test_cache.py`
- Create: `tests/test_http_provider.py`
- Create: `tests/test_cli_config.py`

---

### Task 1: Add failing cache-key test for endpoint/protocol separation

**Objective:** Ensure HTTP results from different protocols or endpoints cannot share cache entries.

**Files:**
- Modify: `tests/test_cache.py`
- Modify later: `ai_translator.py`

**Step 1: Write failing test**

Add a test asserting cache keys differ when only the endpoint fingerprint changes.

```python
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
```

**Step 2: Run test to verify failure**

Run:

```bash
uv run --dev pytest tests/test_cache.py -v
```

Expected: FAIL because `endpoint` is not part of the cache key yet.

**Step 3: Write minimal implementation**

Extend cache key generation to accept an optional endpoint fingerprint.

**Step 4: Run test to verify pass**

Run:

```bash
uv run --dev pytest tests/test_cache.py -v
```

Expected: PASS.

---

### Task 2: Add failing HTTP provider tests for OpenAI-compatible requests

**Objective:** Lock down the OpenAI HTTP request/response contract before implementation.

**Files:**
- Create: `tests/test_http_provider.py`
- Modify later: `ai_translator.py`

**Step 1: Write failing test**

Add a test that verifies:

- request URL becomes `<base_url>/chat/completions`
- `Authorization: Bearer ...` is sent when API key is provided
- request payload contains `model` and a user message with the prompt
- response content is extracted from `choices[0].message.content`

**Step 2: Run test to verify failure**

Run:

```bash
uv run --dev pytest tests/test_http_provider.py::test_http_provider_openai_posts_chat_completions_and_returns_text -v
```

Expected: FAIL because `HTTPProvider` does not exist.

**Step 3: Write minimal implementation**

Implement `HTTPProvider(protocol="openai", ...)` using `urllib.request`.

**Step 4: Run test to verify pass**

Run the same test and expect PASS.

---

### Task 3: Add failing HTTP provider tests for Anthropic-compatible requests

**Objective:** Lock down Anthropic request/response behavior and base URL normalization.

**Files:**
- Modify: `tests/test_http_provider.py`
- Modify later: `ai_translator.py`

**Step 1: Write failing test**

Add a test that verifies:

- request URL becomes `<base_url>/v1/messages`
- `anthropic-version: 2023-06-01` header is sent
- `Authorization: Bearer ...` is sent when API key is provided
- response content text blocks are concatenated/extracted correctly

**Step 2: Run test to verify failure**

Run:

```bash
uv run --dev pytest tests/test_http_provider.py::test_http_provider_anthropic_posts_messages_and_returns_text -v
```

Expected: FAIL.

**Step 3: Write minimal implementation**

Add Anthropic request path and content extraction logic.

**Step 4: Run test to verify pass**

Run the same test and expect PASS.

---

### Task 4: Add failing config/factory tests for CLI and env defaults

**Objective:** Make provider selection testable without invoking the real network or Claude CLI.

**Files:**
- Create: `tests/test_cli_config.py`
- Modify later: `ai_translator.py`

**Step 1: Write failing tests**

Add tests for:

- env vars populate parser defaults
- `create_provider_from_args()` returns `ClaudeCLIProvider` by default
- `create_provider_from_args()` returns `HTTPProvider` for `--provider http`

Suggested env vars:

- `AI_TRANSLATOR_PROVIDER`
- `AI_TRANSLATOR_PROTOCOL`
- `AI_TRANSLATOR_MODEL`
- `AI_TRANSLATOR_BASE_URL`
- `AI_TRANSLATOR_API_KEY`
- `AI_TRANSLATOR_TIMEOUT`

**Step 2: Run test to verify failure**

Run:

```bash
uv run --dev pytest tests/test_cli_config.py -v
```

Expected: FAIL because parser/factory helpers do not exist.

**Step 3: Write minimal implementation**

Add:

- `build_arg_parser()`
- `create_provider_from_args(args)`
- env-backed defaults in parser arguments

**Step 4: Run test to verify pass**

Run the same file and expect PASS.

---

### Task 5: Wire endpoint fingerprint into Translator cache usage

**Objective:** Ensure provider endpoint differences affect runtime cache lookup.

**Files:**
- Modify: `tests/test_translator.py`
- Modify later: `ai_translator.py`

**Step 1: Write failing test**

Add a test with two fake providers that share model/provider names but expose different endpoint fingerprints, and assert they do not reuse each other’s cache entries.

**Step 2: Run test to verify failure**

Run:

```bash
uv run --dev pytest tests/test_translator.py -v
```

Expected: FAIL because Translator does not yet incorporate provider endpoint metadata into cache calls.

**Step 3: Write minimal implementation**

Add a provider endpoint/fingerprint property and pass it through cache get/set operations.

**Step 4: Run test to verify pass**

Run the same file and expect PASS.

---

### Task 6: Update CLI help text and README

**Objective:** Reflect the new multi-provider behavior in user-facing docs.

**Files:**
- Modify: `README.md`
- Modify: `ai_translator.py`

**Step 1: Write documentation updates**

Update README to show:

- default Claude CLI usage
- HTTP OpenAI-compatible usage
- Lemonade example using `http://localhost:13305/v1`
- Anthropic-compatible example using root base URL

**Step 2: Verify example consistency**

Check CLI help and README examples align with implemented flag names and semantics.

---

### Task 7: Run full validation and smoke checks

**Objective:** Confirm Phase 2 works end-to-end without breaking Phase 1.

**Files:**
- No new files required unless fixes are needed

**Step 1: Run full automated tests**

```bash
uv run --dev pytest tests/ -q
```

Expected: all tests pass.

**Step 2: Run local factory smoke checks**

```bash
python - <<'PY'
from ai_translator import build_arg_parser, create_provider_from_args
args = build_arg_parser().parse_args([
    '--provider', 'http',
    '--protocol', 'openai',
    '--base-url', 'http://localhost:13305/v1',
    '--model', 'user.gemma-4-26B-A4B-it-GGUF',
    '測試'
])
provider = create_provider_from_args(args)
print(type(provider).__name__)
print(provider.provider_name)
print(provider.model_name)
print(provider.endpoint_fingerprint)
PY
```

Expected: `HTTPProvider` with a stable endpoint fingerprint.

**Step 3: Optional non-invasive Lemonade request smoke test**

Only if policy and environment allow outbound/local HTTP requests from this session, run a tiny translation request against the local Lemonade OpenAI-compatible path. If such requests are blocked, stop at factory/unit validation and document the limitation.

---

## Risks and Tradeoffs

- Adding both OpenAI and Anthropic support in one phase increases scope, but it aligns with the user’s local-provider preferences and avoids an awkward half-finished CLI.
- Keeping HTTP logic in `ai_translator.py` is acceptable for now, but future phases should likely split providers into separate modules.
- Real Lemonade smoke tests may be blocked by tool/network policy, so unit tests must be strong enough to validate protocol behavior in isolation.

## Verification Checklist

- [ ] `--provider http` works
- [ ] `--protocol openai` and `--protocol anthropic` are both implemented
- [ ] env vars provide defaults for provider settings
- [ ] cache key/runtime cache lookup distinguish endpoint/protocol differences
- [ ] README examples are updated
- [ ] all tests pass

## Follow-up After Phase 2

1. Add structured retry/error reporting for HTTP providers
2. Optionally split providers/parser/config into separate modules
3. Add real Lemonade integration tests if a safe local HTTP test path is available
4. Consider package metadata updates in `pyproject.toml` to remove Claude-only wording
