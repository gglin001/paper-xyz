# pixi run -e mlx mlx_vlm.generate --help

args=(
  #
  --model third_party/dots.mocr-bf16
  #
)
pixi run -e mlx mlx_vlm.server "${args[@]}"
