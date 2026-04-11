#!/usr/bin/env python3
"""olmocr + dots.mocr reference CLI script, VLM API mode only.

Examples:
  pixi run -e default python agent/olmocr_dots_mocr_rerf.py agent/demo.pdf -o md/demo.olmocr_dots_mocr.md
  pixi run -e default python agent/olmocr_dots_mocr_rerf.py agent/demo.pdf -o md/demo.olmocr_dots_mocr.md --svg-dir debug_agent/demo_svg --concurrency 8

Notes:
  - Uses olmocr's PDF page rendering helper, but sends requests in the style of
    third_party/dots.mocr image-to-SVG inference.
  - Writes one SVG per page plus an aggregate Markdown manifest.
  - Default args assume an OpenAI-compatible `chat/completions` API exists, but
    this script does not require a real server for `--help` or import checks.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import logging
import os
import re
import shutil
import time
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

import httpx
from olmocr.data.renderpdf import render_pdf_to_base64png
from PIL import Image
from pypdf import PdfReader

HELP_EPILOG = "\n".join((__doc__ or "").strip().splitlines()[2:]).strip()
DEFAULT_API = "http://127.0.0.1:11235/v1/chat/completions"
DEFAULT_MODEL = "olmocr"
DEFAULT_PROMPT_TEMPLATE = (
    'Please generate the SVG code based on the image.viewBox="0 0 {width} {height}"'
)
DEFAULT_TEXT_PREFIX = "<|img|><|imgpad|><|endofimg|>"
LOG_FORMAT = "%(asctime)s\t%(levelname)s\t%(name)s: %(message)s"
SVG_FENCE_RE = re.compile(
    r"^\s*```(?:svg|xml|html)?\s*(.*?)\s*```\s*$",
    re.DOTALL | re.IGNORECASE,
)
SVG_COMPLETE_RE = re.compile(r"<svg\b[^>]*>.*?</svg>", re.DOTALL | re.IGNORECASE)
SVG_OPEN_RE = re.compile(r"<svg\b[^>]*>.*", re.DOTALL | re.IGNORECASE)
SVG_TAG_RE = re.compile(r"</?\s*([a-zA-Z][\w:-]*)\b[^>]*?/?>")


@dataclass(slots=True)
class PageConversion:
    page_num: int
    raw_response: str
    svg_content: str | None
    input_tokens: int
    output_tokens: int
    attempts: int
    image_width: int
    image_height: int
    svg_path: Path | None = None


def configure_logging(verbose: int) -> None:
    if verbose <= 1:
        logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    else:
        logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)


def default_output_path(input_path: Path) -> Path:
    return Path("md") / f"{input_path.stem}.olmocr_dots_mocr.md"


def default_svg_dir(output_path: Path) -> Path:
    return Path(f"{output_path.with_suffix('')}_svg")


def get_num_pages(input_path: Path) -> int:
    reader = PdfReader(str(input_path))
    return len(reader.pages)


def check_external_tools() -> list[str]:
    required_tools = ("pdfinfo", "pdftoppm")
    return [tool for tool in required_tools if shutil.which(tool) is None]


def parse_api_key(arg_value: str | None) -> str | None:
    if arg_value:
        return arg_value
    for env_name in ("OPENAI_API_KEY", "API_KEY"):
        if os.getenv(env_name):
            return os.environ[env_name]
    return None


def extract_message_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if isinstance(text, str):
                parts.append(text)
            elif isinstance(text, dict) and isinstance(text.get("value"), str):
                parts.append(text["value"])
        return "".join(parts)
    raise ValueError(f"Unsupported message content type: {type(content).__name__}")


def decode_base64_png_size(image_base64: str) -> tuple[int, int]:
    image_bytes = base64.b64decode(image_base64)
    with Image.open(BytesIO(image_bytes)) as image:
        return image.size


def build_svg_prompt(prompt_template: str, width: int, height: int) -> str:
    return prompt_template.replace("{width}", str(width)).replace(
        "{height}", str(height)
    )


def unwrap_code_fence(text: str) -> str:
    match = SVG_FENCE_RE.match(text)
    if match:
        return match.group(1).strip()
    return text.strip()


def fix_svg(svg: str) -> str:
    if re.search(r'(<path\b[^>]*\bd="[^">]*$)', svg):
        svg += '">'

    svg = re.sub(r"<[^>]*$", "", svg)

    stack: list[str] = []
    for match in SVG_TAG_RE.finditer(svg):
        name = match.group(1)
        token = match.group(0)
        is_close = token.lstrip().startswith("</")
        is_self_close = token.rstrip().endswith("/>")

        if is_self_close:
            continue
        if not is_close:
            stack.append(name)
            continue
        if name not in stack:
            continue
        while stack and stack[-1] != name:
            stack.pop()
        if stack and stack[-1] == name:
            stack.pop()

    while stack:
        svg += f"</{stack.pop()}>"

    return svg


def ensure_svg_root_attributes(svg: str, width: int, height: int) -> str:
    match = re.search(r"<svg\b[^>]*>", svg, flags=re.IGNORECASE)
    if not match:
        return svg

    opening_tag = match.group(0)
    extra_attrs: list[str] = []
    if "xmlns=" not in opening_tag:
        extra_attrs.append('xmlns="http://www.w3.org/2000/svg"')
    if "viewBox=" not in opening_tag:
        extra_attrs.append(f'viewBox="0 0 {width} {height}"')
    if "width=" not in opening_tag:
        extra_attrs.append(f'width="{width}"')
    if "height=" not in opening_tag:
        extra_attrs.append(f'height="{height}"')
    if not extra_attrs:
        return svg

    patched_tag = f"{opening_tag[:-1]} {' '.join(extra_attrs)}>"
    return svg.replace(opening_tag, patched_tag, 1)


def extract_svg_from_response(
    response: str,
    *,
    width: int,
    height: int,
) -> tuple[str | None, bool]:
    candidate = unwrap_code_fence(response)
    candidate = re.sub(r"^\s*svg:\s*", "", candidate, flags=re.IGNORECASE)

    match = SVG_COMPLETE_RE.search(candidate)
    if match:
        svg = ensure_svg_root_attributes(match.group(0).strip(), width, height)
        return svg, True

    match = SVG_OPEN_RE.search(candidate)
    if match:
        svg = ensure_svg_root_attributes(fix_svg(match.group(0).strip()), width, height)
        return svg, True

    return None, False


async def build_request_payload(
    input_path: Path,
    page_num: int,
    *,
    model: str,
    prompt_template: str,
    text_prefix: str,
    max_tokens: int,
    token_param: str,
    temperature: float,
    top_p: float,
    target_longest_image_dim: int,
) -> tuple[dict[str, Any], int, int]:
    image_base64 = await asyncio.to_thread(
        render_pdf_to_base64png,
        str(input_path),
        page_num,
        target_longest_image_dim,
    )
    image_width, image_height = await asyncio.to_thread(
        decode_base64_png_size, image_base64
    )
    prompt = build_svg_prompt(prompt_template, image_width, image_height)

    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_base64}"},
                    },
                    {"type": "text", "text": f"{text_prefix}{prompt}"},
                ],
            }
        ],
        "temperature": temperature,
        "top_p": top_p,
    }
    payload[token_param] = max_tokens
    return payload, image_width, image_height


async def request_page_once(
    client: httpx.AsyncClient,
    args: argparse.Namespace,
    input_path: Path,
    page_num: int,
) -> PageConversion:
    payload, image_width, image_height = await build_request_payload(
        input_path,
        page_num,
        model=args.model,
        prompt_template=args.prompt_template,
        text_prefix=args.text_prefix,
        max_tokens=args.max_tokens,
        token_param=args.token_param,
        temperature=args.temperature,
        top_p=args.top_p,
        target_longest_image_dim=args.target_longest_image_dim,
    )
    response = await client.post(args.api, json=payload)
    response.raise_for_status()

    try:
        data = response.json()
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Page {page_num} returned invalid JSON: {response.text[:500]}"
        ) from exc

    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError(f"Page {page_num} response is missing choices")

    choice = choices[0]
    message = choice.get("message")
    if not isinstance(message, dict):
        raise ValueError(f"Page {page_num} response is missing message")

    raw_response = extract_message_text(message.get("content")).strip()
    if not raw_response:
        raise ValueError(f"Page {page_num} response content is empty")

    finish_reason = choice.get("finish_reason")
    if finish_reason not in (None, "stop", "end_turn"):
        raise ValueError(f"Page {page_num} finish_reason={finish_reason}")

    svg_content, _ = extract_svg_from_response(
        raw_response,
        width=image_width,
        height=image_height,
    )
    usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
    input_tokens = int(usage.get("prompt_tokens", 0) or 0)
    output_tokens = int(usage.get("completion_tokens", 0) or 0)

    return PageConversion(
        page_num=page_num,
        raw_response=raw_response,
        svg_content=svg_content,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        attempts=1,
        image_width=image_width,
        image_height=image_height,
    )


async def convert_page(
    client: httpx.AsyncClient,
    args: argparse.Namespace,
    input_path: Path,
    page_num: int,
) -> PageConversion:
    last_error: Exception | None = None

    for attempt in range(1, args.max_page_retries + 1):
        try:
            result = await request_page_once(client, args, input_path, page_num)
            result.attempts = attempt
            logging.info(
                "[olmocr_dots_mocr] page=%s attempts=%s svg=%s size=%sx%s prompt_tokens=%s completion_tokens=%s",
                page_num,
                attempt,
                "yes" if result.svg_content else "no",
                result.image_width,
                result.image_height,
                result.input_tokens,
                result.output_tokens,
            )
            return result
        except (httpx.HTTPError, ValueError) as exc:
            last_error = exc
            logging.warning(
                "[olmocr_dots_mocr] page=%s attempt=%s failed: %s",
                page_num,
                attempt,
                exc,
            )
            if attempt < args.max_page_retries:
                await asyncio.sleep(min(2 ** (attempt - 1), 8))

    raise RuntimeError(
        f"olmocr_dots_mocr conversion failed for page {page_num}: {last_error}"
    )


async def convert_pdf(
    args: argparse.Namespace,
    input_path: Path,
) -> list[PageConversion]:
    page_count = get_num_pages(input_path)
    semaphore = asyncio.Semaphore(args.concurrency)
    api_key = parse_api_key(args.api_key)
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else None
    limits = httpx.Limits(
        max_connections=args.concurrency,
        max_keepalive_connections=args.concurrency,
    )
    timeout = httpx.Timeout(args.timeout)

    async with httpx.AsyncClient(
        headers=headers,
        limits=limits,
        timeout=timeout,
    ) as client:

        async def run_page(page_num: int) -> PageConversion:
            async with semaphore:
                return await convert_page(client, args, input_path, page_num)

        tasks = [
            asyncio.create_task(run_page(page_num))
            for page_num in range(1, page_count + 1)
        ]
        return await asyncio.gather(*tasks)


def make_relative_path(path: Path, start: Path) -> str:
    try:
        return os.path.relpath(path, start)
    except ValueError:
        return str(path)


def build_markdown(
    input_path: Path,
    output_path: Path,
    page_results: list[PageConversion],
) -> str:
    lines = [
        "# Generated SVG Pages",
        "",
        f"Source PDF: `{input_path}`",
        "",
        f"Total pages: {len(page_results)}",
    ]

    for page_result in sorted(page_results, key=lambda item: item.page_num):
        lines.extend(
            [
                "",
                f"## Page {page_result.page_num}",
                "",
                (
                    f"SVG file: `{make_relative_path(page_result.svg_path, output_path.parent)}`"
                    if page_result.svg_path is not None
                    else "SVG extraction failed for this page, raw model output is included below."
                ),
                "",
            ]
        )

        if page_result.svg_content is not None:
            lines.extend(["```svg", page_result.svg_content.rstrip(), "```"])
        else:
            lines.extend(["```text", page_result.raw_response.rstrip(), "```"])

    return "\n".join(lines).rstrip() + "\n"


def write_outputs(
    input_path: Path,
    output_path: Path,
    svg_dir: Path,
    page_results: list[PageConversion],
) -> tuple[str, int]:
    svg_dir.mkdir(parents=True, exist_ok=True)
    digits = max(4, len(str(len(page_results))))
    svg_count = 0

    for page_result in sorted(page_results, key=lambda item: item.page_num):
        if page_result.svg_content is None:
            continue
        svg_path = svg_dir / f"page_{page_result.page_num:0{digits}d}.svg"
        svg_path.write_text(page_result.svg_content.rstrip() + "\n", encoding="utf-8")
        page_result.svg_path = svg_path
        svg_count += 1

    markdown = build_markdown(input_path, output_path, page_results)
    output_path.write_text(markdown, encoding="utf-8")
    return markdown, svg_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Reference CLI for PDF to Markdown + per-page SVG conversion using "
            "olmocr page rendering and dots.mocr-style image-to-SVG prompting."
        ),
        epilog=HELP_EPILOG or None,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "input",
        help="Input PDF path. Example: agent/demo.pdf.",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output markdown path. Defaults to md/<input-stem>.olmocr_dots_mocr.md.",
    )
    parser.add_argument(
        "--svg-dir",
        help=(
            "Directory for per-page SVG outputs. Defaults to "
            "<output-without-suffix>_svg."
        ),
    )
    parser.add_argument(
        "--api",
        default=DEFAULT_API,
        help="OpenAI-compatible /v1/chat/completions URL.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="Model name sent in the API payload.",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Bearer token. Falls back to OPENAI_API_KEY or API_KEY if unset.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="Per-request timeout in seconds.",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=4,
        help="Maximum number of pages processed concurrently.",
    )
    parser.add_argument(
        "--max-page-retries",
        type=int,
        default=4,
        help="Maximum attempts per page.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=32768,
        help="Maximum completion tokens requested from the API.",
    )
    parser.add_argument(
        "--token-param",
        choices=("max_completion_tokens", "max_tokens"),
        default="max_completion_tokens",
        help="Payload key used for the token limit field.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.9,
        help="Sampling temperature. dots.mocr SVG examples use a non-zero value.",
    )
    parser.add_argument(
        "--top-p",
        type=float,
        default=1.0,
        help="top_p sent to chat/completions.",
    )
    parser.add_argument(
        "--target-longest-image-dim",
        type=int,
        default=1024,
        help="Longest rendered page image dimension in pixels.",
    )
    parser.add_argument(
        "--prompt-template",
        default=DEFAULT_PROMPT_TEMPLATE,
        help="Prompt template. Supports {width} and {height} placeholders.",
    )
    parser.add_argument(
        "--text-prefix",
        default=DEFAULT_TEXT_PREFIX,
        help="Text prefix prepended before the final SVG prompt.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="Set the verbosity level. -v for info logging, -vv for debug logging.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    configure_logging(args.verbose)

    if args.concurrency < 1:
        logging.error("--concurrency must be >= 1")
        return 1
    if args.max_page_retries < 1:
        logging.error("--max-page-retries must be >= 1")
        return 1

    missing_tools = check_external_tools()
    if missing_tools:
        logging.error(
            "Missing required external tools: %s. Install Poppler so olmocr page rendering can call pdfinfo/pdftoppm.",
            ", ".join(missing_tools),
        )
        return 1

    input_path = Path(args.input).resolve()
    if not input_path.exists():
        logging.error("Input file not found: %s", input_path)
        return 1
    if input_path.suffix.lower() != ".pdf":
        logging.error("Only PDF input is supported: %s", input_path)
        return 1

    output_path = (
        Path(args.output).resolve()
        if args.output
        else default_output_path(input_path).resolve()
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    svg_dir = (
        Path(args.svg_dir).resolve() if args.svg_dir else default_svg_dir(output_path)
    )
    svg_dir.mkdir(parents=True, exist_ok=True)

    start = time.time()
    try:
        page_results = asyncio.run(convert_pdf(args, input_path))
        markdown, svg_count = write_outputs(
            input_path,
            output_path,
            svg_dir,
            page_results,
        )
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:500] if exc.response is not None else ""
        status_code = (
            exc.response.status_code if exc.response is not None else "unknown"
        )
        logging.error(
            "API request failed: status=%s body=%s",
            status_code,
            body,
        )
        return 2
    except KeyboardInterrupt:
        logging.warning("Interrupted")
        return 130
    except Exception as exc:
        logging.error("%s", exc)
        return 2

    elapsed = time.time() - start
    total_input_tokens = sum(page.input_tokens for page in page_results)
    total_output_tokens = sum(page.output_tokens for page in page_results)
    missing_svg_pages = [
        str(page.page_num) for page in page_results if page.svg_content is None
    ]

    logging.info("[olmocr_dots_mocr] input=%s", input_path)
    logging.info("[olmocr_dots_mocr] output_md=%s", output_path)
    logging.info("[olmocr_dots_mocr] output_svg_dir=%s", svg_dir)
    logging.info(
        "[olmocr_dots_mocr] pages=%s svg_pages=%s chars=%s prompt_tokens=%s completion_tokens=%s total_time=%.2fs",
        len(page_results),
        svg_count,
        len(markdown),
        total_input_tokens,
        total_output_tokens,
        elapsed,
    )
    if missing_svg_pages:
        logging.warning(
            "[olmocr_dots_mocr] pages without extracted SVG: %s",
            ", ".join(missing_svg_pages),
        )
    logging.debug("[olmocr_dots_mocr] refs=third_party/dots.mocr + third_party/olmocr")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
