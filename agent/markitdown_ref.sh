#!/usr/bin/env bash
set -euo pipefail

# help
markitdown --help

# demo
markitdown agent/demo.pdf -o md/demo.md

# batch cvt
pdf_files=(pdf/*.pdf)
for pdf_file in "${pdf_files[@]}"; do
  file_name="$(basename "$pdf_file" .pdf)"
  markitdown "$pdf_file" -o "md/${file_name}.md"
done
