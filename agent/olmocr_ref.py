#!/usr/bin/env python3
"""olmocr reference CLI script, VLM API mode only.

Examples:
  pixi run -e default python agent/olmocr_ref.py agent/demo.pdf -o md/demo.olmocr.md
  pixi run -e default python agent/olmocr_ref.py agent/demo.pdf -o md/demo.olmocr.md --concurrency 8 --guided-decoding

Notes:
  - Uses olmocr's page render, prompt, and front matter parser, but calls a remote
    OpenAI-compatible `chat/completions` endpoint instead of running the full pipeline.
  - Best results usually come from servers/models that are already tuned for the
    olmocr prompt and markdown + YAML front matter output format.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import logging
import os
import shutil
import time
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

import httpx
from olmocr.data.renderpdf import render_pdf_to_base64png
from olmocr.prompts import PageResponse, build_no_anchoring_v4_yaml_prompt
from olmocr.train.front_matter import FrontMatterParser
from PIL import Image
from pypdf import PdfReader

HELP_EPILOG = "\n".join((__doc__ or "").strip().splitlines()[2:]).strip()
DEFAULT_API = "http://127.0.0.1:11235/v1/chat/completions"
DEFAULT_MODEL = "olmocr"
DEFAULT_PROMPT = build_no_anchoring_v4_yaml_prompt()
GUIDED_REGEX = (
    r"---\nprimary_language: (?:[a-z]{2}|null)\n"
    r"is_rotation_valid: (?:True|False|true|false)\n"
    r"rotation_correction: (?:0|90|180|270)\n"
    r"is_table: (?:True|False|true|false)\n"
    r"is_diagram: (?:True|False|true|false)\n"
    r"(?:---|---\n[\s\S]+)"
)
LOG_FORMAT = "%(asctime)s\t%(levelname)s\t%(name)s: %(message)s"


@dataclass(slots=True)
class PageConversion:
    page_num: int
    response: PageResponse
    input_tokens: int
    output_tokens: int
    attempts: int
    applied_rotation: int


def configure_logging(verbose: int) -> None:
    if verbose <= 1:
        logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    else:
        logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)


def default_output_path(input_path: Path) -> Path:
    return Path("md") / f"{input_path.stem}.olmocr.md"


def rotate_base64_png(image_base64: str, rotation: int) -> str:
    if rotation not in {0, 90, 180, 270}:
        raise ValueError(f"Unsupported rotation: {rotation}")
    if rotation == 0:
        return image_base64

    image_bytes = base64.b64decode(image_base64)
    with Image.open(BytesIO(image_bytes)) as image:
        if rotation == 90:
            transpose = Image.Transpose.ROTATE_90
        elif rotation == 180:
            transpose = Image.Transpose.ROTATE_180
        else:
            transpose = Image.Transpose.ROTATE_270

        rotated = image.transpose(transpose)
        output = BytesIO()
        rotated.save(output, format="PNG")

    return base64.b64encode(output.getvalue()).decode("utf-8")


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


def parse_page_markdown(markdown: str) -> PageResponse:
    parser = FrontMatterParser(front_matter_class=PageResponse)
    front_matter, text = parser._extract_front_matter_and_text(markdown)
    if front_matter:
        try:
            return parser._parse_front_matter(front_matter, text)
        except Exception as exc:
            logging.debug(
                "[olmocr] falling back to plain-markdown parsing after front matter parse failure: %s",
                exc,
            )

    natural_text = text.strip() if front_matter else markdown.strip()
    if natural_text.lower() == "null":
        natural_text = ""

    return PageResponse(
        primary_language=None,
        is_rotation_valid=True,
        rotation_correction=0,
        is_table=False,
        is_diagram=False,
        natural_text=natural_text or None,
    )


def build_markdown(page_results: list[PageConversion]) -> str:
    chunks: list[str] = []
    for page_result in sorted(page_results, key=lambda item: item.page_num):
        text = page_result.response.natural_text
        if text is not None:
            chunks.append(text.rstrip())
    markdown = "\n".join(chunks).strip()
    return f"{markdown}\n" if markdown else ""


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


async def build_request_payload(
    input_path: Path,
    page_num: int,
    *,
    model: str,
    prompt: str,
    max_tokens: int,
    temperature: float,
    target_longest_image_dim: int,
    rotation: int,
    guided_decoding: bool,
) -> dict[str, Any]:
    image_base64 = await asyncio.to_thread(
        render_pdf_to_base64png,
        str(input_path),
        page_num,
        target_longest_image_dim,
    )
    image_base64 = await asyncio.to_thread(rotate_base64_png, image_base64, rotation)

    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_base64}"},
                    },
                ],
            }
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if guided_decoding:
        payload["guided_regex"] = GUIDED_REGEX
    return payload


async def request_page_once(
    client: httpx.AsyncClient,
    args: argparse.Namespace,
    input_path: Path,
    page_num: int,
    rotation: int,
) -> PageConversion:
    payload = await build_request_payload(
        input_path,
        page_num,
        model=args.model,
        prompt=args.prompt,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        target_longest_image_dim=args.target_longest_image_dim,
        rotation=rotation,
        guided_decoding=args.guided_decoding,
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

    markdown = extract_message_text(message.get("content"))
    if not markdown.strip():
        raise ValueError(f"Page {page_num} response content is empty")

    finish_reason = choice.get("finish_reason")
    if finish_reason not in (None, "stop", "end_turn"):
        raise ValueError(f"Page {page_num} finish_reason={finish_reason}")

    page_response = parse_page_markdown(markdown)
    usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
    input_tokens = int(usage.get("prompt_tokens", 0) or 0)
    output_tokens = int(usage.get("completion_tokens", 0) or 0)

    return PageConversion(
        page_num=page_num,
        response=page_response,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        attempts=1,
        applied_rotation=rotation,
    )


async def convert_page(
    client: httpx.AsyncClient,
    args: argparse.Namespace,
    input_path: Path,
    page_num: int,
) -> PageConversion:
    last_valid_result: PageConversion | None = None
    cumulative_rotation = 0
    last_error: Exception | None = None

    for attempt in range(1, args.max_page_retries + 1):
        try:
            result = await request_page_once(
                client, args, input_path, page_num, cumulative_rotation
            )
            result.attempts = attempt
            last_valid_result = result

            if result.response.is_rotation_valid:
                logging.info(
                    "[olmocr] page=%s attempts=%s prompt_tokens=%s completion_tokens=%s rotation=%s",
                    page_num,
                    attempt,
                    result.input_tokens,
                    result.output_tokens,
                    result.applied_rotation,
                )
                return result

            correction = result.response.rotation_correction % 360
            cumulative_rotation = (cumulative_rotation + correction) % 360
            logging.info(
                "[olmocr] page=%s attempt=%s requested rotation retry, correction=%s next_rotation=%s",
                page_num,
                attempt,
                correction,
                cumulative_rotation,
            )
        except (httpx.HTTPError, ValueError) as exc:
            last_error = exc
            logging.warning(
                "[olmocr] page=%s attempt=%s failed: %s", page_num, attempt, exc
            )

        if attempt < args.max_page_retries:
            await asyncio.sleep(min(2 ** (attempt - 1), 8))

    if last_valid_result is not None:
        logging.warning(
            "[olmocr] page=%s exhausted retries, keeping last rotation-invalid response",
            page_num,
        )
        return last_valid_result

    raise RuntimeError(f"olmocr conversion failed for page {page_num}: {last_error}")


async def convert_pdf(
    args: argparse.Namespace, input_path: Path
) -> tuple[str, list[PageConversion]]:
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
        headers=headers, limits=limits, timeout=timeout
    ) as client:

        async def run_page(page_num: int) -> PageConversion:
            async with semaphore:
                return await convert_page(client, args, input_path, page_num)

        tasks = [
            asyncio.create_task(run_page(page_num))
            for page_num in range(1, page_count + 1)
        ]
        results = await asyncio.gather(*tasks)

    markdown = build_markdown(results)
    return markdown, results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Reference CLI for olmocr-style PDF to markdown conversion over a remote "
            "OpenAI-compatible VLM API."
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
        help="Output markdown path. Defaults to md/<input-stem>.olmocr.md.",
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
        default=8,
        help="Maximum attempts per page, including rotation correction retries.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=8000,
        help="max_tokens sent to chat/completions.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Sampling temperature sent to chat/completions.",
    )
    parser.add_argument(
        "--target-longest-image-dim",
        type=int,
        default=1288,
        help="Longest rendered page image dimension in pixels.",
    )
    parser.add_argument(
        "--prompt",
        default=DEFAULT_PROMPT,
        help="Prompt text. Default is olmocr's no-anchoring v4 YAML prompt.",
    )
    parser.add_argument(
        "--guided-decoding",
        action="store_true",
        help="Attach olmocr's guided regex to the request body.",
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

    output_path = (
        Path(args.output).resolve()
        if args.output
        else default_output_path(input_path).resolve()
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    start = time.time()
    try:
        markdown, page_results = asyncio.run(convert_pdf(args, input_path))
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
    elapsed = time.time() - start
    total_input_tokens = sum(page.input_tokens for page in page_results)
    total_output_tokens = sum(page.output_tokens for page in page_results)

    logging.info("[olmocr] input=%s", input_path)
    logging.info("[olmocr] output=%s", output_path)
    logging.info(
        "[olmocr] pages=%s chars=%s prompt_tokens=%s completion_tokens=%s total_time=%.2fs",
        len(page_results),
        len(markdown),
        total_input_tokens,
        total_output_tokens,
        elapsed,
    )
    logging.debug("[olmocr] import_source=third_party/olmocr")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
