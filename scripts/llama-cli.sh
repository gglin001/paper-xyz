#!/usr/bin/env bash
set -euo pipefail

# pixi run -e llama llama-cli --help

args=(
  #
  -m third_party/Unlimited-OCR-GGUF/Unlimited-OCR-Q8_0.gguf
  -mm third_party/Unlimited-OCR-GGUF/mmproj-Unlimited-OCR-F16.gguf
  --prompt "document parsing."
  #
  # -m third_party/dots.mocr-gguf/dotsmocr-1.8b-q8_0.gguf
  # -mm third_party/dots.mocr-gguf/mmproj-dotsmocr-bf16.gguf
  # --prompt "Parse this document and convert it into standard markdown format."
  #
  # -m third_party/chandra-ocr-2-GGUF/chandra-ocr-2.Q8_0.gguf
  # -mm third_party/chandra-ocr-2-GGUF/chandra-ocr-2.mmproj-bf16.gguf
  # --prompt "Parse this document and convert it into standard markdown format."
  #
  # -n 10000
  # --temp 0.0
  #
  -st
  #
  --image agent/demo.png
  #
)
pixi run -e llama llama-cli "${args[@]}"
