# Agent Reference Scripts

This directory stores reusable reference scripts only, not production pipeline code.

## Covered PDF Backends

- `agent/markitdown_ref.py`: markitdown CLI examples (`single`, `batch`, `stdin`, `plugins`, `list-plugins`).
- `agent/pymupdf4llm_ref.py`: preset-based markdown extraction and chunk JSONL output.
- `agent/pymupdf_ref.py`: PyMuPDF `get_text` mode examples (`text`, `html`, `words`, `dict`, etc.).
- `agent/pypdf_ref.py`: pypdf extraction examples (`plain` / `layout`, orientation filter, metadata export).
- `agent/marker_single_ref.py`: marker-pdf single-file conversion examples with multiple runtime profiles.
- `agent/surya_ocr_ref.py`: surya OCR examples for image/PDF inputs, including markdown export from OCR JSON.
- `agent/pdf_split_ref.py`: extract selected pages into one subset PDF and optionally one file per page.

## Marker Config Samples

- `agent/marker_config_fast.json`: speed-first setup (disable OCR + images).
- `agent/marker_config_quality.json`: quality-first setup (higher DPI + layout tuning).

## Quick Commands

```bash
# markitdown
pixi run -e markitdown python agent/markitdown_ref.py agent/demo.pdf --output md/demo.markitdown.md --mode single
pixi run -e markitdown python agent/markitdown_ref.py agent/demo.pdf --output md/demo.stdin.md --mode stdin
pixi run -e markitdown python agent/markitdown_ref.py agent/demo.pdf --output md/demo.plugins.md --mode plugins
pixi run -e markitdown python agent/markitdown_ref.py --mode list-plugins
pixi run -e markitdown python agent/markitdown_ref.py pdf --output-dir md --mode batch

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
pixi run -e marker python agent/marker_single_ref.py agent/demo.pdf --output-dir md --mode standard
pixi run -e marker python agent/marker_single_ref.py agent/demo.pdf --output-dir md --mode fast
pixi run -e marker python agent/marker_single_ref.py agent/demo.pdf --output-dir md --mode config --config-json agent/marker_config_quality.json
pixi run -e marker python agent/marker_single_ref.py agent/demo.pdf --output-dir md --mode debug --debug-dir debug_agent/marker_debug

# surya_ocr
pixi run -e marker python agent/surya_ocr_ref.py agent/demo.pdf --output md/demo.surya.pdf.md --debug-dir debug_agent/surya_ocr_pdf
pixi run -e marker python agent/surya_ocr_ref.py agent/demo.png --output md/demo.surya.png.md --debug-dir debug_agent/surya_ocr_png --save-images

# pdf_split
pixi run -e default python agent/pdf_split_ref.py agent/demo.pdf -o debug_agent/demo.p1-3.pdf --pages 1-3
pixi run -e default python agent/pdf_split_ref.py agent/demo.pdf --per-page-dir debug_agent/demo_pages --pages 1,3,5-6
pixi run -e default python agent/pdf_split_ref.py agent/demo.pdf -o debug_agent/demo.z0-2.pdf --pages 0-2 --zero-based

# debug large PDF conversion with a subset first
pixi run -e default python agent/pdf_split_ref.py pdf/large.pdf -o debug_agent/large.p5-12.pdf --pages 5-12
pixi run -e markitdown markitdown debug_agent/large.p5-12.pdf -o md/large.p5-12.markitdown.md
```

## Notes

- Use `agent/demo.pdf` and `agent/demo.png` as sample inputs in commands and `--help` text only.
- `marker_single_ref.py` writes into an output folder. For `agent/demo.pdf` with `output_dir=md`, markdown path is `md/demo/demo.md`.
- `surya_ocr_ref.py` supports `TORCH_DEVICE=cpu` when macOS MPS acceleration is unstable.
- Run scripts from repo root so relative paths (`pdf/`, `md/`, `debug_agent/`) resolve correctly.
- For shell refs, use `pixi run -e <env> bash agent/<script>.sh help`; for Python refs, use `pixi run -e <env> python agent/<script>.py --help`.
- For large PDFs, prefer `pdf_split_ref.py` first, then run conversion on the subset PDF for faster tuning.
