# pixi run -e mlx mlx_vlm.generate --help

args=(
  #
  --model third_party/dots.mocr-bf16
  #
  --trust-remote-code
  #
  --host 127.0.0.1
  --port 11235
  #
)
pixi run -e mlx mlx_vlm.server "${args[@]}"
