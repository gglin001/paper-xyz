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
import logging
import time
from pathlib import Path
from typing import Any

# `marker` is installed in the pixi `marker` environment, not in `default`.
import marker  # ty: ignore[unresolved-import]
from marker.config.parser import ConfigParser  # ty: ignore[unresolved-import]
from marker.models import create_model_dict  # ty: ignore[unresolved-import]
from marker.output import save_output  # ty: ignore[unresolved-import]

HELP_EPILOG = "\n".join((__doc__ or "").strip().splitlines()[2:]).strip()
LOG_FORMAT = "%(asctime)s\t%(levelname)s\t%(name)s: %(message)s"

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
    input_path = Path(args.input).resolve()
    if not input_path.exists():
        logging.error("Input file not found: %s", input_path)
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
        logging.error("%s", exc)
        return 1
    except KeyboardInterrupt:
        logging.warning("Interrupted")
        return 130
    elapsed = time.time() - start
    marker_path = next(iter(marker.__path__))
    logging.info("[marker] package_path=%s", marker_path)
    logging.info("[marker] mode=%s input=%s", args.mode, input_path)
    logging.info("[marker] output=%s/%s.md", out_folder, base_name)
    logging.debug("[marker] config=%s", json.dumps(config_dict, sort_keys=True))
    logging.info("[marker] total_time=%.2fs", elapsed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
