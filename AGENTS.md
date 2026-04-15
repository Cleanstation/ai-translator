# AGENTS.md

## Project Overview

ai-translator is a tool for translating Chinese phrases into short English names.
It is designed for:
- code naming
- file naming
- test item naming
- other concise identifier-generation workflows

Supported providers:
- `claude-cli`
- `http`
  - OpenAI-compatible API
  - Anthropic-compatible API

## Repository Layout

```text
ai-translator/
├── ai_translator.py    # Main implementation (Translator, providers, parser, CLI)
├── tests/              # pytest test suite
├── docs/               # public-safe docs, templates, and integration guidance
├── scripts/            # small repository utility scripts
├── pyproject.toml      # package metadata and tool configuration
├── README.md           # user-facing usage guide
└── AGENTS.md           # public-safe project guidance for coding agents
```

## Important Components

### Translator

Main responsibilities:
- collect context
- build prompts
- orchestrate provider calls
- manage cache usage
- format translation results

### Providers

- `ClaudeCLIProvider`: shells out to `claude --print`
- `HTTPProvider`: supports OpenAI-compatible and Anthropic-compatible HTTP APIs

### Other important helpers

- `TranslationCache`: provider-aware cache with endpoint separation
- `parse_translation_response()`: extracts a JSON translation object from model output
- `build_arg_parser()`: CLI argument definitions
- `create_provider_from_args()`: builds provider instances from CLI/env config

## Development Notes

- Keep the public repository free of private infrastructure details.
- Do not hardcode real endpoints, API key paths, or host-specific values in tracked files.
- Prefer generic examples such as `localhost` and `YOUR_API_KEY` in public docs.
- Keep `Translator` decoupled from transport-specific logic when adding features.
- Prefer adding tests before modifying production behavior.

## Validation

Primary test command:

```bash
uv run --dev pytest tests/ -q
```

Basic syntax check:

```bash
python -m py_compile ai_translator.py
```
