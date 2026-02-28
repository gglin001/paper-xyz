# PNG to Markdown Prompt Template

Use this prompt for page-by-page conversion in Codex:

```text
Convert PNG files in `<png_dir>` to Markdown files in `<md_dir>`, processing each file one by one in sorted filename order.

Requirements:

- Add each image file to context and read it directly.
- Do not use any OCR method.
- Do not use extra local image processing.
- Keep output as close as possible to the original page content.
- Do not output extra commentary.
- Save each result as a same-name `.md` file.
- If a glyph or token is uncertain, keep a conservative transcription and do not invent missing content.
```

Demo filled example:

```text
Convert PNG files in `png/demo` to Markdown files in `md/demo`, processing each file one by one in sorted filename order.

Requirements:

- Add each image file to context and read it directly.
- Do not use any OCR method.
- Do not use extra local image processing.
- Keep output as close as possible to the original page content.
- Do not output extra commentary.
- Save each result as a same-name `.md` file.
- If a glyph or token is uncertain, keep a conservative transcription and do not invent missing content.
```
