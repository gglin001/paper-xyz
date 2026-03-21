from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from paper_xyz._types import ConversionResult, InputFormat
from paper_xyz.pipeline.vlm_pipeline import VlmPipeline


@dataclass(slots=True)
class PdfFormatOption:
    pipeline_cls: type[VlmPipeline] = VlmPipeline
    pipeline_options: Any | None = None


class DocumentConverter:
    def __init__(
        self,
        *,
        allowed_formats: list[InputFormat] | None = None,
        format_options: dict[InputFormat, PdfFormatOption] | None = None,
    ) -> None:
        self.allowed_formats = allowed_formats or [InputFormat.PDF]
        self.format_options = format_options or {InputFormat.PDF: PdfFormatOption()}

    def convert(self, source: str | Path) -> ConversionResult:
        source_path = Path(source).expanduser().resolve()
        if not source_path.exists():
            raise FileNotFoundError(f"Input file not found: {source_path}")
        if source_path.suffix.lower() != ".pdf":
            raise ValueError(
                f"Unsupported input format for paper_xyz: {source_path.suffix}"
            )
        if InputFormat.PDF not in self.allowed_formats:
            raise ValueError("PDF input is not allowed by this DocumentConverter.")

        option = self.format_options.get(InputFormat.PDF)
        if option is None:
            raise ValueError("No PDF format option is configured.")

        pipeline_options = option.pipeline_options
        if pipeline_options is None:
            pipeline_options = option.pipeline_cls.get_default_options()

        pipeline = option.pipeline_cls(pipeline_options)
        return pipeline.convert_pdf(source_path)
