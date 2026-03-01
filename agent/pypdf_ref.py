#!/usr/bin/env python3
"""Reference extractor for pypdf with multiple configuration examples.

Examples:
  pixi run -e default python agent/pypdf_ref.py agent/demo.pdf --output md/demo.pypdf.layout.txt
  pixi run -e default python agent/pypdf_ref.py agent/demo.pdf --output md/demo.pypdf.plain.txt --mode plain
  pixi run -e default python agent/pypdf_ref.py agent/demo.pdf --output md/demo.pypdf.layout.txt --mode layout --space-width 120
  pixi run -e default python agent/pypdf_ref.py agent/demo.pdf --output md/demo.pypdf.layout.txt --show-metadata --metadata-json md/demo.pypdf.layout.meta.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pypdf import PdfReader


def parse_orientations(raw: str) -> tuple[int, ...]:
    values = [chunk.strip() for chunk in raw.split(",") if chunk.strip()]
    if not values:
        return (0, 90, 180, 270)
    return tuple(int(value) for value in values)


def normalize_lines(text: str) -> str:
    lines = [line.rstrip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def extract_pages(
    reader: PdfReader,
    *,
    mode: str,
    orientations: tuple[int, ...],
    space_width: float,
    strip_empty_lines: bool,
) -> str:
    chunks: list[str] = []
    for page_index, page in enumerate(reader.pages):
        page_text = page.extract_text(
            extraction_mode=mode,
            orientations=orientations,
            space_width=space_width,
        )
        text = page_text or ""
        if strip_empty_lines:
            text = normalize_lines(text)
        chunks.append(f"<!-- page:{page_index + 1} -->\n\n{text}")
    return "\n\n".join(chunks).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract text with pypdf. Example input: agent/demo.pdf."
    )
    parser.add_argument("input_pdf", help="Input PDF path. Example: agent/demo.pdf.")
    parser.add_argument(
        "--output",
        "-o",
        required=True,
        help="Output text path.",
    )
    parser.add_argument(
        "--mode",
        choices=["plain", "layout"],
        default="layout",
        help="pypdf extraction mode.",
    )
    parser.add_argument(
        "--orientations",
        default="0,90,180,270",
        help="Comma separated allowed text orientations.",
    )
    parser.add_argument(
        "--space-width",
        type=float,
        default=200.0,
        help="pypdf spacing heuristic.",
    )
    parser.add_argument(
        "--strip-empty-lines",
        action="store_true",
        help="Drop empty lines in output.",
    )
    parser.add_argument(
        "--password",
        default=None,
        help="Password for encrypted PDFs.",
    )
    parser.add_argument(
        "--show-metadata",
        action="store_true",
        help="Print metadata to stdout.",
    )
    parser.add_argument(
        "--metadata-json",
        default=None,
        help="Write metadata JSON to this path.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    input_pdf = Path(args.input_pdf)
    if not input_pdf.exists():
        raise SystemExit(f"Input PDF not found: {input_pdf}")

    reader = PdfReader(str(input_pdf))
    if reader.is_encrypted:
        if not args.password:
            raise SystemExit("PDF is encrypted. Provide --password.")
        decrypt_status = reader.decrypt(args.password)
        if decrypt_status == 0:
            raise SystemExit("Incorrect password for encrypted PDF.")

    total_pages = len(reader.pages)
    if total_pages == 0:
        raise SystemExit("Input PDF has no pages.")

    orientations = parse_orientations(args.orientations)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    content = extract_pages(
        reader,
        mode=args.mode,
        orientations=orientations,
        space_width=args.space_width,
        strip_empty_lines=args.strip_empty_lines,
    )
    output.write_text(content, encoding="utf-8")

    metadata = {key: str(value) for key, value in (reader.metadata or {}).items()}
    if args.show_metadata:
        print(json.dumps(metadata, indent=2, sort_keys=True))

    if args.metadata_json is not None:
        metadata_path = Path(args.metadata_json)
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.write_text(
            json.dumps(metadata, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        print(f"[pypdf] metadata -> {metadata_path}")

    print(
        f"[pypdf] input={input_pdf} pages={total_pages} mode={args.mode} output={output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
