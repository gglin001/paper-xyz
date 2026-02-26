# Agent Reference Scripts

This directory stores reusable reference scripts only, not production pipeline code.

## Covered PDF Backends

- `agent/markitdown_ref.sh`: markitdown CLI examples (`single`, `batch`, `stdin`, `plugins`, `list-plugins`).
- `agent/pymupdf4llm_ref.py`: preset-based markdown extraction with optional page selection and chunk JSONL output.
- `agent/pymupdf_ref.py`: PyMuPDF `get_text` mode examples (`text`, `html`, `words`, `dict`, etc.).
- `agent/pypdf_ref.py`: pypdf extraction examples (`plain` / `layout`, orientation filter, metadata export).
- `agent/marker_single_ref.sh`: marker-pdf single-file conversion examples with multiple runtime profiles.

## Marker Config Samples

- `agent/marker_config_fast.json`: speed-first setup (disable OCR + images).
- `agent/marker_config_quality.json`: quality-first setup (higher DPI + layout tuning).

## Quick Commands

```bash
# markitdown (default: single demo input)
pixi run bash agent/markitdown_ref.sh
pixi run bash agent/markitdown_ref.sh stdin
pixi run bash agent/markitdown_ref.sh plugins

# pymupdf4llm (default preset)
pixi run python agent/pymupdf4llm_ref.py
pixi run python agent/pymupdf4llm_ref.py --preset page_chunks --output debug_agent/demo.chunks.jsonl

# pymupdf (default mode: text)
pixi run python agent/pymupdf_ref.py
pixi run python agent/pymupdf_ref.py --mode text --pages 1-2

# pypdf (default mode: layout)
pixi run python agent/pypdf_ref.py
pixi run python agent/pypdf_ref.py --mode layout --pages 1-3 --metadata-json

# marker_single (default mode: standard)
pixi run bash agent/marker_single_ref.sh
pixi run bash agent/marker_single_ref.sh fast
pixi run bash agent/marker_single_ref.sh config agent/demo.pdf md agent/marker_config_quality.json
```

## Notes

- Default demo run for each script uses `agent/demo.pdf` as input and writes results under `md/`.
- `marker_single_ref.sh` writes into an output folder, so default markdown path is `md/demo/demo.md`.
- Run scripts from repo root so relative paths (`pdf/`, `md/`, `debug_agent/`) resolve correctly.
- Run `pixi run bash agent/<script>.sh help` to inspect mode arguments quickly.
- For large PDFs, test with page ranges first to tune params quickly.
