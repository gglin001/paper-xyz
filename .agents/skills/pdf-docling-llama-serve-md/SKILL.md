---
name: pdf-docling-llama-serve-md
description: "Convert PDF files to Markdown with docling VLM API and local llama-server in this repository. Follows `agent/pdf-docling-md.md` and supports the demo flow `agent/demo.pdf -> md/demo.md`."
---

# PDF to Markdown with docling and llama-server

## Overview

Use this skill when a task asks for reproducible PDF to Markdown conversion via docling backed by local `llama-server`.

## Prerequisites

- Run commands from repository root.

## Checklist

- Keep conversion inputs in `pdf/` or `debug_agent/`.
- Write final Markdown outputs to `md/`.
- Start `llama-server` before running docling conversion.
- Use `agent/docling_rerf.py` as the conversion entry point from the dedicated `docling` pixi environment.

## Workflow

### Step 0, Optional subset split for large or complex PDFs

Use this step for faster debug loops before full conversion:

```bash
pixi run -e default python agent/pdf_split_ref.py pdf/large.pdf --pages 10-20 -o debug_agent/large.p10-20.pdf
```

### Step 1, Start local llama-server

```bash
bash agent/llama-serve.sh
```

Optional readiness check in another terminal:

```bash
curl -sS http://127.0.0.1:11235/v1/models | head
```

### Step 2, Convert PDF to Markdown with docling

Generic command:

```bash
pixi run -e docling python agent/docling_rerf.py <input_pdf> -o <output_md>
```

Demo command required by this flow:

```bash
pixi run -e docling python agent/docling_rerf.py agent/demo.pdf -o md/demo.md
```

## Validation

Check the output file exists and is not empty:

```bash
test -s md/demo.md && echo "ok: md/demo.md created"
```

Inspect the first lines:

```bash
sed -n '1,40p' md/demo.md
```

## Troubleshooting

- Slow or unstable conversion on large files: split representative pages with `agent/pdf_split_ref.py`, tune flags such as `--concurrency`, then rerun on the full PDF.
