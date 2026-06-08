#!/usr/bin/env python3
"""paper_xyz reference CLI script, VLM API mode only.

Examples:
  pixi run -e default python agent/paper_xyz_ref.py agent/demo.pdf
  pixi run -e default python agent/paper_xyz_ref.py agent/demo.pdf --start_page 0 --end_page 1
  pixi run -e default python agent/paper_xyz_ref.py agent/demo.pdf -o md/demo.paper_xyz.md --concurrency 8
  pixi run -e default python agent/paper_xyz_ref.py --list_model_services
  pixi run -e default python agent/paper_xyz_ref.py agent/demo.pdf --model_service rednote-hilab/dots.mocr
  pixi run -e default python agent/paper_xyz_ref.py agent/demo.pdf --model_service rednote-hilab/dots.mocr-svg
  pixi run -e default python agent/paper_xyz_ref.py agent/demo.pdf --model_service datalab-to/chandra-ocr-2

Notes:
  - Uses the focused implementation in src/paper_xyz.
  - Renders PDF pages locally with PyMuPDF and calls an OpenAI-compatible
    `chat/completions` endpoint page by page.
  - A page that exhausts retries is kept as a Markdown placeholder by default;
    use --fail_fast to restore all-or-nothing behavior.
  - The CLI exposes only shared runtime controls. Model-specific defaults live
    in src/paper_xyz/model_services.py.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import time
from pathlib import Path

import httpx
from paper_xyz import (
    DEFAULT_API,
    DEFAULT_MODEL_SERVICE,
    ConversionConfig,
    PdfToMarkdownConverter,
    iter_model_service_profiles,
)
from paper_xyz.converter import summarize_results
from paper_xyz.pdf import get_page_count, resolve_page_range

HELP_EPILOG = "\n".join((__doc__ or "").strip().splitlines()[2:]).strip()
LOG_FORMAT = "%(asctime)s\t%(levelname)s\t%(name)s: %(message)s"


def configure_logging(verbose: int) -> None:
    level = logging.DEBUG if verbose > 1 else logging.INFO
    logging.basicConfig(level=level, format=LOG_FORMAT)


def default_output_path(input_path: Path, start_page: int, end_page: int) -> Path:
    return Path("md") / f"{input_path.stem}.p{start_page}-{end_page}.paper_xyz.md"


def parse_api_key(arg_value: str | None) -> str | None:
    if arg_value:
        return arg_value
    for env_name in ("OPENAI_API_KEY", "API_KEY"):
        value = os.getenv(env_name)
        if value:
            return value
    return None


def format_model_services() -> str:
    lines = ["Available model services:"]
    for profile in iter_model_service_profiles():
        lines.append(
            f"  {profile.name}: model={profile.model} parser={profile.response_parser}"
        )
        lines.append(f"    {profile.description}")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Reference CLI for paper_xyz PDF to Markdown conversion over a remote "
            "OpenAI-compatible VLM API."
        ),
        epilog=HELP_EPILOG or None,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Input PDF path. Example: agent/demo.pdf.",
    )
    parser.add_argument(
        "--list_model_services",
        action="store_true",
        help="List built-in model service presets and exit.",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output markdown path. Defaults to md/<input-stem>.p<start>-<end>.paper_xyz.md.",
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
        "--api",
        default=DEFAULT_API,
        help="OpenAI-compatible /v1/chat/completions URL.",
    )
    parser.add_argument(
        "--model_service",
        default=DEFAULT_MODEL_SERVICE,
        help=(
            "Built-in model service preset. Default: "
            f"{DEFAULT_MODEL_SERVICE}. Use --list_model_services to inspect presets."
        ),
    )
    parser.add_argument(
        "--api_key",
        default=None,
        help="Bearer token. Falls back to OPENAI_API_KEY or API_KEY if unset.",
    )
    parser.add_argument(
        "--timeout", type=float, default=120.0, help="Per-request timeout in seconds."
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=4,
        help="Maximum number of pages processed concurrently.",
    )
    parser.add_argument(
        "--max_page_retries",
        type=int,
        default=8,
        help="Maximum attempts per page.",
    )
    parser.add_argument(
        "--fail_fast",
        action="store_true",
        help=(
            "Exit non-zero when any page exhausts retries. By default, failed "
            "pages are kept as Markdown placeholders so successful pages are written."
        ),
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="Set the verbosity level. -v for info logging, -vv for debug logging.",
    )
    args = parser.parse_args()
    if not args.input and not args.list_model_services:
        parser.error("input is required unless --list_model_services is used")
    return args


def build_config(args: argparse.Namespace) -> ConversionConfig:
    return ConversionConfig(
        api_url=args.api,
        model_service=args.model_service,
        api_key=parse_api_key(args.api_key),
        timeout=args.timeout,
        concurrency=args.concurrency,
        max_page_retries=args.max_page_retries,
        allow_page_failures=not args.fail_fast,
    )


def main() -> int:
    args = parse_args()
    if args.list_model_services:
        print(format_model_services())
        return 0

    configure_logging(args.verbose)

    input_path = Path(args.input).resolve()
    if not input_path.exists():
        logging.error("Input file not found: %s", input_path)
        return 1

    try:
        page_count = get_page_count(input_path)
        start_page, end_page = resolve_page_range(
            page_count=page_count,
            start_page=args.start_page,
            end_page=args.end_page,
        )
        config = build_config(args)
    except Exception as exc:
        logging.error("%s", exc)
        return 1

    output_path = (
        Path(args.output).resolve()
        if args.output
        else default_output_path(input_path, start_page, end_page).resolve()
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    start = time.time()
    try:
        converter = PdfToMarkdownConverter(config)
        markdown, page_results = asyncio.run(
            converter.convert(input_path, start_page=start_page, end_page=end_page)
        )
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:500] if exc.response is not None else ""
        logging.error(
            "API request failed: status=%s body=%s", exc.response.status_code, body
        )
        return 2
    except KeyboardInterrupt:
        logging.warning("Interrupted")
        return 130
    except Exception as exc:
        logging.error("%s", exc)
        return 2

    output_path.write_text(markdown, encoding="utf-8")
    stats = summarize_results(markdown, page_results)
    elapsed = time.time() - start

    logging.info("[paper_xyz] input=%s", input_path)
    logging.info("[paper_xyz] output=%s", output_path)
    logging.info(
        "[paper_xyz] page_range=%s-%s total_pages=%s", start_page, end_page, page_count
    )
    logging.info(
        "[paper_xyz] pages=%s failed_pages=%s chars=%s prompt_tokens=%s completion_tokens=%s total_time=%.2fs",
        stats.pages,
        stats.failed_pages,
        stats.chars,
        stats.prompt_tokens,
        stats.completion_tokens,
        elapsed,
    )
    failed_page_indexes = [
        str(page.page_index) for page in page_results if page.error is not None
    ]
    if failed_page_indexes:
        logging.warning(
            "[paper_xyz] failed_page_indexes=%s",
            ",".join(failed_page_indexes),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
