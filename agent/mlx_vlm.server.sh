#!/usr/bin/env bash
set -euo pipefail

# pixi run -e mlx mlx_vlm.generate --help

args=(
  #
  --model third_party/dots.mocr-8bit
  #
  --trust-remote-code
  #
  --host 127.0.0.1
  --port 11235
  #
)
pixi run -e mlx mlx_vlm.server "${args[@]}"
