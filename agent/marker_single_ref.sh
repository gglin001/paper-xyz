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
#   pixi run bash agent/marker_single_ref.sh help
#   pixi run bash agent/marker_single_ref.sh standard agent/demo.pdf md
#   pixi run bash agent/marker_single_ref.sh fast agent/demo.pdf md
#   pixi run bash agent/marker_single_ref.sh page-range agent/demo.pdf md 0-2
#   pixi run bash agent/marker_single_ref.sh config agent/demo.pdf md agent/marker_config_fast.json
#   pixi run bash agent/marker_single_ref.sh debug agent/demo.pdf md debug_agent/marker_debug

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
  - Run with `pixi run`.
  - page range is 0-based, same as marker CLI (example: 0,2-4).
EOF
}

require_marker_single() {
  if ! command -v marker_single >/dev/null 2>&1; then
    echo "marker_single is not available in PATH." >&2
    return 1
  fi
}

run_standard() {
  local input="${1:-agent/demo.pdf}"
  local output_dir="${2:-md}"
  marker_single \
    "$input" \
    --output_dir "$output_dir" \
    --output_format markdown \
    --disable_tqdm
}

run_fast() {
  local input="${1:-agent/demo.pdf}"
  local output_dir="${2:-md}"
  marker_single \
    "$input" \
    --output_dir "$output_dir" \
    --output_format markdown \
    --disable_ocr \
    --disable_image_extraction \
    --disable_multiprocessing \
    --disable_tqdm
}

run_page_range() {
  local input="${1:-agent/demo.pdf}"
  local output_dir="${2:-md}"
  local page_range="${3:-0-1}"
  marker_single \
    "$input" \
    --output_dir "$output_dir" \
    --output_format markdown \
    --page_range "$page_range" \
    --disable_tqdm
}

run_json() {
  local input="${1:-agent/demo.pdf}"
  local output_dir="${2:-md}"
  marker_single \
    "$input" \
    --output_dir "$output_dir" \
    --output_format json \
    --disable_tqdm
}

run_config() {
  local input="${1:-agent/demo.pdf}"
  local output_dir="${2:-md}"
  local config_json="${3:-agent/marker_config_fast.json}"
  marker_single \
    "$input" \
    --output_dir "$output_dir" \
    --config_json "$config_json"
}

run_debug() {
  local input="${1:-agent/demo.pdf}"
  local output_dir="${2:-md}"
  local debug_dir="${3:-debug_agent/marker_debug}"
  mkdir -p "$debug_dir"
  marker_single \
    "$input" \
    --output_dir "$output_dir" \
    --output_format markdown \
    --debug \
    --debug_data_folder "$debug_dir" \
    --debug_layout_images \
    --debug_json \
    --disable_tqdm
}

main() {
  require_marker_single
  local mode="${1:-standard}"
  case "$mode" in
    help|-h|--help)
      usage
      ;;
    standard)
      run_standard "${2:-}" "${3:-}"
      ;;
    fast)
      run_fast "${2:-}" "${3:-}"
      ;;
    page-range)
      run_page_range "${2:-}" "${3:-}" "${4:-}"
      ;;
    json)
      run_json "${2:-}" "${3:-}"
      ;;
    config)
      run_config "${2:-}" "${3:-}" "${4:-}"
      ;;
    debug)
      run_debug "${2:-}" "${3:-}" "${4:-}"
      ;;
    *)
      echo "Unknown mode: $mode" >&2
      usage
      return 1
      ;;
  esac
}

main "$@"
