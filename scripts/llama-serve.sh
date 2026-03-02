# llama-server --help

args=(
  #
  -m third_party/GLM-OCR-GGUF/GLM-OCR-Q8_0.gguf
  -mm third_party/GLM-OCR-GGUF/mmproj-GLM-OCR-Q8_0.gguf
  #
  #
  # -m third_party/GLM-OCR-GGUF-mradermacher/GLM-OCR.f16.gguf
  # -mm third_party/GLM-OCR-GGUF-mradermacher/GLM-OCR.mmproj-f16.gguf
  #
  --temp 0.0
  #
  --host 127.0.0.1
  --port 11235
  #
)
llama-server "${args[@]}"
