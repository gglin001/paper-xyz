#!/usr/bin/env python3
"""Convert each PDF page into PNG files via pdf2image.

Tip:
  For large or complex PDFs, or for debug/test iteration, split
  representative pages first with `agent/pdf_split_ref.py`, then run this
  script on the subset PDF while tuning conversion settings.

Examples:
  pixi run -e default python scripts/pdf_to_png.py agent/demo.pdf -o png/demo
  pixi run -e default python scripts/pdf_to_png.py agent/demo.pdf -o png/demo --dpi 300
"""

from __future__ import annotations

import argparse
from pathlib import Path

from pdf2image import convert_from_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert PDF pages to PNG.")
    parser.add_argument("input", help="Input PDF path.")
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
        help="Render DPI. Default: 100",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input = Path(args.input).expanduser().resolve()

    if not input.is_file():
        raise FileNotFoundError(f"PDF file not found: {input}")

    output_dir = (
        Path(args.output_dir).expanduser().resolve()
        if args.output_dir
        else input.parent / f"{input.stem}"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    png_paths = convert_from_path(
        str(input),
        dpi=args.dpi,
        fmt="png",
        output_folder=str(output_dir),
        output_file=input.stem,
        paths_only=True,
    )

    for png_path in png_paths:
        print(Path(png_path).resolve())


if __name__ == "__main__":
    main()
