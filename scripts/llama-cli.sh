# llama-cli --help

args=(
  #
  -m third_party/GLM-OCR-GGUF/GLM-OCR-Q8_0.gguf
  -mm third_party/GLM-OCR-GGUF/mmproj-GLM-OCR-Q8_0.gguf
  #
  # -m third_party/GLM-OCR-GGUF-mradermacher/GLM-OCR.f16.gguf
  # -mm third_party/GLM-OCR-GGUF-mradermacher/GLM-OCR.mmproj-f16.gguf
  #
  # -m third_party/GLM-OCR-GGUF-mradermacher/GLM-OCR.Q8_0.gguf
  # -mm third_party/GLM-OCR-GGUF-mradermacher/GLM-OCR.mmproj-Q8_0.gguf
  #
  # -n 10000
  # --temp 0.0
  #
  -st
  #
  --prompt "Parse this document and convert it into standard markdown format."
  #
  --image png/demo/demo0001-1.png
  #
)
llama-cli "${args[@]}"
