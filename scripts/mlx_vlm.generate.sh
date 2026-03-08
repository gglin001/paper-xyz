#!/usr/bin/env bash
set -euo pipefail

# pixi run -e mlx mlx_vlm.generate --help

PIXI_BIN="${PIXI_BIN:-pixi}"
MLX_MODEL="${MLX_MODEL:-third_party/GLM-OCR-8bit}"
MLX_MAX_TOKENS="${MLX_MAX_TOKENS:-10000}"
MLX_TEMPERATURE="${MLX_TEMPERATURE:-0.0}"
MLX_PROMPT="${MLX_PROMPT:-Parse this document and convert it into standard markdown format.}"
MLX_IMAGE="${MLX_IMAGE:-png/demo/demo-0.png}"

if ! command -v "${PIXI_BIN}" >/dev/null 2>&1; then
  echo "error: ${PIXI_BIN} is required but not installed" >&2
  exit 127
fi

args=(
  --model "${MLX_MODEL}"
  --max-tokens "${MLX_MAX_TOKENS}"
  --temperature "${MLX_TEMPERATURE}"
  --prompt "${MLX_PROMPT}"
  --image "${MLX_IMAGE}"
)

"${PIXI_BIN}" run -e mlx mlx_vlm.generate "${args[@]}"
