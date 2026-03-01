#!/usr/bin/env python3
"""markitdown reference CLI script.

Examples:
  pixi run -e markitdown python agent/markitdown_ref.py single --input agent/demo.pdf --output md/demo.markitdown.md
  pixi run -e markitdown python agent/markitdown_ref.py batch --input-dir pdf --output-dir md
  pixi run -e markitdown python agent/markitdown_ref.py stdin --input agent/demo.pdf --output md/demo.stdin.md
  pixi run -e markitdown python agent/markitdown_ref.py plugins --input agent/demo.pdf --output md/demo.plugins.md
  pixi run -e markitdown python agent/markitdown_ref.py list-plugins
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def ensure_parent_dir(target: str) -> None:
    Path(target).parent.mkdir(parents=True, exist_ok=True)


def run_cmd(*args: str, stdin=None) -> None:
    subprocess.run(["markitdown", *args], check=True, stdin=stdin)


def run_single(input_file: str, output_file: str) -> int:
    ensure_parent_dir(output_file)
    run_cmd(input_file, "-o", output_file)
    print(f"[single] {input_file} -> {output_file}")
    return 0


def run_batch(input_dir: str, output_dir: str) -> int:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    pdf_files = sorted(Path(input_dir).glob("*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in: {input_dir}", file=sys.stderr)
        return 1

    for pdf_file in pdf_files:
        out_file = output_path / f"{pdf_file.stem}.md"
        run_cmd(str(pdf_file), "-o", str(out_file))
        print(f"[batch] {pdf_file} -> {out_file}")
    return 0


def run_stdin(
    input_file: str,
    output_file: str,
    ext_hint: str,
    mime_hint: str,
) -> int:
    ensure_parent_dir(output_file)
    with open(input_file, "rb") as handle:
        run_cmd("-x", ext_hint, "-m", mime_hint, "-o", output_file, stdin=handle)
    print(f"[stdin] {input_file} -> {output_file}")
    return 0


def run_plugins(input_file: str, output_file: str) -> int:
    ensure_parent_dir(output_file)
    run_cmd("-p", input_file, "-o", output_file)
    print(f"[plugins] {input_file} -> {output_file}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reference CLI for markitdown. Example input: agent/demo.pdf.",
    )
    parser.add_argument(
        "mode",
        choices=["single", "batch", "stdin", "plugins", "list-plugins"],
        help="Run mode.",
    )
    parser.add_argument(
        "--input",
        dest="input_path",
        help="Input file path. Required for single, stdin, plugins. Example: agent/demo.pdf.",
    )
    parser.add_argument(
        "--output",
        dest="output_path",
        help="Output markdown path. Required for single, stdin, plugins.",
    )
    parser.add_argument(
        "--input-dir",
        help="Input directory containing PDFs. Required for batch.",
    )
    parser.add_argument(
        "--output-dir",
        help="Output directory. Required for batch.",
    )
    parser.add_argument(
        "--extension-hint",
        default="pdf",
        help="Extension hint for stdin mode, passed to markitdown -x.",
    )
    parser.add_argument(
        "--mime-hint",
        default="application/pdf",
        help="MIME hint for stdin mode, passed to markitdown -m.",
    )
    return parser


def validate_args(args: argparse.Namespace) -> None:
    if args.mode == "batch":
        if not args.input_dir or not args.output_dir:
            raise ValueError("batch mode requires --input-dir and --output-dir")
        return

    if args.mode in {"single", "stdin", "plugins"}:
        if not args.input_path or not args.output_path:
            raise ValueError(f"{args.mode} mode requires --input and --output")


def run_with_args(args: argparse.Namespace) -> int:
    if args.mode == "single":
        return run_single(args.input_path, args.output_path)
    if args.mode == "batch":
        return run_batch(args.input_dir, args.output_dir)
    if args.mode == "stdin":
        return run_stdin(
            args.input_path,
            args.output_path,
            args.extension_hint,
            args.mime_hint,
        )
    if args.mode == "plugins":
        return run_plugins(args.input_path, args.output_path)
    if args.mode == "list-plugins":
        run_cmd("--list-plugins")
        return 0
    raise ValueError(f"Unknown mode: {args.mode}")


def main() -> int:
    args = build_parser().parse_args()
    try:
        validate_args(args)
        return run_with_args(args)
    except FileNotFoundError:
        print(f"Command not found: {MARKITDOWN_BIN}", file=sys.stderr)
        return 127
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as exc:
        return exc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
