#!/usr/bin/env bash
set -euo pipefail

GH_BIN="${GH_BIN:-gh}"

if ! command -v "$GH_BIN" >/dev/null 2>&1; then
  echo "Error: gh CLI not found: $GH_BIN" >&2
  exit 1
fi

REPO_ARG="${1:-}"
JSON_FIELDS="visibility,isPrivate,url"

if [ -n "$REPO_ARG" ]; then
  JSON_OUTPUT="$($GH_BIN repo view "$REPO_ARG" --json "$JSON_FIELDS")"
else
  JSON_OUTPUT="$($GH_BIN repo view --json "$JSON_FIELDS")"
fi

export JSON_OUTPUT
python - <<'PY'
import json
import os
import sys

raw = os.environ.get("JSON_OUTPUT", "")
if not raw:
    print("Error: empty response from gh", file=sys.stderr)
    raise SystemExit(1)

obj = json.loads(raw)
visibility = str(obj.get("visibility", "unknown")).lower()
is_private = obj.get("isPrivate")
url = obj.get("url", "")

print(f"visibility={visibility}")
print(f"is_private={str(bool(is_private)).lower()}")
if url:
    print(f"url={url}")
PY
