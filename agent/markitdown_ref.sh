#!/usr/bin/env bash
set -euo pipefail

# markitdown reference script.
# Run with `pixi run bash agent/markitdown_ref.sh <mode> ...`
#
# Common examples:
#   pixi run bash agent/markitdown_ref.sh help
#   pixi run bash agent/markitdown_ref.sh single agent/demo.pdf md/demo.markitdown.md
#   pixi run bash agent/markitdown_ref.sh batch pdf md
#   pixi run bash agent/markitdown_ref.sh stdin agent/demo.pdf md/demo.stdin.md pdf application/pdf
#   pixi run bash agent/markitdown_ref.sh plugins agent/demo.pdf md/demo.plugins.md
#   DOCINTEL_ENDPOINT="https://<name>.cognitiveservices.azure.com/" \
#     pixi run bash agent/markitdown_ref.sh docintel agent/demo.pdf md/demo.docintel.md

MARKITDOWN_BIN="${MARKITDOWN_BIN:-markitdown}"

usage() {
  cat <<'EOF'
Usage:
  markitdown_ref.sh help
  markitdown_ref.sh single [input_pdf] [output_md]
  markitdown_ref.sh batch [input_dir] [output_dir]
  markitdown_ref.sh stdin [input_pdf] [output_md] [extension_hint] [mime_hint]
  markitdown_ref.sh plugins [input_file] [output_md]
  markitdown_ref.sh docintel [input_file] [output_md] [endpoint]
  markitdown_ref.sh list-plugins

Notes:
  - Run from repo root with `pixi run` so dependencies are on PATH.
  - `docintel` requires a valid endpoint and API key env vars.
EOF
}

ensure_parent_dir() {
  local target="$1"
  mkdir -p "$(dirname "$target")"
}

run_single() {
  local input="${1:-agent/demo.pdf}"
  local output="${2:-md/demo.markitdown.md}"
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
  local input="${1:-agent/demo.pdf}"
  local output="${2:-md/demo.stdin.md}"
  local ext_hint="${3:-pdf}"
  local mime_hint="${4:-application/pdf}"
  ensure_parent_dir "$output"

  # Useful when input comes from pipes and extension/mime metadata is missing.
  cat "$input" | "$MARKITDOWN_BIN" -x "$ext_hint" -m "$mime_hint" -o "$output"
  echo "[stdin] $input -> $output"
}

run_plugins() {
  local input="${1:-agent/demo.pdf}"
  local output="${2:-md/demo.plugins.md}"
  ensure_parent_dir "$output"
  "$MARKITDOWN_BIN" -p "$input" -o "$output"
  echo "[plugins] $input -> $output"
}

run_docintel() {
  local input="${1:-agent/demo.pdf}"
  local output="${2:-md/demo.docintel.md}"
  local endpoint="${3:-${DOCINTEL_ENDPOINT:-}}"
  ensure_parent_dir "$output"

  if [[ -z "${endpoint}" ]]; then
    echo "Missing endpoint. Pass arg3 or set DOCINTEL_ENDPOINT." >&2
    return 1
  fi

  # API key is typically read from env vars by markitdown's DI integration.
  "$MARKITDOWN_BIN" "$input" -d -e "$endpoint" -o "$output"
  echo "[docintel] $input -> $output"
}

mode="${1:-batch}"
case "$mode" in
  help|-h|--help)
    usage
    ;;
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
  docintel)
    run_docintel "${2:-}" "${3:-}" "${4:-}"
    ;;
  list-plugins)
    "$MARKITDOWN_BIN" --list-plugins
    ;;
  *)
    echo "Unknown mode: $mode" >&2
    usage
    exit 1
    ;;
esac
