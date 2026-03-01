# pixi run -e mlx mlx_vlm.generate --help

args=(
  #
  # --model third_party/GLM-OCR-bf16
  --model third_party/GLM-OCR-8bit
  #
  # --max-tokens 10000
  # --temperature 0.0
  #
  --prompt "Parse this document and convert it into standard markdown format."
  #
  --image png/demo/demo0001-1.png
  #
)
pixi run -e mlx mlx_vlm.generate "${args[@]}"
