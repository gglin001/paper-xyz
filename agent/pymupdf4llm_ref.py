#!/usr/bin/env python3
"""Reference CLI for pymupdf4llm with multiple parameter presets.

Examples:
  pixi run python agent/pymupdf4llm_ref.py
  pixi run python agent/pymupdf4llm_ref.py --preset fast_text
  pixi run python agent/pymupdf4llm_ref.py --preset image_folder --pages 0-1
  pixi run python agent/pymupdf4llm_ref.py --preset page_chunks --output debug_agent/demo.chunks.jsonl
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pymupdf4llm


# Presets intentionally keep only a few high-signal parameters, so users can
# quickly compare quality and runtime tradeoffs.
PRESETS: dict[str, dict[str, Any]] = {
    "default": {},
    "fast_text": {
        "ignore_images": True,
        "ignore_graphics": True,
        "table_strategy": "lines_strict",
    },
    "image_folder": {
        "write_images": True,
        "image_path": "debug_agent/pymupdf4llm_images",
        "image_format": "png",
        "dpi": 200,
    },
    "embed_images": {
        "embed_images": True,
        "write_images": False,
    },
    "page_chunks": {
        "page_chunks": True,
        "extract_words": True,
    },
    "table_text_mode": {
        "table_strategy": "text",
        "fontsize_limit": 2,
    },
}


def parse_pages(raw: str | None) -> list[int] | None:
    """Parse 0-based pages from strings like '0,2-4,8'."""
    if not raw:
        return None

    pages: set[int] = set()
    for part in raw.split(","):
        item = part.strip()
        if not item:
            continue
        if "-" in item:
            start_text, end_text = item.split("-", 1)
            start = int(start_text)
            end = int(end_text)
            if start > end:
                start, end = end, start
            pages.update(range(start, end + 1))
        else:
            pages.add(int(item))

    return sorted(pages)


def default_output_path(input_pdf: Path, preset: str) -> Path:
    suffix = ".jsonl" if preset == "page_chunks" else ".md"
    return Path("md") / f"{input_pdf.stem}.pymupdf4llm.{preset}{suffix}"


def write_result(output: Path, result: Any) -> str:
    output.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(result, str):
        output.write_text(result, encoding="utf-8")
        return f"text:{len(result)} chars"

    if isinstance(result, list) and output.suffix == ".jsonl":
        with output.open("w", encoding="utf-8") as handle:
            for record in result:
                handle.write(json.dumps(record, ensure_ascii=False))
                handle.write("\n")
        return f"jsonl:{len(result)} rows"

    payload = json.dumps(result, ensure_ascii=False, indent=2)
    output.write_text(payload, encoding="utf-8")
    return f"json:{len(payload)} chars"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert PDF to markdown using pymupdf4llm presets."
    )
    parser.add_argument(
        "input_pdf",
        nargs="?",
        default="agent/demo.pdf",
        help="Input PDF path.",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output path. Defaults to md/<stem>.pymupdf4llm.<preset>.(md|jsonl).",
    )
    parser.add_argument(
        "--preset",
        choices=sorted(PRESETS.keys()),
        default="default",
        help="Preset parameter set.",
    )
    parser.add_argument(
        "--pages",
        default=None,
        help="0-based pages, e.g. '0,2-4'.",
    )
    parser.add_argument(
        "--show-progress",
        action="store_true",
        help="Enable pymupdf4llm progress output.",
    )
    parser.add_argument(
        "--print-presets",
        action="store_true",
        help="Print presets and exit.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.print_presets:
        print(json.dumps(PRESETS, indent=2, sort_keys=True))
        return 0

    input_pdf = Path(args.input_pdf)
    if not input_pdf.exists():
        raise SystemExit(f"Input PDF not found: {input_pdf}")

    kwargs: dict[str, Any] = dict(PRESETS[args.preset])
    pages = parse_pages(args.pages)
    if pages is not None:
        kwargs["pages"] = pages
    if args.show_progress:
        kwargs["show_progress"] = True

    if args.preset == "image_folder":
        image_path = Path(kwargs["image_path"])
        image_path.mkdir(parents=True, exist_ok=True)

    output = (
        Path(args.output)
        if args.output
        else default_output_path(input_pdf, args.preset)
    )
    result = pymupdf4llm.to_markdown(str(input_pdf), **kwargs)
    summary = write_result(output, result)

    print(f"[pymupdf4llm] input={input_pdf} output={output} preset={args.preset}")
    print(f"[pymupdf4llm] kwargs={json.dumps(kwargs, sort_keys=True)}")
    print(f"[pymupdf4llm] wrote {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
