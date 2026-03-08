#!/usr/bin/env bash
set -euo pipefail

# pixi run -e mlx mlx_lm.server --help

PIXI_BIN="${PIXI_BIN:-pixi}"
MLX_LM_MODEL="${MLX_LM_MODEL:-third_party/dots.ocr-bf16}"
MLX_LM_TEMP="${MLX_LM_TEMP:-0.0}"
MLX_LM_MAX_TOKENS="${MLX_LM_MAX_TOKENS:-10000}"
MLX_LM_HOST="${MLX_LM_HOST:-127.0.0.1}"
MLX_LM_PORT="${MLX_LM_PORT:-11235}"

if ! command -v "${PIXI_BIN}" >/dev/null 2>&1; then
  echo "error: ${PIXI_BIN} is required but not installed" >&2
  exit 127
fi

if [[ ! -e "${MLX_LM_MODEL}" ]]; then
  echo "error: model path not found: ${MLX_LM_MODEL}" >&2
  echo "hint: set MLX_LM_MODEL to an existing local model directory, then rerun" >&2
  exit 2
fi

if ! "${PIXI_BIN}" run -e mlx mlx_lm.server --help >/dev/null 2>&1; then
  echo "error: failed preflight check for mlx_lm.server in pixi environment 'mlx'" >&2
  echo "hint: run 'pixi install', then verify 'pixi run -e mlx mlx_lm.server --help'" >&2
  exit 2
fi

args=(
  --model "${MLX_LM_MODEL}"
  --temp "${MLX_LM_TEMP}"
  --max-tokens "${MLX_LM_MAX_TOKENS}"
  --host "${MLX_LM_HOST}"
  --port "${MLX_LM_PORT}"
)
"${PIXI_BIN}" run -e mlx mlx_lm.server "${args[@]}"
