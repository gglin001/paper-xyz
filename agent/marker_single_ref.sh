#!/usr/bin/env bash
set -euo pipefail

# marker_single reference script (from marker-pdf).
#
# This repo currently has a known environment caveat:
# - `marker_single` works.
# - `marker` and `marker_chunk_convert` may fail if optional runtime deps
#   like `psutil` / `setuptools(pkg_resources)` are missing.
#
# Examples:
#   pixi run -e marker bash agent/marker_single_ref.sh help
#   pixi run -e marker bash agent/marker_single_ref.sh standard agent/demo.pdf md
#   pixi run -e marker bash agent/marker_single_ref.sh fast agent/demo.pdf md
#   pixi run -e marker bash agent/marker_single_ref.sh page-range agent/demo.pdf md 0-2
#   pixi run -e marker bash agent/marker_single_ref.sh config agent/demo.pdf md agent/marker_config_fast.json
#   pixi run -e marker bash agent/marker_single_ref.sh debug agent/demo.pdf md debug_agent/marker_debug

MARKER_BIN="${MARKER_BIN:-marker_single}"
DEFAULT_INPUT="agent/demo.pdf"
DEFAULT_OUTPUT_DIR="md"

usage() {
  cat <<'EOF'
Usage:
  marker_single_ref.sh help
  marker_single_ref.sh standard [input_pdf] [output_dir]
  marker_single_ref.sh fast [input_pdf] [output_dir]
  marker_single_ref.sh page-range [input_pdf] [output_dir] [range]
  marker_single_ref.sh json [input_pdf] [output_dir]
  marker_single_ref.sh config [input_pdf] [output_dir] [config_json]
  marker_single_ref.sh debug [input_pdf] [output_dir] [debug_dir]

Notes:
  - Run with `pixi run -e marker`.
  - page range is 0-based, same as marker CLI (example: 0,2-4).
EOF
}

require_marker_single() {
  if ! command -v "$MARKER_BIN" >/dev/null 2>&1; then
    echo "marker_single command not found: $MARKER_BIN" >&2
    return 1
  fi
}

main() {
  local mode="${1:-standard}"
  local input="${2:-$DEFAULT_INPUT}"
  local output_dir="${3:-$DEFAULT_OUTPUT_DIR}"
  local -a args

  case "$mode" in
  help | -h | --help)
    usage
    return 0
    ;;
  esac

  require_marker_single
  case "$mode" in
  standard)
    args=(
      --output_dir "$output_dir"
      --output_format markdown
      --disable_tqdm
    )
    ;;
  fast)
    args=(
      --output_dir "$output_dir"
      --output_format markdown
      --disable_ocr
      --disable_image_extraction
      --disable_multiprocessing
      --disable_tqdm
    )
    ;;
  page-range)
    args=(
      --output_dir "$output_dir"
      --output_format markdown
      --page_range "${4:-0-1}"
      --disable_tqdm
    )
    ;;
  json)
    args=(
      --output_dir "$output_dir"
      --output_format json
      --disable_tqdm
    )
    ;;
  config)
    args=(
      --output_dir "$output_dir"
      --config_json "${4:-agent/marker_config_fast.json}"
    )
    ;;
  debug)
    local debug_dir="${4:-debug_agent/marker_debug}"
    mkdir -p "$debug_dir"
    args=(
      --output_dir "$output_dir"
      --output_format markdown
      --debug
      --debug_data_folder "$debug_dir"
      --debug_layout_images
      --debug_json
      --disable_tqdm
    )
    ;;
  *)
    echo "Unknown mode: $mode" >&2
    usage
    return 1
    ;;
  esac

  "$MARKER_BIN" "$input" "${args[@]}"
}

main "$@"
