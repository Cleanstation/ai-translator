#!/usr/bin/env bash
set -euo pipefail

CONFIG_DIR="$HOME/.config/ai-translator"
LOCAL_ENV="$CONFIG_DIR/local.env"

if [ -r "$LOCAL_ENV" ]; then
  # shellcheck disable=SC1090
  . "$LOCAL_ENV"
fi
