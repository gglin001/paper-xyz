---
name: pdf-png-md-direct-context
description: "Convert PDF files into page-level Markdown with a strict two-step workflow in this repository: render PDF pages to PNG with `agent/pdf_to_png_ref.py`, then transcribe each PNG directly in Codex image context without OCR or external converters. Use when tasks request reproducible PDF to PNG to MD conversion with faithful page mapping, including flows like `agent/pdf-png-md.md`."
---

# PDF PNG to Markdown, Direct Context

## Overview

Use this skill for conversion tasks that follow the same approach as `agent/pdf-png-md.md`. Keep the workflow reproducible, page aligned, and free of OCR tooling.

## Checklist

- Use only `agent/pdf_to_png_ref.py` for `pdf -> png`.
- Use Codex image context only for `png -> md`.
- Keep one input page mapped to one output Markdown file.
- Process files in deterministic filename order.
- Avoid OCR, extra converters, and extra image preprocessing.

## Workflow

### Step 1, Render `pdf -> png`

Run the repository script with `pixi`:

```bash
pixi run -e default python agent/pdf_to_png_ref.py <input_pdf> -od <output_png_dir>
```

Demo example:

```bash
pixi run -e default python agent/pdf_to_png_ref.py agent/demo.pdf -od png/demo
mkdir -p md/demo
```

Expected result:

- One PNG per PDF page.
- Stable filename stems for page mapping, for example `demo-0.png`.

### Step 2, Transcribe `png -> md` in Codex only

Use Codex image context directly for each PNG file. Do not use OCR libraries, OCR CLI tools, or extra conversion backends.

Load `references/png_to_md_prompt.md` and fill placeholders:

- `<png_dir>`
- `<md_dir>`

Process files one by one in sorted filename order, and write one Markdown file with the same basename.
Example mapping:

- `demo-0.png -> demo-0.md`
- `demo-1.png -> demo-1.md`

## Output Rules

- Preserve original content order and structure as closely as possible.
- Do not add explanations, summaries, or metadata outside converted content.
- Do not run extra local image preprocessing.
- Do not run alternate PDF to Markdown converters for this flow.
- Keep output limited to target conversion files.

## Validation

After conversion, verify counts first:

```bash
find <output_png_dir> -maxdepth 1 -name '*.png' | wc -l
find <output_md_dir> -maxdepth 1 -name '*.md' | wc -l
```

Then verify basename alignment:

```bash
comm -23 \
  <(find <output_png_dir> -maxdepth 1 -name '*.png' -exec basename {} .png \; | sort) \
  <(find <output_md_dir> -maxdepth 1 -name '*.md' -exec basename {} .md \; | sort)
```

If any basename is printed, create the missing Markdown file before delivery.
