#!/usr/bin/env python3
"""marker_single reference CLI script.

Examples:
  pixi run -e marker python agent/marker_single_ref.py standard --input agent/demo.pdf --output-dir md
  pixi run -e marker python agent/marker_single_ref.py fast --input agent/demo.pdf --output-dir md
  pixi run -e marker python agent/marker_single_ref.py json --input agent/demo.pdf --output-dir md
  pixi run -e marker python agent/marker_single_ref.py config --input agent/demo.pdf --output-dir md --config-json agent/marker_config_fast.json
  pixi run -e marker python agent/marker_single_ref.py debug --input agent/demo.pdf --output-dir md --debug-dir debug_agent/marker_debug
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

MARKER_BIN = os.environ.get("MARKER_BIN", "marker_single")


def require_marker_single() -> None:
    if shutil.which(MARKER_BIN):
        return
    raise FileNotFoundError(f"marker_single command not found: {MARKER_BIN}")


def build_marker_args(
    mode: str, output_dir: str, extra: str | None = None
) -> list[str]:
    if mode == "standard":
        return [
            "--output_dir",
            output_dir,
            "--output_format",
            "markdown",
            "--disable_tqdm",
        ]

    if mode == "fast":
        return [
            "--output_dir",
            output_dir,
            "--output_format",
            "markdown",
            "--disable_ocr",
            "--disable_image_extraction",
            "--disable_multiprocessing",
            "--disable_tqdm",
        ]

    if mode == "json":
        return [
            "--output_dir",
            output_dir,
            "--output_format",
            "json",
            "--disable_tqdm",
        ]

    if mode == "config":
        if not extra:
            raise ValueError("config mode requires --config-json")
        return [
            "--output_dir",
            output_dir,
            "--config_json",
            extra,
        ]

    if mode == "debug":
        if not extra:
            raise ValueError("debug mode requires --debug-dir")
        Path(extra).mkdir(parents=True, exist_ok=True)
        return [
            "--output_dir",
            output_dir,
            "--output_format",
            "markdown",
            "--debug",
            "--debug_data_folder",
            extra,
            "--debug_layout_images",
            "--debug_json",
            "--disable_tqdm",
        ]

    raise ValueError(f"Unknown mode: {mode}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reference CLI for marker_single. Example input: agent/demo.pdf.",
    )
    parser.add_argument(
        "mode",
        choices=["standard", "fast", "json", "config", "debug"],
        help="Run mode.",
    )
    parser.add_argument(
        "--input",
        dest="input_pdf",
        required=True,
        help="Input PDF path. Example: agent/demo.pdf.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Output directory.",
    )
    parser.add_argument(
        "--config-json",
        help="Config file path for config mode. Example: agent/marker_config_fast.json.",
    )
    parser.add_argument(
        "--debug-dir",
        help="Debug output directory for debug mode.",
    )
    return parser


def validate_args(args: argparse.Namespace) -> None:
    if args.mode == "config" and not args.config_json:
        raise ValueError("config mode requires --config-json")
    if args.mode == "debug" and not args.debug_dir:
        raise ValueError("debug mode requires --debug-dir")


def run_with_args(args: argparse.Namespace) -> int:
    extra: str | None = None
    if args.mode == "config":
        extra = args.config_json
    elif args.mode == "debug":
        extra = args.debug_dir

    marker_args = build_marker_args(args.mode, args.output_dir, extra)
    subprocess.run([MARKER_BIN, args.input_pdf, *marker_args], check=True)
    return 0


def main() -> int:
    args = build_parser().parse_args()
    try:
        require_marker_single()
        validate_args(args)
        return run_with_args(args)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 127
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as exc:
        return exc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
