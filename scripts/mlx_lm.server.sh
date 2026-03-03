#!/usr/bin/env bash
set -euo pipefail

# pixi run -e mlx mlx_lm.server --help

args=(
  #
  # --model third_party/GLM-OCR-8bit
  # --model third_party/DeepSeek-OCR-2-8bit
  --model third_party/dots.ocr-bf16
  #
  --temp 0.0
  --max-tokens 10000
  #
  --host 127.0.0.1
  --port 11235
  #
)
# TODO: not work
pixi run -e mlx mlx_lm.server "${args[@]}"

# if pgrep -f 'mlx_lm.server' >/dev/null 2>&1; then
#   exit 0
# fi

# zellij a mlx --create-background
# zellij -s mlx run -- pixi run -e mlx mlx_lm.server "${args[@]}"
