#!/usr/bin/env python3
"""Reference CLI for pymupdf4llm with multiple parameter presets.

Examples:
  pixi run -e default python agent/pymupdf4llm_ref.py agent/demo.pdf --output md/demo.pymupdf4llm.default.md
  pixi run -e default python agent/pymupdf4llm_ref.py agent/demo.pdf --output md/demo.pymupdf4llm.fast.md --preset fast_text
  pixi run -e default python agent/pymupdf4llm_ref.py agent/demo.pdf --output md/demo.pymupdf4llm.image.md --preset image_folder
  pixi run -e default python agent/pymupdf4llm_ref.py agent/demo.pdf --output debug_agent/demo.chunks.jsonl --preset page_chunks
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pymupdf4llm

HELP_EPILOG = "\n".join((__doc__ or "").strip().splitlines()[2:]).strip()

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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Convert PDF to markdown using pymupdf4llm presets. "
            "Example input: agent/demo.pdf."
        ),
        epilog=HELP_EPILOG or None,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "input",
        help="Input PDF path. Example: agent/demo.pdf.",
    )
    parser.add_argument(
        "--output",
        "-o",
        required=True,
        help="Output path.",
    )
    parser.add_argument(
        "--preset",
        choices=sorted(PRESETS.keys()),
        default="default",
        help="Preset parameter set.",
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
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.print_presets:
        print(json.dumps(PRESETS, indent=2, sort_keys=True))
        return 0

    input = Path(args.input)
    if not input.exists():
        raise SystemExit(f"Input PDF not found: {input}")

    kwargs: dict[str, Any] = dict(PRESETS[args.preset])
    if args.show_progress:
        kwargs["show_progress"] = True

    if args.preset == "image_folder":
        image_path = Path(kwargs["image_path"])
        image_path.mkdir(parents=True, exist_ok=True)

    output = Path(args.output)
    result = pymupdf4llm.to_markdown(str(input), **kwargs)
    summary = write_result(output, result)

    print(f"[pymupdf4llm] input={input} output={output} preset={args.preset}")
    print(f"[pymupdf4llm] kwargs={json.dumps(kwargs, sort_keys=True)}")
    print(f"[pymupdf4llm] wrote {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
