#!/usr/bin/env python3
"""Reference extractor for PyMuPDF with multiple text modes.

Examples:
  pixi run -e default python agent/pymupdf_ref.py agent/demo.pdf --output md/demo.pymupdf.text.txt
  pixi run -e default python agent/pymupdf_ref.py agent/demo.pdf --output md/demo.pymupdf.text.txt --mode text
  pixi run -e default python agent/pymupdf_ref.py agent/demo.pdf --output md/demo.pymupdf.words.json --mode words --sort
  pixi run -e default python agent/pymupdf_ref.py agent/demo.pdf --output md/demo.pymupdf.clip.txt --mode text --clip 0,0,595,842
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import fitz

TEXT_MODES = {"text", "html", "xhtml", "xml"}
STRUCTURED_MODES = {"blocks", "words", "dict", "rawdict", "json", "rawjson"}
ALL_MODES = sorted(TEXT_MODES | STRUCTURED_MODES)


def parse_clip(raw: str | None) -> fitz.Rect | None:
    if not raw:
        return None
    values = [chunk.strip() for chunk in raw.split(",")]
    if len(values) != 4:
        raise ValueError("clip requires 4 comma-separated numbers: x0,y0,x1,y1")
    return fitz.Rect(*(float(value) for value in values))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract page text via PyMuPDF. Example input: agent/demo.pdf."
    )
    parser.add_argument("input_pdf", help="Input PDF path. Example: agent/demo.pdf.")
    parser.add_argument(
        "--output",
        "-o",
        required=True,
        help="Output file path.",
    )
    parser.add_argument(
        "--mode",
        choices=ALL_MODES,
        default="text",
        help="PyMuPDF get_text mode.",
    )
    parser.add_argument(
        "--sort",
        action="store_true",
        help="Sort blocks by reading order if mode supports it.",
    )
    parser.add_argument(
        "--clip",
        default=None,
        help="Clip box as x0,y0,x1,y1.",
    )
    parser.add_argument(
        "--flags",
        type=int,
        default=None,
        help="Optional PyMuPDF text extraction flags integer.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    input_pdf = Path(args.input_pdf)
    if not input_pdf.exists():
        raise SystemExit(f"Input PDF not found: {input_pdf}")

    clip = parse_clip(args.clip)
    doc = fitz.open(str(input_pdf))
    try:
        page_count = doc.page_count
        if page_count == 0:
            raise SystemExit("Input PDF has no pages.")

        extract_kwargs: dict[str, Any] = {}
        if args.sort:
            extract_kwargs["sort"] = True
        if clip is not None:
            extract_kwargs["clip"] = clip
        if args.flags is not None:
            extract_kwargs["flags"] = args.flags

        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)

        if args.mode in TEXT_MODES:
            chunks: list[str] = []
            for page_index in range(page_count):
                text = doc[page_index].get_text(args.mode, **extract_kwargs)
                chunks.append(f"<!-- page:{page_index + 1} -->\n\n{text}")
            output.write_text("\n\n".join(chunks).rstrip() + "\n", encoding="utf-8")
            summary = f"text chars={output.stat().st_size}"
        else:
            records: list[dict[str, Any]] = []
            for page_index in range(page_count):
                payload = doc[page_index].get_text(args.mode, **extract_kwargs)
                if args.mode in {"json", "rawjson"}:
                    payload = json.loads(payload)
                records.append({"page": page_index + 1, "content": payload})
            output.write_text(
                json.dumps(records, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            summary = f"records={len(records)}"

    finally:
        doc.close()

    print(f"[pymupdf] input={input_pdf} mode={args.mode} pages={page_count}")
    print(f"[pymupdf] kwargs={extract_kwargs}")
    print(f"[pymupdf] output={output} ({summary})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
