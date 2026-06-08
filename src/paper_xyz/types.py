from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ResponseParser = Literal["markdown", "dots_layout_json", "chandra_html", "svg"]


@dataclass(frozen=True, slots=True)
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0


@dataclass(frozen=True, slots=True)
class RenderedPage:
    page_index: int
    image_base64: str
    width: int
    height: int
    rotation: int

    @property
    def data_uri(self) -> str:
        return f"data:image/png;base64,{self.image_base64}"


@dataclass(frozen=True, slots=True)
class PageMetadata:
    primary_language: str | None
    is_rotation_valid: bool
    rotation_correction: int
    is_table: bool
    is_diagram: bool

    def __post_init__(self) -> None:
        if self.rotation_correction not in {0, 90, 180, 270}:
            raise ValueError("rotation_correction must be one of 0, 90, 180, or 270")


@dataclass(slots=True)
class PageResult:
    page_index: int
    metadata: PageMetadata
    markdown: str
    raw_response: str
    usage: TokenUsage
    attempts: int
    applied_rotation: int
    image_width: int
    image_height: int
