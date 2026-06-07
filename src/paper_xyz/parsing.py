from __future__ import annotations

import re
from typing import Any

from paper_xyz.types import PageMetadata

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


def parse_page_response(text: str) -> tuple[PageMetadata, str]:
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
