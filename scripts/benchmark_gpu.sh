#!/usr/bin/env bash
set -euo pipefail

API_URL="${API_URL:-http://localhost:8000/api/v1}"
PROMPT_FILE="${PROMPT_FILE:-/tmp/llm_prompt.txt}"
IMAGE_FILE="${IMAGE_FILE:-}"

echo "Using API: $API_URL"

if [[ ! -f "$PROMPT_FILE" ]]; then
  cat > "$PROMPT_FILE" <<'EOF'
Summarize the engineering tradeoffs between CPU inference and GPU inference for small local language models.
EOF
fi

echo
echo "Submitting 3 LLM jobs..."
for i in 1 2 3; do
  curl -sS -X POST "$API_URL/jobs" \
    -F job_type=llm \
    -F task=summarize \
    -F max_tokens=128 \
    -F prompt="$(cat "$PROMPT_FILE")" | tee "/tmp/llm_job_$i.json"
  echo
done

if [[ -n "$IMAGE_FILE" && -f "$IMAGE_FILE" ]]; then
  echo
echo "Submitting 2 vision jobs..."
  for i in 1 2; do
    curl -sS -X POST "$API_URL/jobs" \
      -F job_type=vision \
      -F task=classify \
      -F file=@"$IMAGE_FILE" | tee "/tmp/vision_job_$i.json"
    echo
  done
fi

echo
echo "Recent jobs:"
curl -sS "$API_URL/jobs?limit=10"
echo
