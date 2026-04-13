#!/usr/bin/env bash
set -euo pipefail

if [[ "${LLM_BOOTSTRAP_MODELS:-1}" == "1" ]]; then
  python models/download_model.py
fi

exec "$@"