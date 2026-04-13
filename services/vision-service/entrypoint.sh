#!/usr/bin/env bash
set -euo pipefail

if [[ "${VISION_BOOTSTRAP_MODELS:-0}" == "1" ]]; then
  python models/download_models.py
fi

exec "$@"