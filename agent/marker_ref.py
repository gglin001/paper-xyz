#!/usr/bin/env python3
"""marker reference CLI script, using marker Python API directly.

Examples:
  pixi run -e marker python agent/marker_ref.py agent/demo.pdf -od md --mode fast
  pixi run -e marker python agent/marker_ref.py agent/demo.pdf -od md --mode standard
  pixi run -e marker python agent/marker_ref.py agent/demo.pdf -od md --mode quality

Notes:
  - Output format is fixed to markdown.
  - Default mode is fast. Other modes are often much slower, use with caution.
  - marker writes to a folder. With -od md and agent/demo.pdf, markdown is md/demo/demo.md.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import marker
from marker.config.parser import ConfigParser
from marker.models import create_model_dict
from marker.output import save_output

HELP_EPILOG = "\n".join((__doc__ or "").strip().splitlines()[2:]).strip()

MARKDOWN_MODES: dict[str, dict[str, Any]] = {
    "standard": {},
    "fast": {
        "disable_ocr": True,
        "disable_image_extraction": True,
    },
    "quality": {
        "lowres_image_dpi": 128,
        "highres_image_dpi": 256,
        "layout_coverage_min_lines": 1,
        "layout_coverage_threshold": 0.2,
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reference CLI for marker (Python API), markdown output only.",
        epilog=HELP_EPILOG or None,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "input",
        help="Input PDF path. Example: agent/demo.pdf.",
    )
    parser.add_argument(
        "-od",
        "--output-dir",
        required=True,
        help="Output directory. Example: md.",
    )
    parser.add_argument(
        "--mode",
        choices=sorted(MARKDOWN_MODES.keys()),
        default="fast",
        help="Built-in markdown profile. Default: fast. Other modes can be much slower.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input).resolve()
    if not input_path.exists():
        print(f"Input file not found: {input_path}", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    cli_options: dict[str, Any] = {
        "output_dir": str(output_dir),
        "output_format": "markdown",
        **MARKDOWN_MODES[args.mode],
    }

    config_parser = ConfigParser(cli_options)
    config_dict = config_parser.generate_config_dict()

    start = time.time()
    try:
        models = create_model_dict()
        converter_cls = config_parser.get_converter_cls()
        converter = converter_cls(
            config=config_dict,
            artifact_dict=models,
            processor_list=config_parser.get_processors(),
            renderer=config_parser.get_renderer(),
            llm_service=config_parser.get_llm_service(),
        )

        rendered = converter(str(input_path))
        out_folder = config_parser.get_output_folder(str(input_path))
        base_name = config_parser.get_base_filename(str(input_path))
        save_output(rendered, out_folder, base_name)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        return 130
    elapsed = time.time() - start
    marker_path = next(iter(marker.__path__))
    print(f"[marker] package_path={marker_path}")
    print(f"[marker] mode={args.mode} input={input_path}")
    print(f"[marker] output={out_folder}/{base_name}.md")
    print(f"[marker] config={json.dumps(config_dict, sort_keys=True)}")
    print(f"[marker] total_time={elapsed:.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
