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
import logging
from pathlib import Path
from typing import Literal

from pypdf import PdfReader

HELP_EPILOG = "\n".join((__doc__ or "").strip().splitlines()[2:]).strip()
LOG_FORMAT = "%(asctime)s\t%(levelname)s\t%(name)s: %(message)s"


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
    mode: Literal["plain", "layout"],
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract text with pypdf. Example input: agent/demo.pdf.",
        epilog=HELP_EPILOG or None,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input", help="Input PDF path. Example: agent/demo.pdf.")
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
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="Set the verbosity level. -v for info logging, -vv for debug logging.",
    )
    return parser.parse_args()


def configure_logging(verbose: int) -> None:
    if verbose <= 1:
        logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    else:
        logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)


def main() -> int:
    args = parse_args()
    configure_logging(args.verbose)
    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"Input PDF not found: {input_path}")

    reader = PdfReader(str(input_path))
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
        logging.info("%s", json.dumps(metadata, indent=2, sort_keys=True))

    if args.metadata_json is not None:
        metadata_path = Path(args.metadata_json)
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.write_text(
            json.dumps(metadata, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        logging.info("[pypdf] metadata -> %s", metadata_path)

    logging.info(
        "[pypdf] input=%s pages=%s mode=%s output=%s",
        input_path,
        total_pages,
        args.mode,
        output,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
