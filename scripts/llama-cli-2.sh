#!/usr/bin/env bash
set -euo pipefail

# pixi run -e llama llama-cli --help

args=(
  #
  -m third_party/Qwen3.8-27B-GGUF/Qwen3.8-27B-UD-Q4_K_XL.gguf
  -mm third_party/Qwen3.8-27B-GGUF/mmproj-BF16.gguf
  #
  --temp 1.0
  --top-p 0.95
  --top-k 20
  --min-p 0.0
  #
)
pixi run -e llama llama-cli "${args[@]}"
