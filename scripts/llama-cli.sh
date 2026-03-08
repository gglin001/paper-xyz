#!/usr/bin/env bash
set -euo pipefail

# llama-cli --help

LLAMA_CLI_BIN="${LLAMA_CLI_BIN:-llama-cli}"
LLAMA_MODEL="${LLAMA_MODEL:-third_party/GLM-OCR-GGUF/GLM-OCR-Q8_0.gguf}"
LLAMA_MMPROJ="${LLAMA_MMPROJ:-third_party/GLM-OCR-GGUF/mmproj-GLM-OCR-Q8_0.gguf}"
LLAMA_PROMPT="${LLAMA_PROMPT:-Parse this document and convert it into standard markdown format.}"
LLAMA_IMAGE="${LLAMA_IMAGE:-png/demo/demo-0.png}"
LLAMA_STREAM="${LLAMA_STREAM:-1}"

if ! command -v "${LLAMA_CLI_BIN}" >/dev/null 2>&1; then
  echo "error: ${LLAMA_CLI_BIN} is required but not installed" >&2
  exit 127
fi

args=(
  -m "${LLAMA_MODEL}"
  -mm "${LLAMA_MMPROJ}"
)

if [[ -n "${LLAMA_MAX_TOKENS:-}" ]]; then
  args+=( -n "${LLAMA_MAX_TOKENS}" )
fi

if [[ -n "${LLAMA_TEMP:-}" ]]; then
  args+=( --temp "${LLAMA_TEMP}" )
fi

if [[ "${LLAMA_STREAM}" == "1" ]]; then
  args+=( -st )
fi

args+=(
  --prompt "${LLAMA_PROMPT}"
  --image "${LLAMA_IMAGE}"
)

"${LLAMA_CLI_BIN}" "${args[@]}"
