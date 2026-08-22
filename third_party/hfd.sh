# https://hf-mirror.com/
wget https://hf-mirror.com/hfd/hfd.sh
chmod a+x hfd.sh
# cp hfd.sh ~/.local/bin/
cp hfd.sh .pixi/envs/default/bin/

export HF_ENDPOINT=https://hf-mirror.com

pushd third_party

hfd.sh sahilchachra/Unlimited-OCR-GGUF \
  --include "Unlimited-OCR-Q8_0.gguf" --include "mmproj-Unlimited-OCR-F16.gguf"
# https://huggingface.co/sahilchachra/Unlimited-OCR-GGUF

hfd.sh ggml-org/GLM-OCR-GGUF \
  --include "GLM-OCR-Q8_0.gguf" --include "mmproj-GLM-OCR-Q8_0.gguf"
# https://huggingface.co/ggml-org/GLM-OCR-GGUF
# llama-server -hf ggml-org/GLM-OCR-GGUF

hfd.sh lodrick-the-lafted/dots.mocr-gguf \
  --include "dotsmocr-1.8b-q8_0.gguf" --include "mmproj-dotsmocr-bf16.gguf"
# https://huggingface.co/lodrick-the-lafted/dots.mocr-gguf

hfd.sh prithivMLmods/chandra-ocr-2-GGUF \
  --include "chandra-ocr-2.Q8_0.gguf" --include "chandra-ocr-2.mmproj-bf16.gguf"
# https://huggingface.co/prithivMLmods/chandra-ocr-2-GGUF

hfd.sh Abiray/OvisOCR2-GGUF \
  --include "OvisOCR2-Q8_0.gguf" --include "mmproj-BF16.gguf" \
  --include "OvisOCR2-BF16.gguf"
# https://huggingface.co/Abiray/OvisOCR2-GGUF

hfd.sh prithivMLmods/HunyuanOCR-1.5-GGUF-Updated \
  --include "HunyuanOCR.Q8_0.gguf" --include "HunyuanOCR.mmproj-bf16.gguf"
# https://huggingface.co/prithivMLmods/HunyuanOCR-1.5-GGUF-Updated

# -----

hfd.sh mlx-community/dots.mocr-bf16
# https://huggingface.co/mlx-community/dots.mocr-bf16
# python -m mlx_vlm.generate --model mlx-community/dots.mocr-bf16 --max-tokens 100 --temperature 0.0 --prompt "Describe this image." --image <path_to_image>

hfd.sh mlx-community/dots.mocr-8bit
# https://huggingface.co/mlx-community/dots.mocr-8bit
# python -m mlx_vlm.generate --model mlx-community/dots.mocr-8bit --max-tokens 100 --temperature 0.0 --prompt "Describe this image." --image <path_to_image>

hfd.sh mlx-community/OvisOCR2-8bit
# https://huggingface.co/mlx-community/OvisOCR2-8bit

# -----

hfd.sh unsloth/Qwen3.8-27B-GGUF \
  --include "Qwen3.8-27B-UD-Q4_K_XL.gguf" --include "mmproj-BF16.gguf"
# https://huggingface.co/unsloth/Qwen3.8-27B-GGUF

popd
