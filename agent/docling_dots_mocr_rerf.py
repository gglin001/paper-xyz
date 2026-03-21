#!/usr/bin/env python3
"""dots.mocr-style PDF -> Markdown + SVG reference CLI.

Examples:
  pixi run -e default python agent/docling_dots_mocr_rerf.py agent/demo.pdf -o md/demo.dots.mocr.md
  pixi run -e default python agent/docling_dots_mocr_rerf.py pdf/paper.pdf -o md/paper.dots.mocr.md --svg-dir svg/paper.dots.mocr
  pixi run -e default python agent/docling_dots_mocr_rerf.py debug_agent/paper.subset.pdf --concurrency 8 --svg-model rednote-hilab/dots.mocr-svg

Notes:
  - Follows the request format used by third_party/dots.mocr.
  - Writes one combined Markdown file plus one SVG file per PDF page.
"""

from __future__ import annotations

import argparse
import base64
import json
import logging
import math
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

import fitz
import requests
from PIL import Image

HELP_EPILOG = "\n".join((__doc__ or "").strip().splitlines()[2:]).strip()
DEFAULT_API = "http://127.0.0.1:11235/v1/chat/completions"
DEFAULT_MODEL = "rednote-hilab/dots.mocr"
DEFAULT_MD_PROMPT = """Please output the layout information from the PDF image, including each layout element's bbox, its category, and the corresponding text content within the bbox.

1. Bbox format: [x1, y1, x2, y2]

2. Layout Categories: The possible categories are ['Caption', 'Footnote', 'Formula', 'List-item', 'Page-footer', 'Page-header', 'Picture', 'Section-header', 'Table', 'Text', 'Title'].

3. Text Extraction & Formatting Rules:
    - Picture: For the 'Picture' category, the text field should be omitted.
    - Formula: Format its text as LaTeX.
    - Table: Format its text as HTML.
    - All Others (Text, Title, etc.): Format their text as Markdown.

4. Constraints:
    - The output text must be the original text from the image, with no translation.
    - All layout elements must be sorted according to human reading order.

5. Final Output: The entire output must be a single JSON object.
"""
DEFAULT_SVG_PROMPT_TEMPLATE = (
    'Please generate the SVG code based on the image.viewBox="0 0 {width} {height}"'
)
DEFAULT_TIMEOUT = 180.0
DEFAULT_MAX_COMPLETION_TOKENS = 32768
DEFAULT_DPI = 200
DEFAULT_CONCURRENCY = 4
DEFAULT_MAX_PAGE_PIXELS = 11_289_600
LOG_FORMAT = "%(asctime)s\t%(levelname)s\t%(name)s: %(message)s"
FENCED_BLOCK_RE = re.compile(
    r"^\s*```(?:json|xml|svg|markdown|md)?\s*\n?(.*?)\n?```\s*$",
    re.DOTALL,
)
SVG_TAG_RE = re.compile(r"</?\s*([a-zA-Z][\w:-]*)\b[^>]*?/?>")


@dataclass(slots=True)
class PageResult:
    page_index: int
    markdown: str
    svg_path: Path | None
    svg_raw_path: Path | None
    markdown_from_raw_response: bool


def image_to_data_url(image: Image.Image, fmt: str = "PNG") -> str:
    buffer = BytesIO()
    image.save(buffer, format=fmt)
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/{fmt.lower()};base64,{encoded}"


def build_messages(
    image: Image.Image, prompt: str, system_prompt: str | None = None
) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append(
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": image_to_data_url(image)},
                },
                {
                    "type": "text",
                    # dots.mocr keeps the image token prefix to avoid an extra leading newline.
                    "text": f"<|img|><|imgpad|><|endofimg|>{prompt}",
                },
            ],
        }
    )
    return messages


def extract_message_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("response does not contain choices")
    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise ValueError("response does not contain a message")
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)
    raise ValueError("response message content is neither text nor a text-part list")


def call_chat_completion(
    *,
    api: str,
    model: str,
    image: Image.Image,
    prompt: str,
    temperature: float,
    top_p: float,
    max_completion_tokens: int,
    timeout: float,
    system_prompt: str | None = None,
) -> str:
    headers = {"Content-Type": "application/json"}
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model,
        "messages": build_messages(image, prompt, system_prompt=system_prompt),
        "temperature": temperature,
        "top_p": top_p,
        "max_completion_tokens": max_completion_tokens,
    }
    response = requests.post(api, json=payload, headers=headers, timeout=timeout)
    response.raise_for_status()
    return extract_message_text(response.json())


def strip_single_fence(text: str) -> str:
    match = FENCED_BLOCK_RE.match(text)
    if match:
        return match.group(1).strip()
    return text.strip()


def load_json_from_response(text: str) -> Any:
    candidates: list[str] = []
    stripped = strip_single_fence(text)
    candidates.append(stripped)

    for match in re.finditer(r"```(?:json)?\s*(.*?)```", text, re.DOTALL):
        candidates.append(match.group(1).strip())

    for open_char, close_char in (("{", "}"), ("[", "]")):
        start = text.find(open_char)
        end = text.rfind(close_char)
        if start != -1 and end != -1 and end > start:
            candidates.append(text[start : end + 1].strip())

    seen: set[str] = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, str):
            try:
                return json.loads(parsed)
            except json.JSONDecodeError:
                return parsed
        return parsed
    raise ValueError("unable to parse JSON from model response")


def is_layout_cell_list(value: Any) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, dict) and "bbox" in item and "category" in item
        for item in value
    )


def find_layout_cells(value: Any) -> list[dict[str, Any]] | None:
    if is_layout_cell_list(value):
        return value
    if isinstance(value, dict):
        if "bbox" in value and "category" in value:
            return [value]
        for key in (
            "cells",
            "layouts",
            "layout",
            "elements",
            "items",
            "blocks",
            "results",
            "data",
        ):
            candidate = value.get(key)
            found = find_layout_cells(candidate)
            if found is not None:
                return found
        for candidate in value.values():
            found = find_layout_cells(candidate)
            if found is not None:
                return found
    if isinstance(value, list):
        for candidate in value:
            found = find_layout_cells(candidate)
            if found is not None:
                return found
    return None


def has_latex_markdown(text: str) -> bool:
    patterns = [
        r"\$\$.*?\$\$",
        r"\$[^$\n]+?\$",
        r"\\begin\{.*?\}.*?\\end\{.*?\}",
        r"\\[a-zA-Z]+\{.*?\}",
        r"\\[a-zA-Z]+",
        r"\\\[.*?\\\]",
        r"\\\(.*?\\\)",
    ]
    return any(re.search(pattern, text, re.DOTALL) for pattern in patterns)


def clean_latex_preamble(text: str) -> str:
    patterns = [
        r"\\documentclass\{[^}]+\}",
        r"\\usepackage\{[^}]+\}",
        r"\\usepackage\[[^\]]*\]\{[^}]+\}",
        r"\\begin\{document\}",
        r"\\end\{document\}",
    ]
    for pattern in patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    return text


def get_formula_in_markdown(text: str) -> str:
    text = text.strip()
    if not text:
        return ""
    if text.startswith("$$") and text.endswith("$$"):
        inner = text[2:-2].strip()
        if "$" not in inner:
            return f"$$\n{inner}\n$$"
        return text
    if text.startswith("\\[") and text.endswith("\\]"):
        inner = text[2:-2].strip()
        return f"$$\n{inner}\n$$"
    if re.findall(r".*\\\[.*\\\].*", text):
        return text
    if re.findall(r"\$([^$]+)\$", text):
        return text
    if not has_latex_markdown(text):
        return text
    if "usepackage" in text:
        text = clean_latex_preamble(text)
    if text.startswith("`") and text.endswith("`"):
        text = text[1:-1]
    return f"$$\n{text}\n$$"


def clean_text(text: str) -> str:
    text = text.strip()
    if text.startswith("`$") and text.endswith("$`"):
        text = text[1:-1]
    return text


def layout_cells_to_markdown(
    cells: list[dict[str, Any]], *, drop_page_furniture: bool
) -> str:
    chunks: list[str] = []
    for cell in cells:
        category = str(cell.get("category", "")).strip()
        if drop_page_furniture and category in {"Page-header", "Page-footer"}:
            continue

        text = cell.get("text", "")
        if not isinstance(text, str):
            text = str(text)

        if category == "Picture":
            continue
        if category == "Formula":
            text = get_formula_in_markdown(text)
        else:
            text = clean_text(text)

        if text:
            chunks.append(text)

    return "\n\n".join(chunks).strip()


def markdown_from_layout_response(
    response_text: str, *, drop_page_furniture: bool
) -> tuple[str, bool]:
    try:
        payload = load_json_from_response(response_text)
        cells = find_layout_cells(payload)
        if cells is None:
            raise ValueError("unable to find layout cells in parsed JSON")
        markdown = layout_cells_to_markdown(
            cells, drop_page_furniture=drop_page_furniture
        )
        if not markdown:
            return strip_single_fence(response_text), True
        return markdown, False
    except ValueError:
        return strip_single_fence(response_text), True


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
        if name in stack[::-1]:
            while stack and stack[-1] != name:
                stack.pop()
            if stack and stack[-1] == name:
                stack.pop()

    while stack:
        svg += f"</{stack.pop()}>"
    return svg


def extract_svg_from_response(response_text: str) -> tuple[str | None, bool]:
    cleaned = response_text.replace("svg:", "").strip()
    match = re.search(r"<svg[^>]*>.*?</svg>", cleaned, re.DOTALL)
    if match:
        return match.group(0), True
    match = re.search(r"<svg[^>]*>.*", cleaned, re.DOTALL)
    if match:
        return fix_svg(match.group(0)), True
    return None, False


def render_pdf_page(
    input_path: Path, page_index: int, dpi: int, max_page_pixels: int
) -> Image.Image:
    with fitz.open(input_path) as doc:
        page = doc.load_page(page_index)
        scale = dpi / 72.0
        page_pixels = page.rect.width * page.rect.height * scale * scale
        if page_pixels > max_page_pixels:
            scale = math.sqrt(max_page_pixels / (page.rect.width * page.rect.height))
        pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        return Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)


def default_markdown_output(input_path: Path) -> Path:
    return Path("md") / f"{input_path.stem}.dots.mocr.md"


def default_svg_dir(input_path: Path) -> Path:
    return Path("svg") / f"{input_path.stem}.dots.mocr"


def build_page_markdown(page_index: int, markdown: str) -> str:
    body = markdown.strip()
    if not body:
        body = "<!-- empty page -->"
    return f"<!-- page {page_index + 1} -->\n\n{body}"


def process_pdf_page(
    *,
    input_path: Path,
    page_index: int,
    svg_dir: Path,
    args: argparse.Namespace,
) -> PageResult:
    image = render_pdf_page(
        input_path=input_path,
        page_index=page_index,
        dpi=args.dpi,
        max_page_pixels=args.max_page_pixels,
    )

    md_response = call_chat_completion(
        api=args.api,
        model=args.model,
        image=image,
        prompt=args.prompt,
        temperature=args.temperature,
        top_p=args.top_p,
        max_completion_tokens=args.max_completion_tokens,
        timeout=args.timeout,
    )
    markdown, markdown_from_raw_response = markdown_from_layout_response(
        md_response,
        drop_page_furniture=args.drop_page_furniture,
    )

    svg_response = call_chat_completion(
        api=args.api,
        model=args.svg_model or args.model,
        image=image,
        prompt=args.svg_prompt.format(width=image.width, height=image.height),
        temperature=args.svg_temperature,
        top_p=args.svg_top_p,
        max_completion_tokens=args.svg_max_completion_tokens,
        timeout=args.timeout,
    )
    svg_content, has_svg = extract_svg_from_response(svg_response)

    svg_path = svg_dir / f"page_{page_index + 1:04d}.svg"
    svg_raw_path: Path | None = None
    if has_svg and svg_content is not None:
        svg_path.write_text(svg_content, encoding="utf-8")
    else:
        svg_path = None
        svg_raw_path = svg_dir / f"page_{page_index + 1:04d}.raw.txt"
        svg_raw_path.write_text(svg_response, encoding="utf-8")

    return PageResult(
        page_index=page_index,
        markdown=markdown,
        svg_path=svg_path,
        svg_raw_path=svg_raw_path,
        markdown_from_raw_response=markdown_from_raw_response,
    )


def run_with_args(args: argparse.Namespace) -> int:
    input_path = Path(args.input).resolve()
    if input_path.suffix.lower() != ".pdf":
        raise ValueError(
            f"only PDF input is supported, got {input_path.suffix or '<no suffix>'}"
        )
    if not input_path.is_file():
        raise ValueError(f"input PDF does not exist: {input_path}")
    if args.concurrency < 1:
        raise ValueError("--concurrency must be >= 1")
    if args.dpi < 36:
        raise ValueError("--dpi must be >= 36")

    output_md = (
        Path(args.output).resolve()
        if args.output
        else default_markdown_output(input_path).resolve()
    )
    svg_dir = (
        Path(args.svg_dir).resolve()
        if args.svg_dir
        else default_svg_dir(input_path).resolve()
    )
    output_md.parent.mkdir(parents=True, exist_ok=True)
    svg_dir.mkdir(parents=True, exist_ok=True)

    with fitz.open(input_path) as doc:
        total_pages = doc.page_count
    if total_pages < 1:
        raise RuntimeError("input PDF has no pages")

    start = time.time()
    results: list[PageResult] = []
    max_workers = min(args.concurrency, total_pages)

    logging.info("[dots.mocr] input=%s", input_path)
    logging.info("[dots.mocr] pages=%s concurrency=%s", total_pages, max_workers)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(
                process_pdf_page,
                input_path=input_path,
                page_index=page_index,
                svg_dir=svg_dir,
                args=args,
            ): page_index
            for page_index in range(total_pages)
        }
        for future in as_completed(future_map):
            page_index = future_map[future]
            result = future.result()
            results.append(result)
            logging.info("[dots.mocr] page=%s/%s complete", page_index + 1, total_pages)

    results.sort(key=lambda item: item.page_index)
    markdown = "\n\n".join(
        build_page_markdown(result.page_index, result.markdown) for result in results
    ).strip()
    output_md.write_text(f"{markdown}\n", encoding="utf-8")

    raw_markdown_pages = sum(result.markdown_from_raw_response for result in results)
    missing_svg_pages = [
        result.page_index + 1 for result in results if result.svg_path is None
    ]
    elapsed = time.time() - start

    logging.info("[dots.mocr] markdown=%s", output_md)
    logging.info("[dots.mocr] svg_dir=%s", svg_dir)
    logging.info(
        "[dots.mocr] raw_markdown_pages=%s total_time=%.2fs",
        raw_markdown_pages,
        elapsed,
    )

    if missing_svg_pages:
        pages = ", ".join(str(page) for page in missing_svg_pages)
        raise RuntimeError(
            "failed to extract SVG on page(s) "
            f"{pages}; raw responses were saved under {svg_dir}"
        )

    return 0


def configure_logging(verbose: int) -> None:
    level = logging.DEBUG if verbose > 1 else logging.INFO
    logging.basicConfig(level=level, format=LOG_FORMAT)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Reference CLI for dots.mocr-style PDF parsing over an OpenAI-compatible "
            "chat/completions endpoint, with combined Markdown and per-page SVG output."
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
        help="Combined output markdown path. Default: md/<stem>.dots.mocr.md",
    )
    parser.add_argument(
        "--svg-dir",
        help="Directory for per-page SVG output. Default: svg/<stem>.dots.mocr",
    )
    parser.add_argument(
        "--api",
        default=DEFAULT_API,
        help=f"OpenAI-compatible chat/completions endpoint. Default: {DEFAULT_API}",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Model name used for Markdown/layout extraction. Default: {DEFAULT_MODEL}",
    )
    parser.add_argument(
        "--svg-model",
        default=None,
        help="Optional model name used for SVG generation. Default: reuse --model.",
    )
    parser.add_argument(
        "--prompt",
        default=DEFAULT_MD_PROMPT,
        help="Prompt used for Markdown/layout extraction.",
    )
    parser.add_argument(
        "--svg-prompt",
        default=DEFAULT_SVG_PROMPT_TEMPLATE,
        help="SVG prompt template. Supports {width} and {height}.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help=f"Per-request timeout in seconds. Default: {DEFAULT_TIMEOUT}",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=DEFAULT_CONCURRENCY,
        help=f"Concurrent PDF pages to process. Default: {DEFAULT_CONCURRENCY}",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=DEFAULT_DPI,
        help=f"Page render DPI before API inference. Default: {DEFAULT_DPI}",
    )
    parser.add_argument(
        "--max-page-pixels",
        type=int,
        default=DEFAULT_MAX_PAGE_PIXELS,
        help=f"Clamp rendered page pixels before API inference. Default: {DEFAULT_MAX_PAGE_PIXELS}",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.1,
        help="Sampling temperature for Markdown/layout extraction. Default: 0.1",
    )
    parser.add_argument(
        "--top-p",
        type=float,
        default=0.9,
        help="Top-p for Markdown/layout extraction. Default: 0.9",
    )
    parser.add_argument(
        "--max-completion-tokens",
        type=int,
        default=DEFAULT_MAX_COMPLETION_TOKENS,
        help=f"Max completion tokens for Markdown/layout extraction. Default: {DEFAULT_MAX_COMPLETION_TOKENS}",
    )
    parser.add_argument(
        "--svg-temperature",
        type=float,
        default=0.9,
        help="Sampling temperature for SVG generation. Default: 0.9",
    )
    parser.add_argument(
        "--svg-top-p",
        type=float,
        default=1.0,
        help="Top-p for SVG generation. Default: 1.0",
    )
    parser.add_argument(
        "--svg-max-completion-tokens",
        type=int,
        default=DEFAULT_MAX_COMPLETION_TOKENS,
        help=f"Max completion tokens for SVG generation. Default: {DEFAULT_MAX_COMPLETION_TOKENS}",
    )
    parser.add_argument(
        "--drop-page-furniture",
        action="store_true",
        help="Drop Page-header and Page-footer items from the combined Markdown output.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="Set the verbosity level. -v for info, -vv for debug.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    configure_logging(args.verbose)
    try:
        return run_with_args(args)
    except ValueError as exc:
        logging.error("%s", exc)
        return 1
    except RuntimeError as exc:
        logging.error("%s", exc)
        return 2
    except requests.RequestException as exc:
        logging.error("request failed: %s", exc)
        return 3
    except KeyboardInterrupt:
        logging.warning("Interrupted")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
