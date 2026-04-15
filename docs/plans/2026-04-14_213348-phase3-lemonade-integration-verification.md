# ai-translator Lemonade Phase 3 Verification Plan

> **For Hermes:** Follow strict TDD for code changes. Prefer non-invasive verification first. Do not mutate Lemonade runtime unless verification proves it is necessary.

**Goal:** Verify the newly added HTTP provider path against the local Lemonade deployment, capture any real integration mismatches, and document exact working commands for OpenAI-compatible and Anthropic-compatible usage.

**Architecture:** Treat `ai-translator` as a pure client. Do not change Lemonade model lifecycle or backend configuration in this phase unless a concrete mismatch requires it. Prefer live smoke tests, then document the confirmed working invocation pattern.

**Tech Stack:** Python 3.10+, `ai_translator.py`, local Lemonade 10.2.0, pytest, shell smoke tests.

---

## Current Context

- Phase 1 and Phase 2 are complete.
- `ai-translator` now supports `claude-cli` and `http` providers.
- Local Lemonade is running at `localhost:13305`.
- Loaded model: `user.gemma-4-26B-A4B-it-GGUF`.
- Local API key files exist:
  - `~/path/to/lemonade_api_key`
  - `~/path/to/lemonade_api_key`
- Previous direct network calls to Lemonade via raw `curl` were blocked in this environment, so verification may need to fall back to documentation plus factory/unit validation if the runtime blocks local HTTP requests again.

## Desired Outcome

After this phase:

- We know whether `ai-translator` can successfully hit local Lemonade from this session.
- If yes, we capture exact working commands.
- If no due to runtime/tool policy, we capture the exact limitation and leave the project in a documented, test-covered state.

## Files Likely to Change

- Modify if needed: `README.md`
- Modify if needed: `docs/multi-llm-provider-architecture.md`
- Modify if needed: `docs/plans/...` only for status notes
- Modify only if a real bug is proven: `ai_translator.py` and tests

---

### Task 1: Verify local Lemonade runtime prerequisites

**Objective:** Confirm the target service and model are actually available before blaming client code.

**Files:**
- No code changes expected

**Checks:**

```bash
lemonade --host localhost status
python - <<'PY'
from pathlib import Path
for p in [Path('~/path/to/lemonade_api_key').expanduser(), Path('~/path/to/lemonade_api_key').expanduser()]:
    print(f'{p}:', 'present' if p.exists() else 'missing')
PY
```

Expected:
- Lemonade reports running on port 13305
- `user.gemma-4-26B-A4B-it-GGUF` is loaded
- at least one API key file is present

---

### Task 2: Attempt OpenAI-compatible smoke test through ai-translator

**Objective:** Verify the exact CLI invocation pattern against the live Lemonade service.

**Files:**
- No code changes expected unless a real bug is found

**Command:**

```bash
export LEMONADE_API_KEY="$(cat ~/path/to/lemonade_api_key)"
python ai_translator.py \
  --provider http \
  --protocol openai \
  --base-url http://localhost:13305/v1 \
  --model user.gemma-4-26B-A4B-it-GGUF \
  --api-key "$LEMONADE_API_KEY" \
  --json \
  "電源板測試"
```

Expected:
- JSON output containing a translation result
- or a concrete transport/protocol error we can diagnose

If the environment blocks the request, stop retrying the same pattern and document the limitation.

---

### Task 3: Attempt Anthropic-compatible smoke test through ai-translator

**Objective:** Verify the alternate protocol path using the root base URL.

**Files:**
- No code changes expected unless a real bug is found

**Command:**

```bash
export LEMONADE_API_KEY="$(cat ~/path/to/lemonade_api_key)"
python ai_translator.py \
  --provider http \
  --protocol anthropic \
  --base-url http://localhost:13305 \
  --model user.gemma-4-26B-A4B-it-GGUF \
  --api-key "$LEMONADE_API_KEY" \
  --json \
  "電源板測試"
```

Expected:
- JSON output containing a translation result
- or a concrete transport/protocol error we can diagnose

If blocked by environment policy, do not keep retrying raw network calls.

---

### Task 4: If live verification fails for a project bug, fix it with TDD

**Objective:** Only modify code if the live smoke test reveals a real client-side mismatch.

**Files:**
- Modify as needed: `tests/test_http_provider.py`
- Modify as needed: `tests/test_cli_config.py`
- Modify as needed: `ai_translator.py`

**Step 1:** Reproduce with a failing test
**Step 2:** Run the test and confirm failure
**Step 3:** Implement the minimum fix
**Step 4:** Re-run targeted tests and full suite

---

### Task 5: Write down exact recommended commands

**Objective:** Leave the repository with clear, reality-checked instructions.

**Files:**
- Modify if needed: `README.md`
- Modify if needed: `docs/multi-llm-provider-architecture.md`

Add or refine:
- working OpenAI-compatible Lemonade command
- working Anthropic-compatible Lemonade command
- note about `localhost` vs `127.0.0.1`
- note about environment/tool policy if local HTTP is blocked in Hermes session

---

## Risks and Tradeoffs

- Local HTTP requests may be blocked by the execution environment even if Lemonade itself is healthy.
- Anthropic-compatible behavior may differ from OpenAI-compatible behavior because Lemonade and clients often have different assumptions about base URL shape and headers.
- We should avoid mutating Lemonade config or loaded model in this phase unless absolutely necessary.

## Verification Checklist

- [ ] Lemonade runtime confirmed healthy
- [ ] Loaded model confirmed
- [ ] API key file confirmed present
- [ ] OpenAI-compatible ai-translator command attempted
- [ ] Anthropic-compatible ai-translator command attempted
- [ ] Any client bug fixed under TDD
- [ ] Full test suite still passes
- [ ] Final recommended commands documented
