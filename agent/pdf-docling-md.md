- optional pre-step for large/complex PDFs, or debug/test workflows, split representative pages first:

```bash
pixi run -e default python agent/pdf_split_ref.py pdf/large.pdf --pages 10-20 -o debug_agent/large.p10-20.pdf
```

- run bash for `llama-serve` service

```bash
bash agent/llama-serve.sh
```

- run `agent/docling_rerf.py` for `pdf -> png`

```bash
pixi run -e default python agent/docling_rerf.py agent/demo.pdf -o md/demo.md
```
