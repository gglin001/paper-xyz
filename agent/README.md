# Agent Reference Scripts

This directory stores reusable reference scripts only, not production pipeline code.

## Usage

- Run scripts from repo root so relative paths (`pdf/`, `md/`, `debug_agent/`) resolve correctly.
- Use the backend's own pixi environment. Local helpers such as `agent/pdf_split_ref.py` stay on `pixi run -e default`.
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

- `agent/olmocr_ref.py`: olmocr-style VLM API reference script that renders PDF pages locally and calls an OpenAI-compatible `chat/completions` endpoint page by page. Help: `pixi run -e default python agent/olmocr_ref.py --help`.
- `agent/olmocr_dots_mocr_ref.py`: olmocr-rendered PDF to Markdown + per-page SVG reference script using dots.mocr-style image-to-SVG prompting over an OpenAI-compatible API. Help: `pixi run -e default python agent/olmocr_dots_mocr_ref.py --help`.
- `agent/markitdown_ref.py`: markitdown CLI wrapper (`single`, `plugins`). Help: `pixi run -e markitdown python agent/markitdown_ref.py --help`. List plugins directly: `pixi run -e markitdown markitdown --list-plugins`.
- `agent/pdf_split_ref.py`: selected-page subset extraction helper. Usage workflow is documented in `Shared Workflow` above. Help: `pixi run -e default python agent/pdf_split_ref.py --help`.
