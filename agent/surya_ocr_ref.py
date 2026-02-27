#!/usr/bin/env python3
"""surya_ocr reference script.

Run with:
  pixi run -e marker python agent/surya_ocr_ref.py <mode> ...
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

DEFAULT_INPUT = Path("agent/demo.png")
DEFAULT_OUTPUT_DIR = Path("debug_agent/surya_ocr")
DEFAULT_OUTPUT_MD = Path("md/demo.surya.md")


def require_surya(bin_name: str) -> None:
    if shutil.which(bin_name) is None:
        raise SystemExit(f"surya_ocr command not found: {bin_name}")


def run_surya(
    *,
    surya_bin: str,
    input_path: Path,
    output_dir: Path,
    save_images: bool = False,
    page_range: str | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [surya_bin, str(input_path), "--output_dir", str(output_dir)]
    if save_images:
        cmd.append("--images")
    if page_range:
        cmd.extend(["--page_range", page_range])
    subprocess.run(cmd, check=True)


def find_results_json(input_path: Path, output_dir: Path) -> Path:
    expected = output_dir / input_path.stem / "results.json"
    if expected.is_file():
        return expected

    candidates = sorted(output_dir.rglob("results.json"))
    if not candidates:
        raise SystemExit(f"Cannot find results.json under: {output_dir}")
    return candidates[0]


def normalize_text(raw: str) -> str:
    text = raw.strip()
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def lines_for_page(page: dict[str, Any]) -> list[str]:
    lines: list[tuple[float, float, str]] = []
    for line in page.get("text_lines", []):
        text = normalize_text(str(line.get("text") or ""))
        if not text:
            continue

        bbox = line.get("bbox") or [0.0, 0.0]
        x = float(bbox[0]) if len(bbox) >= 1 else 0.0
        y = float(bbox[1]) if len(bbox) >= 2 else 0.0
        lines.append((y, x, text))

    lines.sort(key=lambda item: (item[0], item[1]))
    return [text for _, _, text in lines]


def write_markdown(results_path: Path, output_md: Path) -> None:
    data = json.loads(results_path.read_text(encoding="utf-8"))
    output_md.parent.mkdir(parents=True, exist_ok=True)

    with output_md.open("w", encoding="utf-8") as out:
        for doc_idx, (doc_name, pages) in enumerate(data.items()):
            if doc_idx:
                out.write("\n")
            out.write(f"# OCR Output: {doc_name}\n\n")

            for page in pages:
                page_no = page.get("page", "?")
                out.write(f"## Page {page_no}\n\n")
                for text in lines_for_page(page):
                    out.write(f"{text}\n")
                out.write("\n")

    print(f"[to-md] {results_path} -> {output_md}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reference helper for surya_ocr image/PDF OCR."
    )
    subparsers = parser.add_subparsers(dest="mode")

    ocr_parser = subparsers.add_parser("ocr", help="Run OCR.")
    ocr_parser.add_argument("input_path", nargs="?", default=str(DEFAULT_INPUT))
    ocr_parser.add_argument("output_dir", nargs="?", default=str(DEFAULT_OUTPUT_DIR))

    images_parser = subparsers.add_parser(
        "images", help="Run OCR and save bbox images."
    )
    images_parser.add_argument("input_path", nargs="?", default=str(DEFAULT_INPUT))
    images_parser.add_argument("output_dir", nargs="?", default=str(DEFAULT_OUTPUT_DIR))

    range_parser = subparsers.add_parser(
        "page-range", help="Run OCR for specific page range."
    )
    range_parser.add_argument("input_pdf", nargs="?", default="agent/demo.pdf")
    range_parser.add_argument("output_dir", nargs="?", default=str(DEFAULT_OUTPUT_DIR))
    range_parser.add_argument("range", nargs="?", default="0")

    to_md_parser = subparsers.add_parser(
        "to-md", help="Run OCR and convert results.json to markdown."
    )
    to_md_parser.add_argument("input_path", nargs="?", default=str(DEFAULT_INPUT))
    to_md_parser.add_argument("output_md", nargs="?", default=str(DEFAULT_OUTPUT_MD))
    to_md_parser.add_argument("output_dir", nargs="?", default=str(DEFAULT_OUTPUT_DIR))

    subparsers.add_parser("help", help="Show help.")
    return parser


def main() -> None:
    parser = build_parser()
    argv = sys.argv[1:] or ["ocr"]
    args = parser.parse_args(argv)
    mode = args.mode
    if mode in (None, "help"):
        parser.print_help()
        return

    surya_bin = os.environ.get("SURYA_BIN", "surya_ocr")
    require_surya(surya_bin)

    if mode == "ocr":
        input_path = Path(args.input_path)
        output_dir = Path(args.output_dir)
        run_surya(surya_bin=surya_bin, input_path=input_path, output_dir=output_dir)
        print(f"[ocr] {input_path} -> {output_dir}")
        return

    if mode == "images":
        input_path = Path(args.input_path)
        output_dir = Path(args.output_dir)
        run_surya(
            surya_bin=surya_bin,
            input_path=input_path,
            output_dir=output_dir,
            save_images=True,
        )
        print(f"[images] {input_path} -> {output_dir}")
        return

    if mode == "page-range":
        input_pdf = Path(args.input_pdf)
        output_dir = Path(args.output_dir)
        run_surya(
            surya_bin=surya_bin,
            input_path=input_pdf,
            output_dir=output_dir,
            page_range=args.range,
        )
        print(f"[page-range] {input_pdf} ({args.range}) -> {output_dir}")
        return

    if mode == "to-md":
        input_path = Path(args.input_path)
        output_md = Path(args.output_md)
        output_dir = Path(args.output_dir)
        run_surya(surya_bin=surya_bin, input_path=input_path, output_dir=output_dir)
        results_path = find_results_json(input_path, output_dir)
        write_markdown(results_path, output_md)
        return

    raise SystemExit(f"Unknown mode: {mode}")


if __name__ == "__main__":
    main()
