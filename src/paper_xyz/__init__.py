from __future__ import annotations

from paper_xyz.converter import (
    DEFAULT_API,
    DEFAULT_MODEL_SERVICE,
    ConversionConfig,
    ConversionStats,
    PdfToMarkdownConverter,
    build_document_markdown,
)
from paper_xyz.model_services import (
    ModelServiceProfile,
    get_model_service_profile,
    iter_model_service_profiles,
    supported_model_services,
)
from paper_xyz.prompts import DEFAULT_MARKDOWN_PROMPT
from paper_xyz.types import (
    ImageRenderProfile,
    PageMetadata,
    PageResult,
    RenderedPage,
    TokenUsage,
)

__all__ = [
    "ConversionConfig",
    "ConversionStats",
    "DEFAULT_API",
    "DEFAULT_MARKDOWN_PROMPT",
    "DEFAULT_MODEL_SERVICE",
    "ImageRenderProfile",
    "ModelServiceProfile",
    "PageMetadata",
    "PageResult",
    "PdfToMarkdownConverter",
    "RenderedPage",
    "TokenUsage",
    "build_document_markdown",
    "get_model_service_profile",
    "iter_model_service_profiles",
    "supported_model_services",
]
