from __future__ import annotations

import json
import re
from typing import Any

from bs4 import BeautifulSoup

from paper_xyz.types import PageMetadata, ResponseParser

FRONT_MATTER_RE = re.compile(
    r"\A\s*---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)(.*)\Z", re.DOTALL
)


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


def parse_page_response(
    text: str,
    *,
    response_parser: ResponseParser = "markdown",
) -> tuple[PageMetadata, str]:
    if response_parser == "markdown":
        return parse_markdown_response(text)
    if response_parser == "dots_layout_json":
        return parse_dots_layout_json_response(text)
    if response_parser == "chandra_html":
        return parse_chandra_html_response(text)
    if response_parser == "deepseek_markdown":
        return parse_deepseek_markdown_response(text)
    if response_parser == "svg":
        return parse_svg_response(text)
    raise ValueError(f"Unsupported response_parser: {response_parser}")


def parse_markdown_response(text: str) -> tuple[PageMetadata, str]:
    front_matter, markdown = split_front_matter(text)
    if front_matter is None:
        body = normalize_markdown_body(text)
        return default_metadata(body), body

    values = parse_simple_yaml_mapping(front_matter)
    metadata = PageMetadata(
        primary_language=parse_language(values.get("primary_language")),
        is_rotation_valid=parse_bool(values.get("is_rotation_valid"), default=True),
        rotation_correction=parse_rotation(values.get("rotation_correction")),
        is_table=parse_bool(values.get("is_table"), default=False),
        is_diagram=parse_bool(values.get("is_diagram"), default=False),
    )
    return metadata, normalize_markdown_body(markdown)


def parse_dots_layout_json_response(text: str) -> tuple[PageMetadata, str]:
    cells = extract_layout_cells(text)
    if cells is None:
        body = normalize_markdown_body(text)
        return default_metadata(body), body

    markdown = layout_cells_to_markdown(cells)
    return layout_metadata(cells), markdown


def parse_chandra_html_response(text: str) -> tuple[PageMetadata, str]:
    html = strip_outer_code_fence(text).strip()
    if not html:
        return default_metadata(""), ""

    soup = BeautifulSoup(html, "html.parser")
    metadata = chandra_html_metadata(soup)
    content_html = chandra_content_html(soup)
    if not content_html:
        return metadata, ""

    try:
        markdown = chandra_html_to_markdown(content_html)
    except Exception:
        markdown = normalize_markdown_body(content_html)

    if not markdown.strip():
        markdown = normalize_markdown_body(content_html)
    return metadata, normalize_markdown_body(markdown)


def parse_deepseek_markdown_response(text: str) -> tuple[PageMetadata, str]:
    body = clean_deepseek_markdown(text)
    return default_metadata(body), normalize_markdown_body(body)


def parse_svg_response(text: str) -> tuple[PageMetadata, str]:
    svg = extract_svg_fragment(text)
    body = svg if svg else normalize_markdown_body(text)
    return default_metadata(body), body


def clean_deepseek_markdown(text: str) -> str:
    body = text.replace("<\uff5cend\u2581of\u2581sentence\uff5c>", "")
    body = re.sub(
        r"<\|ref\|>(.*?)<\|/ref\|><\|det\|>(.*?)<\|/det\|>",
        replace_deepseek_ref,
        body,
        flags=re.DOTALL,
    )
    body = body.replace("\\coloneqq", ":=").replace("\\eqqcolon", "=:")
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body.strip()


def replace_deepseek_ref(match: re.Match[str]) -> str:
    label = match.group(1).strip().lower()
    if label == "image":
        return "\n![Picture](image.png)\n"
    return ""


def chandra_content_html(
    soup: Any,
    *,
    include_headers_footers: bool = False,
    include_images: bool = True,
) -> str:
    top_level_divs = soup.find_all("div", recursive=False)
    if not top_level_divs:
        return str(soup)

    chunks: list[str] = []
    for div in top_level_divs:
        label = str(div.get("data-label", "") or "").strip()

        if label == "Blank-Page":
            continue
        if not include_headers_footers and label in {"Page-Header", "Page-Footer"}:
            continue
        if not include_images and label in {"Image", "Figure"}:
            continue

        if label in {"Image", "Figure"}:
            for img in div.find_all("img"):
                if not img.get("src"):
                    img["src"] = ""
        else:
            for img in div.find_all("img"):
                if not img.get("src"):
                    img.decompose()

        strip_chandra_layout_attrs(div)
        chunk = str(div.decode_contents()).strip()
        if chunk:
            chunks.append(chunk)

    return "\n\n".join(chunks)


def strip_chandra_layout_attrs(node: Any) -> None:
    for attr in ("data-bbox", "data-label"):
        node.attrs.pop(attr, None)
    for tag in node.find_all(True):
        for attr in ("data-bbox", "data-label"):
            tag.attrs.pop(attr, None)


def chandra_html_to_markdown(html: str) -> str:
    from markdownify import MarkdownConverter

    class ChandraMarkdownConverter(MarkdownConverter):
        def convert_math(self, el: Any, text: str, parent_tags: Any) -> str:
            math = text.strip()
            if not math:
                return ""
            if el.has_attr("display") and el["display"] == "block":
                return f"\n\n$$\n{math}\n$$\n\n"
            return f" ${math}$ "

        def convert_table(self, el: Any, text: str, parent_tags: Any) -> str:
            return f"\n\n{el}\n\n"

    converter = ChandraMarkdownConverter(
        heading_style="ATX",
        bullets="-",
        escape_misc=False,
        escape_underscores=True,
        escape_asterisks=True,
    )
    return converter.convert(html).strip()


def chandra_html_metadata(soup: Any) -> PageMetadata:
    labels = [
        str(div.get("data-label", "") or "").strip()
        for div in soup.find_all("div", recursive=False)
    ]
    content_labels = [
        label
        for label in labels
        if label and label not in {"Page-Header", "Page-Footer", "Blank-Page"}
    ]
    table_count = sum(label == "Table" for label in content_labels)
    diagram_count = sum(
        label in {"Image", "Figure", "Diagram"} for label in content_labels
    )
    content_count = len(content_labels)
    is_table = table_count > 0 and table_count >= max(1, content_count // 2)
    is_diagram = diagram_count > 0 and diagram_count >= max(1, content_count // 2)
    return PageMetadata(
        primary_language=None,
        is_rotation_valid=True,
        rotation_correction=0,
        is_table=is_table,
        is_diagram=is_diagram,
    )


def extract_layout_cells(text: str) -> list[dict[str, Any]] | None:
    payload = extract_json_payload(text)
    cells = layout_cells_from_json(payload) if payload is not None else None
    return cells if cells else None


def extract_json_payload(text: str) -> Any | None:
    candidate = strip_outer_code_fence(text).strip()
    if not candidate:
        return None

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    for index, char in enumerate(candidate):
        if char not in "[{":
            continue
        try:
            value, _ = decoder.raw_decode(candidate[index:])
        except json.JSONDecodeError:
            continue
        return value
    return None


def layout_cells_from_json(value: Any) -> list[dict[str, Any]] | None:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]

    if not isinstance(value, dict):
        return None

    if is_layout_cell(value):
        return [value]

    for key in (
        "cells",
        "layout",
        "layouts",
        "layout_info",
        "elements",
        "data",
        "result",
    ):
        nested = value.get(key)
        if isinstance(nested, list):
            cells = [item for item in nested if isinstance(item, dict)]
            if cells:
                return cells
        if isinstance(nested, dict):
            cells = layout_cells_from_json(nested)
            if cells:
                return cells
    return None


def is_layout_cell(value: dict[str, Any]) -> bool:
    return "category" in value or "bbox" in value or "text" in value


def layout_cells_to_markdown(cells: list[dict[str, Any]]) -> str:
    chunks: list[str] = []
    for cell in cells:
        category = str(cell.get("category", "") or "").strip()
        text = clean_cell_text(cell.get("text", cell.get("content", "")))

        if category == "Picture":
            svg = extract_svg_from_cell(cell)
            if svg:
                chunks.append(svg)
                continue

            placeholder = picture_placeholder(cell)
            if placeholder:
                chunks.append(placeholder)
            continue

        if category == "Formula" and text:
            chunks.append(format_formula_markdown(text))
            continue

        if text:
            chunks.append(text)

    return "\n\n".join(chunks).strip()


def extract_svg_from_cell(cell: dict[str, Any]) -> str | None:
    for key in (
        "svg",
        "svg_code",
        "image_svg",
        "picture_svg",
        "text",
        "content",
        "html",
        "markdown",
    ):
        svg = extract_svg_from_value(cell.get(key))
        if svg:
            return svg
    return None


def extract_svg_from_value(value: Any) -> str | None:
    if isinstance(value, str):
        return extract_svg_fragment(value)
    if isinstance(value, dict):
        for nested in value.values():
            svg = extract_svg_from_value(nested)
            if svg:
                return svg
    if isinstance(value, list):
        for item in value:
            svg = extract_svg_from_value(item)
            if svg:
                return svg
    return None


def extract_svg_fragment(text: str) -> str | None:
    candidate = strip_outer_code_fence(text).strip()
    if candidate.lower().startswith("svg:"):
        candidate = candidate[4:].strip()

    full_match = re.search(r"<svg\b[^>]*>.*?</svg>", candidate, re.DOTALL | re.I)
    if full_match:
        return full_match.group(0).strip()

    partial_match = re.search(r"<svg\b[^>]*>.*", candidate, re.DOTALL | re.I)
    if partial_match:
        return close_svg_fragment(partial_match.group(0)).strip()
    return None


def close_svg_fragment(svg: str) -> str:
    tag_names = re.findall(r"<([a-zA-Z][\w:-]*)\b[^>/]*>", svg)
    closed_names = re.findall(r"</([a-zA-Z][\w:-]*)\s*>", svg)
    if not tag_names or tag_names[0].lower() != "svg":
        return svg

    open_stack = [name for name in tag_names]
    for name in closed_names:
        lower_name = name.lower()
        while open_stack and open_stack[-1].lower() != lower_name:
            open_stack.pop()
        if open_stack:
            open_stack.pop()

    while open_stack:
        svg += f"</{open_stack.pop()}>"
    return svg


def clean_cell_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.startswith("`$") and text.endswith("$`"):
        text = text[1:-1]
    return text


def picture_placeholder(cell: dict[str, Any]) -> str | None:
    bbox = parse_bbox(cell.get("bbox"))
    if bbox is None:
        return "![Picture](image.png)"

    x1, y1, x2, y2 = bbox
    width = max(0, x2 - x1)
    height = max(0, y2 - y1)
    return f"![Picture](page_{x1}_{y1}_{width}_{height}.png)"


def parse_bbox(value: Any) -> tuple[int, int, int, int] | None:
    if not isinstance(value, list) or len(value) != 4:
        return None
    try:
        x1, y1, x2, y2 = (int(float(coord)) for coord in value)
    except (TypeError, ValueError):
        return None
    return x1, y1, x2, y2


def format_formula_markdown(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return ""
    if stripped.startswith("$$") and stripped.endswith("$$"):
        return stripped
    if stripped.startswith("\\[") and stripped.endswith("\\]"):
        return f"$$\n{stripped[2:-2].strip()}\n$$"
    if re.search(r"\$[^$\n]+?\$", stripped) or re.search(r"\\\(.*?\\\)", stripped):
        return stripped
    if "\\" in stripped:
        return f"$$\n{stripped}\n$$"
    return stripped


def layout_metadata(cells: list[dict[str, Any]]) -> PageMetadata:
    categories = [
        str(cell.get("category", "") or "").strip()
        for cell in cells
        if isinstance(cell, dict)
    ]
    content_categories = [
        category
        for category in categories
        if category and category not in {"Page-header", "Page-footer"}
    ]
    table_count = sum(category == "Table" for category in content_categories)
    picture_count = sum(category == "Picture" for category in content_categories)
    content_count = len(content_categories)
    is_table = table_count > 0 and table_count >= max(1, content_count // 2)
    is_diagram = picture_count > 0 and picture_count >= max(1, content_count // 2)
    return PageMetadata(
        primary_language=None,
        is_rotation_valid=True,
        rotation_correction=0,
        is_table=is_table,
        is_diagram=is_diagram,
    )


def split_front_matter(text: str) -> tuple[str | None, str]:
    match = FRONT_MATTER_RE.match(text)
    if not match:
        return None, text
    return match.group(1), match.group(2)


def parse_simple_yaml_mapping(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition(":")
        if not separator:
            continue
        values[key.strip()] = value.strip().strip("'\"")
    return values


def parse_language(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized or normalized.lower() in {"null", "none", "false"}:
        return None
    return normalized[:16]


def parse_bool(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"true", "yes", "1"}:
        return True
    if normalized in {"false", "no", "0", "null", "none"}:
        return False
    return default


def parse_rotation(value: str | None) -> int:
    if value is None:
        return 0
    match = re.search(r"\d+", value)
    if not match:
        return 0
    rotation = int(match.group(0)) % 360
    return rotation if rotation in {0, 90, 180, 270} else 0


def normalize_markdown_body(text: str) -> str:
    body = strip_outer_code_fence(text).strip()
    return "" if body.lower() == "null" else body


def strip_outer_code_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return text

    lines = stripped.splitlines()
    if len(lines) >= 2 and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1])
    return text


def default_metadata(markdown: str) -> PageMetadata:
    return PageMetadata(
        primary_language=None,
        is_rotation_valid=True,
        rotation_correction=0,
        is_table=False,
        is_diagram=False,
    )
