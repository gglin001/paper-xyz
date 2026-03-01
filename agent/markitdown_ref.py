#!/usr/bin/env python3
"""markitdown reference CLI script.

Examples:
  pixi run -e markitdown python agent/markitdown_ref.py agent/demo.pdf --output md/demo.markitdown.md
  pixi run -e markitdown python agent/markitdown_ref.py agent/demo.pdf --output md/demo.plugins.md --mode plugins
  pixi run -e markitdown markitdown --list-plugins
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HELP_EPILOG = "\n".join((__doc__ or "").strip().splitlines()[2:]).strip()


def ensure_parent_dir(target: str) -> None:
    Path(target).parent.mkdir(parents=True, exist_ok=True)


def run_cmd(*args: str, stdin=None) -> None:
    subprocess.run(["markitdown", *args], check=True, stdin=stdin)


def run_single(input_file: str, output_file: str) -> int:
    ensure_parent_dir(output_file)
    run_cmd(input_file, "-o", output_file)
    print(f"[single] {input_file} -> {output_file}")
    return 0


def run_plugins(input_file: str, output_file: str) -> int:
    ensure_parent_dir(output_file)
    run_cmd("-p", input_file, "-o", output_file)
    print(f"[plugins] {input_file} -> {output_file}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reference CLI for markitdown. Example input: agent/demo.pdf.",
        epilog=HELP_EPILOG or None,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Input file path.",
    )
    parser.add_argument(
        "--output",
        help="Output markdown path.",
    )
    parser.add_argument(
        "--mode",
        choices=["single", "plugins"],
        default="single",
        help="Run mode.",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if not args.input or not args.output:
        raise ValueError(f"{args.mode} mode requires input and --output")


def run_with_args(args: argparse.Namespace) -> int:
    if args.mode == "single":
        return run_single(args.input, args.output)
    if args.mode == "plugins":
        return run_plugins(args.input, args.output)
    raise ValueError(f"Unknown mode: {args.mode}")


def main() -> int:
    args = parse_args()
    try:
        validate_args(args)
        return run_with_args(args)
    except FileNotFoundError as exc:
        print(f"Command not found: {exc.filename or 'markitdown'}", file=sys.stderr)
        return 127
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as exc:
        return exc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
