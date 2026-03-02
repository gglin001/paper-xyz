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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reference CLI for markitdown. Example input: agent/demo.pdf.",
        epilog=HELP_EPILOG or None,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "input",
        help="Input file path.",
    )
    parser.add_argument(
        "--output",
        "-o",
        required=True,
        help="Output markdown path.",
    )
    parser.add_argument(
        "--mode",
        choices=["single", "plugins"],
        default="single",
        help="Run mode.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    command = ["markitdown"]
    if args.mode == "plugins":
        command.append("-p")
    command.extend([str(input_path), "-o", str(output_path)])

    try:
        subprocess.run(command, check=True)
    except FileNotFoundError as exc:
        print(f"Command not found: {exc.filename or 'markitdown'}", file=sys.stderr)
        return 127
    except subprocess.CalledProcessError as exc:
        return exc.returncode
    print(f"[markitdown:{args.mode}] {input_path} -> {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
