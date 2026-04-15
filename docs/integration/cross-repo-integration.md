# Cross-Repo Integration

## Goal

Downstream repositories should be able to use `ai-translator` without embedding:
- provider endpoints
- API key paths
- host-specific assumptions
- hardcoded private infrastructure details

## Recommended contract

A downstream repository should resolve `ai-translator` in this order:

```text
AI_TRANSLATOR_BIN -> ai-translator in PATH -> repo-local fallback
```

This keeps the dependency contract stable while allowing each machine to provide its own runtime configuration.

## Why this is the best default

### 1. Low coupling

Downstream repos do not need to know:
- which provider is used
- where the API key comes from
- whether the backend is local, remote, OpenAI-compatible, or Anthropic-compatible

### 2. Host portability

Different machines can expose different wrappers or environment files while downstream repos keep the same invocation logic.

### 3. Public-safe repositories

Public repos can document a clean interface without leaking internal infrastructure or operational details.

## Suggested implementation pattern

### Python example

```python
import os
import shlex
import shutil
from pathlib import Path


def resolve_ai_translator_bin() -> list[str]:
    explicit = os.environ.get("AI_TRANSLATOR_BIN")
    if explicit:
        return shlex.split(explicit)

    path_bin = shutil.which("ai-translator")
    if path_bin:
        return [path_bin]

    repo_local = Path(__file__).resolve().parent / "ai-translator" / "ai_translator.py"
    if repo_local.exists():
        return ["python", str(repo_local)]

    raise RuntimeError("ai-translator not found")
```

### Shell example

```bash
if [ -n "${AI_TRANSLATOR_BIN:-}" ]; then
  TRANSLATOR_BIN="$AI_TRANSLATOR_BIN"
elif command -v ai-translator >/dev/null 2>&1; then
  TRANSLATOR_BIN="ai-translator"
elif [ -f "./ai-translator/ai_translator.py" ]; then
  TRANSLATOR_BIN="python ./ai-translator/ai_translator.py"
else
  echo "ai-translator not found" >&2
  exit 1
fi
```

## Best practice with dotfiles

The cleanest real-world setup is:
- this public repo exposes the CLI contract
- a dotfiles repo installs a wrapper such as `ai-translator-lemonade`
- each machine keeps its own local env file with real host/key values
- downstream repos use `AI_TRANSLATOR_BIN` or PATH only

## Anti-patterns

Avoid these in downstream repos:
- hardcoded private endpoints
- hardcoded key file paths
- mandatory assumptions about one exact submodule path

## Result

This approach gives:
- reusable downstream integrations
- safer public documentation
- easier host-to-host portability
- lower provider migration cost
