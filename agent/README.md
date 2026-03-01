# Agent Reference Scripts

This directory stores reusable reference scripts only, not production pipeline code.

## Covered PDF Backends

- `agent/markitdown_ref.py`: markitdown CLI examples (`single`, `batch`, `stdin`, `plugins`, `list-plugins`).
- `agent/pymupdf4llm_ref.py`: preset-based markdown extraction and chunk JSONL output.
- `agent/pymupdf_ref.py`: PyMuPDF `get_text` mode examples (`text`, `html`, `words`, `dict`, etc.).
- `agent/pypdf_ref.py`: pypdf extraction examples (`plain` / `layout`, orientation filter, metadata export).
- `agent/marker_single_ref.py`: marker-pdf single-file conversion examples with multiple runtime profiles.
- `agent/surya_ocr_ref.py`: surya OCR examples for image/PDF inputs, including markdown export from OCR JSON.

## Marker Config Samples

- `agent/marker_config_fast.json`: speed-first setup (disable OCR + images).
- `agent/marker_config_quality.json`: quality-first setup (higher DPI + layout tuning).

## Quick Commands

```bash
# markitdown
pixi run -e markitdown python agent/markitdown_ref.py single --input agent/demo.pdf --output md/demo.markitdown.md
pixi run -e markitdown python agent/markitdown_ref.py stdin --input agent/demo.pdf --output md/demo.stdin.md
pixi run -e markitdown python agent/markitdown_ref.py plugins --input agent/demo.pdf --output md/demo.plugins.md
pixi run -e markitdown python agent/markitdown_ref.py list-plugins
pixi run -e markitdown python agent/markitdown_ref.py batch --input-dir pdf --output-dir md

# pymupdf4llm
pixi run -e default python agent/pymupdf4llm_ref.py agent/demo.pdf --output md/demo.pymupdf4llm.default.md
pixi run -e default python agent/pymupdf4llm_ref.py agent/demo.pdf --output debug_agent/demo.chunks.jsonl --preset page_chunks

# pymupdf
pixi run -e default python agent/pymupdf_ref.py agent/demo.pdf --output md/demo.pymupdf.text.txt
pixi run -e default python agent/pymupdf_ref.py agent/demo.pdf --output md/demo.pymupdf.words.json --mode words --sort

# pypdf
pixi run -e default python agent/pypdf_ref.py agent/demo.pdf --output md/demo.pypdf.layout.txt
pixi run -e default python agent/pypdf_ref.py agent/demo.pdf --output md/demo.pypdf.layout.txt --mode layout --metadata-json md/demo.pypdf.layout.meta.json

# marker_single
pixi run -e marker python agent/marker_single_ref.py standard --input agent/demo.pdf --output-dir md
pixi run -e marker python agent/marker_single_ref.py fast --input agent/demo.pdf --output-dir md
pixi run -e marker python agent/marker_single_ref.py config --input agent/demo.pdf --output-dir md --config-json agent/marker_config_quality.json
pixi run -e marker python agent/marker_single_ref.py debug --input agent/demo.pdf --output-dir md --debug-dir debug_agent/marker_debug

# surya_ocr
pixi run -e marker python agent/surya_ocr_ref.py agent/demo.pdf --tmp-dir debug_agent/surya_ocr_pdf --output md/demo.surya.pdf.md
pixi run -e marker python agent/surya_ocr_ref.py agent/demo.png --tmp-dir debug_agent/surya_ocr_png --save-images --output md/demo.surya.png.md
```

## Notes

- Use `agent/demo.pdf` and `agent/demo.png` as sample inputs in commands and `--help` text only.
- `marker_single_ref.py` writes into an output folder. For `agent/demo.pdf` with `output_dir=md`, markdown path is `md/demo/demo.md`.
- `surya_ocr_ref.py` supports `TORCH_DEVICE=cpu` when macOS MPS acceleration is unstable.
- Run scripts from repo root so relative paths (`pdf/`, `md/`, `debug_agent/`) resolve correctly.
- For shell refs, use `pixi run -e <env> bash agent/<script>.sh help`; for Python refs, use `pixi run -e <env> python agent/<script>.py --help`.
- For large PDFs, test with smaller sample files first to tune params quickly.
