#!/usr/bin/env bash
set -euo pipefail

if ! command -v curl >/dev/null 2>&1; then
  echo "error: curl is required but not installed" >&2
  exit 127
fi

API_BASE="${API_BASE:-http://127.0.0.1:11235}"
REQUEST_TIMEOUT_SECONDS="${REQUEST_TIMEOUT_SECONDS:-10}"

curl_args=(
  --fail
  --show-error
  --silent
  --connect-timeout "${REQUEST_TIMEOUT_SECONDS}"
  --max-time "${REQUEST_TIMEOUT_SECONDS}"
)

curl "${curl_args[@]}" "${API_BASE}/v1/models"
curl "${curl_args[@]}" \
  "${API_BASE}/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "hi"}]
  }'
