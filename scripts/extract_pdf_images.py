#!/usr/bin/env python3
"""Extract embedded PDF images without calling a VLM API.

Examples:
  pixi run -e default python scripts/extract_pdf_images.py raw/file_name.pdf
  pixi run -e default python scripts/extract_pdf_images.py raw/file_name.pdf -o md/file_name
  pixi run -e default python scripts/extract_pdf_images.py raw/file_name.pdf -o md/file_name --min_image_width 64 --min_image_height 64
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from paper_xyz import ImageExtractionConfig, extract_images_to_directory
from paper_xyz.pdf import get_page_count, resolve_page_range

LOG_FORMAT = "%(asctime)s\t%(levelname)s\t%(name)s: %(message)s"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract PDF images as page-X-image-Y.png without using a VLM."
    )
    parser.add_argument("input", help="Input PDF path. Example: raw/file_name.pdf.")
    parser.add_argument(
        "--output_dir",
        "-o",
        default=None,
        help="Image output directory. Defaults to md/<input-stem>.",
    )
    parser.add_argument(
        "--start_page",
        type=int,
        default=0,
        help="First PDF page number to process, 0-based and inclusive. Default: 0.",
    )
    parser.add_argument(
        "--end_page",
        type=int,
        default=None,
        help="Last PDF page number to process, 0-based and inclusive. Default: last page.",
    )
    parser.add_argument(
        "--image_bbox_tolerance",
        type=float,
        default=1.0,
        help=(
            "PDF-point tolerance used to collapse duplicate image occurrences. "
            "Default: 1.0."
        ),
    )
    parser.add_argument(
        "--min_image_width",
        type=int,
        default=32,
        help="Skip images narrower than this many pixels. Default: 32.",
    )
    parser.add_argument(
        "--min_image_height",
        type=int,
        default=32,
        help="Skip images shorter than this many pixels. Default: 32.",
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
    level = logging.DEBUG if verbose > 1 else logging.INFO
    logging.basicConfig(level=level, format=LOG_FORMAT)


def main() -> int:
    args = parse_args()
    configure_logging(args.verbose)

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.is_file():
        logging.error("PDF file not found: %s", input_path)
        return 1

    output_dir = (
        Path(args.output_dir).expanduser().resolve()
        if args.output_dir
        else (Path("md") / input_path.stem).resolve()
    )

    try:
        page_count = get_page_count(input_path)
        start_page, end_page = resolve_page_range(
            page_count=page_count,
            start_page=args.start_page,
            end_page=args.end_page,
        )
        config = ImageExtractionConfig(
            enabled=True,
            bbox_tolerance=args.image_bbox_tolerance,
            min_width=args.min_image_width,
            min_height=args.min_image_height,
        )
        images_by_page = extract_images_to_directory(
            input_path,
            output_dir,
            start_page=start_page,
            end_page=end_page,
            config=config,
        )
    except Exception as exc:
        logging.error("%s", exc)
        return 2

    extracted_images = sum(len(images) for images in images_by_page.values())
    logging.info("[paper_xyz] input: %s", input_path)
    logging.info("[paper_xyz] output_dir: %s", output_dir)
    logging.info(
        "[paper_xyz] page_range=%s-%s total_pages=%s extracted_images=%s",
        start_page,
        end_page,
        page_count,
        extracted_images,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
