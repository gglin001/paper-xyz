# pixi run -e mlx mlx_vlm.generate --help

args=(
  #
  --model third_party/dots.mocr-bf16
  #
  --max-tokens 10000
  --temperature 0.0
  #
  --prompt "Parse this document and convert it into standard markdown format."
  #
  --image raw/png/demo/demo-0.png
  #
)
pixi run -e mlx mlx_vlm.generate "${args[@]}"
