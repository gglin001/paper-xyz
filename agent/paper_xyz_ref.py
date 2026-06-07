#!/usr/bin/env python3
"""paper_xyz reference CLI script, VLM API mode only.

Examples:
  pixi run -e default python agent/paper_xyz_ref.py agent/demo.pdf
  pixi run -e default python agent/paper_xyz_ref.py agent/demo.pdf --start_page 0 --end_page 1
  pixi run -e default python agent/paper_xyz_ref.py agent/demo.pdf -o md/demo.paper_xyz.md --concurrency 8

Notes:
  - Uses the focused implementation in src/paper_xyz.
  - Renders PDF pages locally with PyMuPDF and calls an OpenAI-compatible
    `chat/completions` endpoint page by page.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import time
from pathlib import Path

import httpx

from paper_xyz import DEFAULT_MARKDOWN_PROMPT, ConversionConfig, PdfToMarkdownConverter
from paper_xyz.converter import summarize_results
from paper_xyz.pdf import get_page_count, resolve_page_range

HELP_EPILOG = "\n".join((__doc__ or "").strip().splitlines()[2:]).strip()
DEFAULT_API = "http://127.0.0.1:11235/v1/chat/completions"
DEFAULT_MODEL = "OCR"
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


def read_prompt(args: argparse.Namespace) -> str:
    if args.prompt_file:
        return Path(args.prompt_file).read_text(encoding="utf-8")
    if args.prompt:
        return args.prompt
    return DEFAULT_MARKDOWN_PROMPT


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Reference CLI for paper_xyz PDF to Markdown conversion over a remote "
            "OpenAI-compatible VLM API."
        ),
        epilog=HELP_EPILOG or None,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input", help="Input PDF path. Example: agent/demo.pdf.")
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
        "--model", default=DEFAULT_MODEL, help="Model name sent in the API payload."
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
        help="Maximum attempts per page, including rotation correction retries.",
    )
    parser.add_argument(
        "--max_tokens",
        type=int,
        default=8000,
        help="Token limit sent to chat/completions.",
    )
    parser.add_argument(
        "--token_param",
        default="max_tokens",
        choices=("max_tokens", "max_completion_tokens"),
        help="Name of the token-limit request field. Default: max_tokens.",
    )
    parser.add_argument(
        "--temperature", type=float, default=0.0, help="Sampling temperature."
    )
    parser.add_argument("--top_p", type=float, default=None, help="Optional top_p.")
    parser.add_argument("--top_k", type=int, default=None, help="Optional top_k.")
    parser.add_argument(
        "--frequency_penalty",
        type=float,
        default=0.0,
        help="Optional frequency_penalty.",
    )
    parser.add_argument(
        "--presence_penalty", type=float, default=0.0, help="Optional presence_penalty."
    )
    parser.add_argument(
        "--repetition_penalty",
        type=float,
        default=None,
        help="Optional repetition_penalty when supported by the backend.",
    )
    parser.add_argument(
        "--target_longest_image_dim",
        type=int,
        default=1288,
        help="Longest rendered page image dimension in pixels.",
    )
    parser.add_argument(
        "--prompt",
        default=None,
        help="Prompt text. Defaults to paper_xyz's Markdown prompt.",
    )
    parser.add_argument(
        "--prompt_file", default=None, help="Read prompt text from a file."
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="Set the verbosity level. -v for info logging, -vv for debug logging.",
    )
    return parser.parse_args()


def build_config(args: argparse.Namespace) -> ConversionConfig:
    return ConversionConfig(
        api_url=args.api,
        model=args.model,
        api_key=parse_api_key(args.api_key),
        prompt=read_prompt(args),
        timeout=args.timeout,
        concurrency=args.concurrency,
        max_page_retries=args.max_page_retries,
        max_tokens=args.max_tokens,
        token_param=args.token_param,
        temperature=args.temperature,
        top_p=args.top_p,
        top_k=args.top_k,
        frequency_penalty=args.frequency_penalty,
        presence_penalty=args.presence_penalty,
        repetition_penalty=args.repetition_penalty,
        target_longest_image_dim=args.target_longest_image_dim,
    )


def main() -> int:
    args = parse_args()
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
        "[paper_xyz] pages=%s chars=%s prompt_tokens=%s completion_tokens=%s total_time=%.2fs",
        stats.pages,
        stats.chars,
        stats.prompt_tokens,
        stats.completion_tokens,
        elapsed,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
