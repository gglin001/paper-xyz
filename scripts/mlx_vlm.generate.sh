#!/usr/bin/env bash
set -euo pipefail

# pixi run -e mlx mlx_vlm.generate --help

args=(
  #
  --model third_party/dots.mocr-8bit
  #
  --max-tokens 10000
  --temperature 0.0
  #
  --prompt "Parse this document and convert it into standard markdown format."
  #
  --image agent/demo.png
  #
)
pixi run -e mlx mlx_vlm.generate "${args[@]}"
