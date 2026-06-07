from __future__ import annotations

import json
import re
from typing import Any

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
