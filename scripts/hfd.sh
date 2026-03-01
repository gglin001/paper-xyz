# https://hf-mirror.com/

# export HF_ENDPOINT=https://hf-mirror.com

pushd third_party

hfd.sh ggml-org/GLM-OCR-GGUF \
  --include "GLM-OCR-Q8_0.gguf" --include "mmproj-GLM-OCR-Q8_0.gguf"
# https://huggingface.co/ggml-org/GLM-OCR-GGUF
# llama-server -hf ggml-org/GLM-OCR-GGUF

hfd.sh mradermacher/GLM-OCR-GGUF \
  --include "GLM-OCR.f16.gguf" --include "GLM-OCR.mmproj-f16.gguf" \
  --include "GLM-OCR.Q8_0.gguf" --include "GLM-OCR.mmproj-Q8_0.gguf" \
  --local-dir GLM-OCR-GGUF-mradermacher
# https://huggingface.co/mradermacher/GLM-OCR-GGUF/tree/main

hfd.sh mradermacher/FireRed-OCR-GGUF \
  --include "FireRed-OCR.Q8_0.gguf" --include "FireRed-OCR.mmproj-Q8_0.gguf"
# https://huggingface.co/mradermacher/FireRed-OCR-GGUF/tree/main

hfd.sh mradermacher/LightOnOCR-2-1B-GGUF \
  --include "LightOnOCR-2-1B.Q8_0.gguf" --include "LightOnOCR-2-1B.mmproj-Q8_0.gguf" \
  --include "LightOnOCR-2-1B.f16.gguf" --include "LightOnOCR-2-1B.mmproj-f16.gguf"
# https://huggingface.co/mradermacher/LightOnOCR-2-1B-GGUF/tree/main

# -----

hfd.sh mlx-community/GLM-OCR-bf16
# https://huggingface.co/mlx-community/GLM-OCR-bf16
# python -m mlx_vlm.generate --model mlx-community/GLM-OCR-bf16 --max-tokens 100 --temperature 0.0 --prompt "Describe this image." --image <path_to_image>

hfd.sh mlx-community/GLM-OCR-8bit
# https://huggingface.co/mlx-community/GLM-OCR-8bit
# python -m mlx_vlm.generate --model mlx-community/GLM-OCR-8bit --max-tokens 100 --temperature 0.0 --prompt "Describe this image." --image <path_to_image>

hfd.sh mlx-community/DeepSeek-OCR-2-8bit
# https://huggingface.co/mlx-community/DeepSeek-OCR-2-8bit
# python -m mlx_vlm.generate --model mlx-community/DeepSeek-OCR-2-8bit --max-tokens 100 --temperature 0.0 --prompt "Describe this image." --image <path_to_image>

hfd.sh mlx-community/dots.ocr-bf16
# https://huggingface.co/mlx-community/dots.ocr-bf16
# python -m mlx_vlm.generate --model mlx-community/dots.ocr-bf16 --max-tokens 100 --temperature 0.0 --prompt "Describe this image." --image <path_to_image>

popd
