# Agent Reference Scripts

This directory stores reusable reference scripts only, not production pipeline code.

## Usage

- Run scripts from repo root so relative paths (`pdf/`, `md/`, `debug_agent/`) resolve correctly.
- Read each script's own docstring and `--help` for exact usage.
- Demo files (`agent/demo.pdf`, `agent/demo.png`) are sample inputs for help text and examples only.

## Shared Workflow

Use `agent/pdf_split_ref.py` first when PDFs are large or complex, or when you need fast debug/test loops:

1. Split representative pages to `debug_agent/`.
2. Tune and test conversion parameters on the subset PDF.
3. Re-run the same settings on the full PDF in `pdf/`.

Example commands:

```bash
pixi run -e default python agent/pdf_split_ref.py pdf/large.pdf --pages 10-20 -o debug_agent/large.p10-20.pdf
pixi run -e markitdown markitdown debug_agent/large.p10-20.pdf -o md/large.p10-20.md
pixi run -e markitdown markitdown pdf/large.pdf -o md/large.md
```

## Reference Scripts

- `agent/markitdown_ref.py`: markitdown CLI wrapper (`single`, `batch`, `stdin`, `plugins`, `list-plugins`). Help: `pixi run -e markitdown python agent/markitdown_ref.py --help`.
- `agent/pymupdf4llm_ref.py`: preset-based markdown extraction and JSON/JSONL output. Help: `pixi run -e default python agent/pymupdf4llm_ref.py --help`.
- `agent/pymupdf_ref.py`: PyMuPDF `get_text` mode examples (`text`, `html`, `words`, `dict`, etc.). Help: `pixi run -e default python agent/pymupdf_ref.py --help`.
- `agent/pypdf_ref.py`: pypdf extraction examples (`plain`, `layout`, metadata export). Help: `pixi run -e default python agent/pypdf_ref.py --help`.
- `agent/marker_ref.py`: marker-pdf single-file conversion with built-in markdown profiles (`standard`, `fast`, `quality`) via Python API imports. Help: `pixi run -e marker python agent/marker_ref.py --help`.
- `agent/surya_ocr_ref.py`: surya OCR for image/PDF inputs with markdown export. Help: `pixi run -e marker python agent/surya_ocr_ref.py --help`.
- `agent/pdf_split_ref.py`: selected-page subset extraction helper. Usage workflow is documented in `Shared Workflow` above. Help: `pixi run -e default python agent/pdf_split_ref.py --help`.
