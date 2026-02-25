#!/usr/bin/env python

import pymupdf4llm
from pathlib import Path

pdf_path = Path("agent/demo.pdf")
out_path = Path("md/demo.md")
# TODO: default args may not good enough
md = pymupdf4llm.to_markdown(str(pdf_path))
out_path.write_text(md, encoding="utf-8")
print(f"{pdf_path} -> {out_path}  chars: {len(md)}")
