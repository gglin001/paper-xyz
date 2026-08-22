#!/usr/bin/env bash
set -euo pipefail

# pixi run -e llama llama-cli --help

args=(
  #
  # -m third_party/Unlimited-OCR-GGUF/Unlimited-OCR-Q8_0.gguf
  # -mm third_party/Unlimited-OCR-GGUF/mmproj-Unlimited-OCR-F16.gguf
  # --prompt "document parsing."
  #
  # -m third_party/dots.mocr-gguf/dotsmocr-1.8b-q8_0.gguf
  # -mm third_party/dots.mocr-gguf/mmproj-dotsmocr-bf16.gguf
  # --prompt "Parse this document and convert it into standard markdown format."
  #
  # -m third_party/chandra-ocr-2-GGUF/chandra-ocr-2.Q8_0.gguf
  # -mm third_party/chandra-ocr-2-GGUF/chandra-ocr-2.mmproj-bf16.gguf
  # --prompt "Parse this document and convert it into standard markdown format."
  #
  # -m third_party/HunyuanOCR-1.5-GGUF-Updated/HunyuanOCR.Q8_0.gguf
  # -mm third_party/HunyuanOCR-1.5-GGUF-Updated/HunyuanOCR.mmproj-bf16.gguf
  # --prompt "提取文档图片中正文的所有信息用markdown格式表示，其中页眉、页脚部分忽略，表格用html格式表达，文档中公式用latex格式表示，按照阅读顺序组织进行解析。"
  #
  # -m third_party/OvisOCR2-GGUF/OvisOCR2-Q8_0.gguf
  -m third_party/OvisOCR2-GGUF/OvisOCR2-BF16.gguf
  -mm third_party/OvisOCR2-GGUF/mmproj-BF16.gguf
  --prompt "Extract all readable content from the image in natural human reading order and output the result as a single Markdown document. For charts or images, represent them using an HTML image tag: <' + 'img src="images/bbox_{left}_{top}_{right}_{bottom}.jpg" />, where left, top, right, bottom are bounding box coordinates scaled to [0, 1000). Format formulas as LaTeX. Format tables as HTML: <table>...</table>. Transcribe all other text as standard Markdown. Preserve the original text without translation or paraphrasing."
  # -n 10000
  # --temp 0.0
  #
  -st
  #
  --image agent/demo.png
  #
)
pixi run -e llama llama-cli "${args[@]}"
