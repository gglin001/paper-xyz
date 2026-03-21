from __future__ import annotations

from pathlib import Path

from paper_xyz._types import (
    ApiModelConfig,
    ApiVlmEngineOptions,
    ConversionResult,
    ConversionStatus,
    InputFormat,
    MarkdownDocument,
    MarkdownPage,
    ResponseFormat,
    StageModelPreset,
    VlmConvertOptions,
    VlmEngineType,
    VlmModelSpec,
    VlmPipelineOptions,
)
from paper_xyz.document_converter import DocumentConverter, PdfFormatOption
from paper_xyz.pipeline.vlm_pipeline import VlmPipeline

__all__ = [
    "ApiModelConfig",
    "ApiVlmEngineOptions",
    "ConversionResult",
    "ConversionStatus",
    "DocumentConverter",
    "InputFormat",
    "MarkdownDocument",
    "MarkdownPage",
    "PdfFormatOption",
    "ResponseFormat",
    "StageModelPreset",
    "VlmConvertOptions",
    "VlmEngineType",
    "VlmModelSpec",
    "VlmPipeline",
    "VlmPipelineOptions",
    "convert_pdf",
]


def convert_pdf(
    source: str | Path,
    *,
    vlm_options: VlmConvertOptions,
    enable_remote_services: bool = True,
) -> ConversionResult:
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_cls=VlmPipeline,
                pipeline_options=VlmPipelineOptions(
                    vlm_options=vlm_options,
                    enable_remote_services=enable_remote_services,
                ),
            )
        }
    )
    return converter.convert(source)
