#!/usr/bin/env bash
set -euo pipefail

# markitdown reference script.
# Run with `pixi run -e markitdown bash agent/markitdown_ref.sh <mode> ...`
#
# Common examples:
#   pixi run -e markitdown bash agent/markitdown_ref.sh help
#   pixi run -e markitdown bash agent/markitdown_ref.sh single agent/demo.pdf md/demo.markitdown.md
#   pixi run -e markitdown bash agent/markitdown_ref.sh batch pdf md
#   pixi run -e markitdown bash agent/markitdown_ref.sh stdin agent/demo.pdf md/demo.stdin.md pdf application/pdf
#   pixi run -e markitdown bash agent/markitdown_ref.sh plugins agent/demo.pdf md/demo.plugins.md

MARKITDOWN_BIN="${MARKITDOWN_BIN:-markitdown}"
DEFAULT_INPUT="agent/demo.pdf"
DEFAULT_OUTPUT="md/demo.markitdown.md"

usage() {
  cat <<'EOF'
Usage:
  markitdown_ref.sh help
  markitdown_ref.sh single [input_pdf] [output_md]
  markitdown_ref.sh batch [input_dir] [output_dir]
  markitdown_ref.sh stdin [input_pdf] [output_md] [extension_hint] [mime_hint]
  markitdown_ref.sh plugins [input_file] [output_md]
  markitdown_ref.sh list-plugins

Notes:
  - Run from repo root with `pixi run -e markitdown` so dependencies are on PATH.
EOF
}

ensure_parent_dir() {
  local target="$1"
  mkdir -p "$(dirname "$target")"
}

run_single() {
  local input="${1:-$DEFAULT_INPUT}"
  local output="${2:-$DEFAULT_OUTPUT}"
  ensure_parent_dir "$output"
  "$MARKITDOWN_BIN" "$input" -o "$output"
  echo "[single] $input -> $output"
}

run_batch() {
  local input_dir="${1:-pdf}"
  local output_dir="${2:-md}"
  local pdf_file
  local count=0

  mkdir -p "$output_dir"
  shopt -s nullglob
  for pdf_file in "$input_dir"/*.pdf; do
    local stem
    stem="$(basename "$pdf_file" .pdf)"
    "$MARKITDOWN_BIN" "$pdf_file" -o "$output_dir/$stem.md"
    echo "[batch] $pdf_file -> $output_dir/$stem.md"
    count=$((count + 1))
  done
  shopt -u nullglob

  if [[ "$count" -eq 0 ]]; then
    echo "No PDF files found in: $input_dir" >&2
    return 1
  fi
}

run_stdin() {
  local input="${1:-$DEFAULT_INPUT}"
  local output="${2:-md/demo.stdin.md}"
  local ext_hint="${3:-pdf}"
  local mime_hint="${4:-application/pdf}"
  ensure_parent_dir "$output"

  # Useful when input comes from pipes and extension/mime metadata is missing.
  "$MARKITDOWN_BIN" -x "$ext_hint" -m "$mime_hint" -o "$output" <"$input"
  echo "[stdin] $input -> $output"
}

run_plugins() {
  local input="${1:-$DEFAULT_INPUT}"
  local output="${2:-md/demo.plugins.md}"
  ensure_parent_dir "$output"
  "$MARKITDOWN_BIN" -p "$input" -o "$output"
  echo "[plugins] $input -> $output"
}

main() {
  local mode="${1:-single}"
  case "$mode" in
  help | -h | --help)
    usage
    return 0
    ;;
  esac

  case "$mode" in
  single)
    run_single "${2:-}" "${3:-}"
    ;;
  batch)
    run_batch "${2:-}" "${3:-}"
    ;;
  stdin)
    run_stdin "${2:-}" "${3:-}" "${4:-}" "${5:-}"
    ;;
  plugins)
    run_plugins "${2:-}" "${3:-}"
    ;;
  list-plugins)
    "$MARKITDOWN_BIN" --list-plugins
    ;;
  *)
    echo "Unknown mode: $mode" >&2
    usage
    return 1
    ;;
  esac
}

main "$@"
