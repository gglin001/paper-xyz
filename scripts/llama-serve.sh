# llama-server --help

args=(
  #
  -m third_party/GLM-OCR-GGUF/GLM-OCR-Q8_0.gguf
  -mm third_party/GLM-OCR-GGUF/mmproj-GLM-OCR-Q8_0.gguf
  #
  # -n 10000
  # --temp 0.0
  #
)
llama-server "${args[@]}"
