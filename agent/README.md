# Agent Reference Scripts

This directory stores reusable reference scripts only, not production pipeline code.

## Covered PDF Backends

- `agent/markitdown_ref.sh`: markitdown CLI examples (`single`, `batch`, `stdin`, `plugins`, `docintel`).
- `agent/pymupdf4llm_ref.py`: preset-based markdown extraction with optional page selection and chunk JSONL output.
- `agent/pymupdf_ref.py`: PyMuPDF `get_text` mode examples (`text`, `html`, `words`, `dict`, etc.).
- `agent/pypdf_ref.py`: pypdf extraction examples (`plain` / `layout`, orientation filter, metadata export).
- `agent/marker_single_ref.sh`: marker-pdf single-file conversion examples with multiple runtime profiles.

## Marker Config Samples

- `agent/marker_config_fast.json`: speed-first setup (disable OCR + images).
- `agent/marker_config_quality.json`: quality-first setup (higher DPI + layout tuning).

## Quick Commands

```bash
# markitdown
pixi run bash agent/markitdown_ref.sh batch pdf md

# pymupdf4llm
pixi run python agent/pymupdf4llm_ref.py --preset default
pixi run python agent/pymupdf4llm_ref.py --preset page_chunks --output debug_agent/demo.chunks.jsonl

# pymupdf
pixi run python agent/pymupdf_ref.py --mode text --pages 1-2

# pypdf
pixi run python agent/pypdf_ref.py --mode layout --pages 1-3 --metadata-json

# marker_single
pixi run bash agent/marker_single_ref.sh fast agent/demo.pdf md
pixi run bash agent/marker_single_ref.sh config agent/demo.pdf md agent/marker_config_quality.json
```

## Notes

- Run scripts from repo root so relative paths (`pdf/`, `md/`, `debug_agent/`) resolve correctly.
- For large PDFs, test with page ranges first to tune params quickly.
