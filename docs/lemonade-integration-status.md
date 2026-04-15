# ai-translator × Lemonade Integration Status

## Summary

This document records the repository-side integration status for Lemonade after adding HTTP provider support.

Public-safe assumptions used here:
- Example host: `localhost:13305`
- Example API key file: `~/path/to/lemonade_api_key`
- Example model: `user.gemma-4-26B-A4B-it-GGUF`

## Repository-side verification

The repository has verified the following through unit tests and local static checks:

- `HTTPProvider` builds correct OpenAI-compatible requests
- `HTTPProvider` builds correct Anthropic-compatible requests
- CLI/env-based provider selection works
- endpoint-aware cache separation works
- HTTP error handling is covered
- parser and CLI failure paths are covered
- full test suite passes

## Recommended local verification commands

Run these in your own shell on the machine that can access Lemonade.
Adjust host/model/API key path as needed.

### 1. OpenAI-compatible verification

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

### 2. Anthropic-compatible verification

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

## Notes

- If your Lemonade server is not bound to localhost, replace `localhost` with your actual host or LAN address.
- For OpenAI-compatible mode, `--base-url` should include `/v1`.
- For Anthropic-compatible mode, `--base-url` should be the root URL, not `/v1`.
- The client sends both `Authorization: Bearer ...` and `x-api-key` on the Anthropic path to improve compatibility with different gateways.
