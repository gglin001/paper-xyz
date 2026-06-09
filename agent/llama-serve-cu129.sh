#!/usr/bin/env bash
set -euo pipefail

# for cuda devices
# CUDA_VISIBLE_DEVICES = "0"
# CUDA_DEVICE_ORDER = "PCI_BUS_ID"

args=(
  #
  -m third_party/GLM-OCR-GGUF/GLM-OCR-Q8_0.gguf
  -mm third_party/GLM-OCR-GGUF/mmproj-GLM-OCR-Q8_0.gguf
  #
  --temp 0.0
  #
  --host 127.0.0.1
  --port 11235
  #
)

if pgrep -laf 'llama-server' >/dev/null 2>&1; then
  exit 0
fi

# pixi run -e cu129 llama-server "${args[@]}"
zellij a llama --create-background
zellij -s llama run -- pixi run -e cu129 llama-server "${args[@]}"

# use `zellij run` cause below not works with background sessions
# zellij -s llama action write-chars "CMD"
# zellij -s llama action write 13
# zellij a llama
