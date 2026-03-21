from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from paper_xyz._api import request_markdown
from paper_xyz._pdf import RenderedPdfPage, render_pdf_pages
from paper_xyz._types import (
    ConversionResult,
    ConversionStatus,
    MarkdownDocument,
    MarkdownPage,
    ResponseFormat,
    VlmConvertOptions,
    VlmPipelineOptions,
)


class VlmPipeline:
    def __init__(self, pipeline_options: VlmPipelineOptions):
        self.pipeline_options = pipeline_options

    @classmethod
    def get_default_options(cls) -> VlmPipelineOptions:
        presets = VlmConvertOptions.list_presets()
        if not presets:
            raise ValueError("No VLM presets are registered for paper_xyz.")
        return VlmPipelineOptions(
            vlm_options=VlmConvertOptions.from_preset(presets[0].preset_id),
            enable_remote_services=True,
        )

    def convert_pdf(self, pdf_path: Path) -> ConversionResult:
        if not self.pipeline_options.enable_remote_services:
            raise RuntimeError(
                "paper_xyz requires `enable_remote_services=True` for API-based VLM conversion."
            )

        vlm_options = self.pipeline_options.vlm_options
        if vlm_options.model_spec.response_format != ResponseFormat.MARKDOWN:
            raise NotImplementedError(
                f"Unsupported response format: {vlm_options.model_spec.response_format}"
            )

        rendered_pages = render_pdf_pages(
            pdf_path,
            scale=vlm_options.scale,
            max_size=vlm_options.max_size,
        )
        api_params = vlm_options.resolved_api_params()
        engine_options = vlm_options.engine_options
        converted_pages: list[MarkdownPage | None] = [None] * len(rendered_pages)
        errors: list[str] = []

        def convert_page(page: RenderedPdfPage) -> MarkdownPage:
            response = request_markdown(
                page.png_bytes,
                prompt=vlm_options.model_spec.prompt,
                engine_options=engine_options,
                params=api_params,
            )
            return MarkdownPage(
                page_no=page.page_no,
                markdown=response.text,
                token_count=response.total_tokens,
            )

        with ThreadPoolExecutor(max_workers=engine_options.concurrency) as executor:
            future_to_index = {
                executor.submit(convert_page, page): index
                for index, page in enumerate(rendered_pages)
            }
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                page_no = rendered_pages[index].page_no
                try:
                    converted_pages[index] = future.result()
                except Exception as exc:
                    errors.append(f"page {page_no}: {exc}")

        pages = [page for page in converted_pages if page is not None]
        status = (
            ConversionStatus.SUCCESS if not errors else ConversionStatus.PARTIAL_SUCCESS
        )
        if not pages:
            status = ConversionStatus.FAILURE

        return ConversionResult(
            status=status,
            document=MarkdownDocument(
                pages=pages,
                source=pdf_path,
                metadata={"page_count": len(rendered_pages)},
            ),
            errors=errors,
            metadata={"source": str(pdf_path), "page_count": len(rendered_pages)},
        )
