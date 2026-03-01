- optional pre-step for large/complex PDFs, or debug/test workflows, split representative pages first:

```bash
pixi run -e default python agent/pdf_split_ref.py pdf/large.pdf --pages 10-20 -o debug_agent/large.p10-20.pdf
```

- run bash for `pdf -> png`

```bash
pixi run -e default python scripts/pdf_to_png.py agent/demo.pdf -o png/demo
```

- for codex prompt, `png -> ocr -> md`

TODO: use `scripts/llama-serve.sh`
