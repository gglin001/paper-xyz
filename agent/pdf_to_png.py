#!/usr/bin/env python3
"""Convert each PDF page into PNG files via PyMuPDF.

Tip:
  For large or complex PDFs, or for debug/test iteration, split
  representative pages first with `agent/pdf_split_ref.py`, then run this
  script on the subset PDF while tuning conversion settings.

Examples:
  pixi run -e default python agent/pdf_to_png.py agent/demo.pdf -o png/demo
  pixi run -e default python agent/pdf_to_png.py agent/demo.pdf -o png/demo --dpi 300
"""

from __future__ import annotations

import argparse
from pathlib import Path

import fitz


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert PDF pages to PNG.")
    parser.add_argument("input", help="Input PDF path.")
    parser.add_argument(
        "-o",
        "--output-dir",
        required=True,
        help="Output directory. Default: <pdf_dir>/<pdf_stem>",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=200,
        help="Render DPI. Default: 200",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(args)
    input_path = Path(args.input).expanduser().resolve()

    if not input_path.is_file():
        raise FileNotFoundError(f"PDF file not found: {input_path}")
    if args.dpi <= 0:
        raise ValueError(f"--dpi must be > 0, got: {args.dpi}")

    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    with fitz.open(str(input_path)) as doc:
        for index, page in enumerate(doc):
            output_path = output_dir / f"{input_path.stem}-{index}.png"
            page.get_pixmap(dpi=args.dpi, alpha=False).save(str(output_path))


if __name__ == "__main__":
    main()
