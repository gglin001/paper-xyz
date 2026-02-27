# Agent Reference Scripts

This directory stores reusable reference scripts only, not production pipeline code.

## Covered PDF Backends

- `agent/markitdown_ref.sh`: markitdown CLI examples (`single`, `batch`, `stdin`, `plugins`, `list-plugins`).
- `agent/pymupdf4llm_ref.py`: preset-based markdown extraction with optional page selection and chunk JSONL output.
- `agent/pymupdf_ref.py`: PyMuPDF `get_text` mode examples (`text`, `html`, `words`, `dict`, etc.).
- `agent/pypdf_ref.py`: pypdf extraction examples (`plain` / `layout`, orientation filter, metadata export).
- `agent/marker_single_ref.sh`: marker-pdf single-file conversion examples with multiple runtime profiles.
- `agent/surya_ocr_ref.py`: surya OCR examples for image/PDF inputs, including markdown export from OCR JSON.

## Marker Config Samples

- `agent/marker_config_fast.json`: speed-first setup (disable OCR + images).
- `agent/marker_config_quality.json`: quality-first setup (higher DPI + layout tuning).

## Quick Commands

```bash
# markitdown (default: single demo input)
pixi run -e markitdown bash agent/markitdown_ref.sh
pixi run -e markitdown bash agent/markitdown_ref.sh stdin
pixi run -e markitdown bash agent/markitdown_ref.sh plugins

# pymupdf4llm (default preset)
pixi run -e default python agent/pymupdf4llm_ref.py
pixi run -e default python agent/pymupdf4llm_ref.py --preset page_chunks --output debug_agent/demo.chunks.jsonl

# pymupdf (default mode: text)
pixi run -e default python agent/pymupdf_ref.py
pixi run -e default python agent/pymupdf_ref.py --mode text --pages 1-2

# pypdf (default mode: layout)
pixi run -e default python agent/pypdf_ref.py
pixi run -e default python agent/pypdf_ref.py --mode layout --pages 1-3 --metadata-json

# marker_single (default mode: standard)
pixi run -e marker bash agent/marker_single_ref.sh
pixi run -e marker bash agent/marker_single_ref.sh fast
pixi run -e marker bash agent/marker_single_ref.sh config agent/demo.pdf md agent/marker_config_quality.json

# surya_ocr (default mode: ocr)
pixi run -e marker python agent/surya_ocr_ref.py
pixi run -e marker python agent/surya_ocr_ref.py page-range agent/demo.pdf debug_agent/surya_ocr 0
pixi run -e marker python agent/surya_ocr_ref.py to-md agent/demo.png md/demo.surya.md
```

## Notes

- Default demo run for each script uses `agent/demo.pdf` as input and writes results under `md/`.
- `marker_single_ref.sh` writes into an output folder, so default markdown path is `md/demo/demo.md`.
- `surya_ocr_ref.py` supports `TORCH_DEVICE=cpu` when macOS MPS acceleration is unstable.
- Run scripts from repo root so relative paths (`pdf/`, `md/`, `debug_agent/`) resolve correctly.
- For shell refs, use `pixi run -e <env> bash agent/<script>.sh help`; for Python refs, use `pixi run -e <env> python agent/<script>.py --help`.
- For large PDFs, test with page ranges first to tune params quickly.
