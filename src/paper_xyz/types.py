from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ImageFormat = Literal["PNG", "JPEG", "WEBP"]
ResizeResample = Literal["bicubic", "lanczos"]
ResizeStrategy = Literal["smart", "chandra"]
ResponseParser = Literal[
    "markdown",
    "dots_layout_json",
    "chandra_html",
    "deepseek_markdown",
    "svg",
]


@dataclass(frozen=True, slots=True)
class ImageRenderProfile:
    render_dpi: float | None = None
    target_longest_dim: int | None = 1288
    max_longest_dim: int | None = None
    min_shortest_dim: int | None = None
    resize_factor: int | None = None
    min_pixels: int | None = None
    max_pixels: int | None = None
    pixel_count_factor: int = 1
    resize_strategy: ResizeStrategy = "smart"
    resample: ResizeResample = "bicubic"
    image_format: ImageFormat = "PNG"
    image_quality: int | None = None

    def __post_init__(self) -> None:
        if self.render_dpi is None and self.target_longest_dim is None:
            raise ValueError("render_dpi or target_longest_dim must be set")
        for field_name in (
            "render_dpi",
            "target_longest_dim",
            "max_longest_dim",
            "min_shortest_dim",
            "resize_factor",
            "min_pixels",
            "max_pixels",
        ):
            value = getattr(self, field_name)
            if value is not None and value <= 0:
                raise ValueError(f"{field_name} must be > 0")
        if self.pixel_count_factor < 1:
            raise ValueError("pixel_count_factor must be >= 1")
        if (
            self.min_pixels is not None
            and self.max_pixels is not None
            and self.min_pixels > self.max_pixels
        ):
            raise ValueError("min_pixels must be <= max_pixels")
        if self.image_quality is not None and not 1 <= self.image_quality <= 100:
            raise ValueError("image_quality must be between 1 and 100")


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
    image_mime_type: str = "image/png"

    @property
    def data_uri(self) -> str:
        return f"data:{self.image_mime_type};base64,{self.image_base64}"


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
    error: str | None = None
