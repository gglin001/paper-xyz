#!/usr/bin/env bash
set -euo pipefail

# llama-server --help

args=(
  #
  -m third_party/GLM-OCR-GGUF/GLM-OCR-Q8_0.gguf
  -mm third_party/GLM-OCR-GGUF/mmproj-GLM-OCR-Q8_0.gguf
  #
  #
  # -m third_party/GLM-OCR-GGUF-mradermacher/GLM-OCR.f16.gguf
  # -mm third_party/GLM-OCR-GGUF-mradermacher/GLM-OCR.mmproj-f16.gguf
  #
  --temp 0.0
  #
  --host 127.0.0.1
  --port 11235
  #
)
# llama-server "${args[@]}"
zellij a llama --create-background
zellij -s llama run -- llama-server "${args[@]}"

# use `zellij run` cause below not works with background sessions
# zellij -s llama action write-chars "CMD"
# zellij -s llama action write 13
# zellij a llama
