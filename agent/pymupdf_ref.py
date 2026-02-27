#!/usr/bin/env python3
"""Reference extractor for PyMuPDF with multiple text modes.

Examples:
  pixi run -e default python agent/pymupdf_ref.py
  pixi run -e default python agent/pymupdf_ref.py --mode text --pages 1-2
  pixi run -e default python agent/pymupdf_ref.py --mode words --sort
  pixi run -e default python agent/pymupdf_ref.py --mode text --clip 0,0,595,842
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


def parse_page_spec(spec: str | None, total_pages: int) -> list[int]:
    if not spec:
        return list(range(total_pages))

    result: set[int] = set()
    for part in spec.split(","):
        item = part.strip()
        if not item:
            continue
        if "-" in item:
            start_text, end_text = item.split("-", 1)
            start = int(start_text)
            end = int(end_text)
            if start > end:
                start, end = end, start
            for page_num in range(start, end + 1):
                if 1 <= page_num <= total_pages:
                    result.add(page_num - 1)
        else:
            page_num = int(item)
            if 1 <= page_num <= total_pages:
                result.add(page_num - 1)
    return sorted(result)


def parse_clip(raw: str | None) -> fitz.Rect | None:
    if not raw:
        return None
    values = [chunk.strip() for chunk in raw.split(",")]
    if len(values) != 4:
        raise ValueError("clip requires 4 comma-separated numbers: x0,y0,x1,y1")
    return fitz.Rect(*(float(value) for value in values))


def default_output_path(input_pdf: Path, mode: str) -> Path:
    if mode in {"html", "xhtml", "xml"}:
        suffix = ".html"
    elif mode in STRUCTURED_MODES:
        suffix = ".json"
    else:
        suffix = ".txt"
    return Path("md") / f"{input_pdf.stem}.pymupdf.{mode}{suffix}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract page text via PyMuPDF.")
    parser.add_argument("input_pdf", nargs="?", default="agent/demo.pdf")
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output file path. Default: md/<stem>.pymupdf.<mode>.<ext>",
    )
    parser.add_argument(
        "--mode",
        choices=ALL_MODES,
        default="text",
        help="PyMuPDF get_text mode.",
    )
    parser.add_argument(
        "--pages",
        default=None,
        help="1-based pages. Example: 1,3-5",
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
        page_indexes = parse_page_spec(args.pages, doc.page_count)
        if not page_indexes:
            raise SystemExit("No pages selected after parsing --pages.")

        extract_kwargs: dict[str, Any] = {}
        if args.sort:
            extract_kwargs["sort"] = True
        if clip is not None:
            extract_kwargs["clip"] = clip
        if args.flags is not None:
            extract_kwargs["flags"] = args.flags

        output = (
            Path(args.output)
            if args.output
            else default_output_path(input_pdf, args.mode)
        )
        output.parent.mkdir(parents=True, exist_ok=True)

        if args.mode in TEXT_MODES:
            chunks: list[str] = []
            for page_index in page_indexes:
                text = doc[page_index].get_text(args.mode, **extract_kwargs)
                chunks.append(f"<!-- page:{page_index + 1} -->\n\n{text}")
            output.write_text("\n\n".join(chunks).rstrip() + "\n", encoding="utf-8")
            summary = f"text chars={output.stat().st_size}"
        else:
            records: list[dict[str, Any]] = []
            for page_index in page_indexes:
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

    print(f"[pymupdf] input={input_pdf} mode={args.mode} pages={len(page_indexes)}")
    print(f"[pymupdf] kwargs={extract_kwargs}")
    print(f"[pymupdf] output={output} ({summary})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
