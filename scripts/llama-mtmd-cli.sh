#!/usr/bin/env bash
set -euo pipefail

# pixi run -e llama llama-cli --help

args=(
  #
  -m third_party/Unlimited-OCR-GGUF/Unlimited-OCR-Q8_0.gguf
  -mm third_party/Unlimited-OCR-GGUF/mmproj-Unlimited-OCR-F16.gguf
  #
  # -n 10000
  # --temp 0.0
  #
  -st
  #
  --prompt "<|grounding|>Convert the document to markdown."
  #
  --image agent/demo.png
  #
)
pixi run -e llama llama-cli "${args[@]}"
