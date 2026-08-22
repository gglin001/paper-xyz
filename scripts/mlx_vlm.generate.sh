#!/usr/bin/env bash
set -euo pipefail

# pixi run -e mlx mlx_vlm.generate --help

args=(
  #
  # --model third_party/dots.mocr-8bit
  # --prompt "Parse this document and convert it into standard markdown format."
  #
  --model third_party/OvisOCR2-8bit
  --prompt "Extract all readable content from the image in natural human reading order and output the result as a single Markdown document. For charts or images, represent them using an HTML image tag: <' + 'img src="images/bbox_{left}_{top}_{right}_{bottom}.jpg" />, where left, top, right, bottom are bounding box coordinates scaled to [0, 1000). Format formulas as LaTeX. Format tables as HTML: <table>...</table>. Transcribe all other text as standard Markdown. Preserve the original text without translation or paraphrasing."
  #
  --max-tokens 10000
  --temperature 0.0
  #
  #
  --image agent/demo.png
  #
)
pixi run -e mlx mlx_vlm.generate "${args[@]}"
