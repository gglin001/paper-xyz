#!/usr/bin/env python3
"""Convert each PDF page into PNG files via pdf2image.

Examples:
  pixi run -e default python scripts/pdf_to_png.py agent/demo.pdf
  pixi run -e default python scripts/pdf_to_png.py agent/demo.pdf --dpi 300
  pixi run -e default python scripts/pdf_to_png.py agent/demo.pdf -o png/demo
"""

from __future__ import annotations

import argparse
from pathlib import Path

from pdf2image import convert_from_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert PDF pages to PNG.")
    parser.add_argument("input_pdf", help="Input PDF path.")
    parser.add_argument(
        "-o",
        "--output-dir",
        default=None,
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
    pdf_path = Path(args.input_pdf).expanduser().resolve()

    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    output_dir = (
        Path(args.output_dir).expanduser().resolve()
        if args.output_dir
        else pdf_path.parent / f"{pdf_path.stem}"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    png_paths = convert_from_path(
        str(pdf_path),
        dpi=args.dpi,
        fmt="png",
        output_folder=str(output_dir),
        output_file=pdf_path.stem,
        paths_only=True,
    )

    for png_path in png_paths:
        print(Path(png_path).resolve())


if __name__ == "__main__":
    main()
