from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path

import httpx

from paper_xyz.api import ChatRequestConfig, request_chat_completion
from paper_xyz.model_services import get_model_service_profile
from paper_xyz.parsing import parse_page_response
from paper_xyz.pdf import render_page_image
from paper_xyz.types import ImageRenderProfile, PageResult, ResponseParser

logger = logging.getLogger(__name__)

DEFAULT_API = "http://127.0.0.1:11235/v1/chat/completions"
DEFAULT_MODEL_SERVICE = "zai-org/GLM-OCR"


@dataclass(frozen=True, slots=True)
class ConversionConfig:
    api_url: str = DEFAULT_API
    model_service: str = DEFAULT_MODEL_SERVICE
    api_key: str | None = None
    timeout: float = 120.0
    concurrency: int = 4
    max_page_retries: int = 8

    def __post_init__(self) -> None:
        request_config = self.to_chat_request_config()
        if self.concurrency < 1:
            raise ValueError("concurrency must be >= 1")
        if self.max_page_retries < 1:
            raise ValueError("max_page_retries must be >= 1")
        if request_config.max_tokens < 1:
            raise ValueError("max_tokens must be >= 1")
        self.image_render_profile()

    def to_chat_request_config(self) -> ChatRequestConfig:
        profile = get_model_service_profile(self.model_service)
        return ChatRequestConfig(
            api_url=self.api_url,
            model=profile.model,
            prompt=profile.prompt,
            max_tokens=profile.max_tokens,
            token_param=profile.token_param,
            temperature=profile.temperature,
            top_p=profile.top_p,
            top_k=profile.top_k,
            repetition_penalty=profile.repetition_penalty,
            extra_body=dict(profile.extra_body),
            image_first=profile.image_first,
            text_prefix=profile.text_prefix,
            accepted_finish_reasons=profile.accepted_finish_reasons,
        )

    def response_parser(self) -> ResponseParser:
        return get_model_service_profile(self.model_service).response_parser

    def image_render_profile(self) -> ImageRenderProfile:
        return get_model_service_profile(self.model_service).render_profile()


@dataclass(frozen=True, slots=True)
class ConversionStats:
    pages: int
    chars: int
    prompt_tokens: int
    completion_tokens: int


class PdfToMarkdownConverter:
    def __init__(self, config: ConversionConfig) -> None:
        self.config = config

    async def convert(
        self,
        pdf_path: str | Path,
        *,
        start_page: int,
        end_page: int,
    ) -> tuple[str, list[PageResult]]:
        semaphore = asyncio.Semaphore(self.config.concurrency)
        headers = (
            {"Authorization": f"Bearer {self.config.api_key}"}
            if self.config.api_key
            else None
        )
        limits = httpx.Limits(
            max_connections=self.config.concurrency,
            max_keepalive_connections=self.config.concurrency,
        )

        async with httpx.AsyncClient(
            headers=headers,
            limits=limits,
            timeout=httpx.Timeout(self.config.timeout),
        ) as client:

            async def run_page(page_index: int) -> PageResult:
                async with semaphore:
                    return await self.convert_page(client, Path(pdf_path), page_index)

            page_results = await asyncio.gather(
                *[
                    asyncio.create_task(run_page(page_index))
                    for page_index in range(start_page, end_page + 1)
                ]
            )

        return build_document_markdown(page_results), page_results

    async def convert_page(
        self,
        client: httpx.AsyncClient,
        pdf_path: Path,
        page_index: int,
    ) -> PageResult:
        last_result: PageResult | None = None
        last_error: Exception | None = None
        cumulative_rotation = 0
        request_config = self._request_config()
        response_parser = self.config.response_parser()

        for attempt in range(1, self.config.max_page_retries + 1):
            try:
                rendered_page = await asyncio.to_thread(
                    render_page_image,
                    pdf_path,
                    page_index,
                    profile=self.config.image_render_profile(),
                    rotation=cumulative_rotation,
                )
                logger.info(
                    "page=%s attempt=%s requesting model=%s image=%sx%s mime=%s rotation=%s",
                    page_index,
                    attempt,
                    request_config.model,
                    rendered_page.width,
                    rendered_page.height,
                    rendered_page.image_mime_type,
                    cumulative_rotation,
                )
                raw_response, usage = await request_chat_completion(
                    client, rendered_page, request_config
                )
                metadata, markdown = parse_page_response(
                    raw_response,
                    response_parser=response_parser,
                )
                result = PageResult(
                    page_index=page_index,
                    metadata=metadata,
                    markdown=markdown,
                    raw_response=raw_response,
                    usage=usage,
                    attempts=attempt,
                    applied_rotation=cumulative_rotation,
                    image_width=rendered_page.width,
                    image_height=rendered_page.height,
                )
                last_result = result

                if metadata.is_rotation_valid:
                    logger.info(
                        "page=%s attempts=%s prompt_tokens=%s completion_tokens=%s rotation=%s",
                        page_index,
                        attempt,
                        usage.prompt_tokens,
                        usage.completion_tokens,
                        cumulative_rotation,
                    )
                    return result

                correction = metadata.rotation_correction % 360
                cumulative_rotation = (cumulative_rotation + correction) % 360
                logger.info(
                    "page=%s attempt=%s requested rotation retry, correction=%s next_rotation=%s",
                    page_index,
                    attempt,
                    correction,
                    cumulative_rotation,
                )
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                logger.warning(
                    "page=%s attempt=%s failed: %s",
                    page_index,
                    attempt,
                    format_exception(exc),
                )

            if attempt < self.config.max_page_retries:
                await asyncio.sleep(min(2 ** (attempt - 1), 8))

        if last_result is not None:
            logger.warning(
                "page=%s exhausted retries, keeping last rotation-invalid response",
                page_index,
            )
            return last_result

        raise RuntimeError(
            f"conversion failed for page {page_index}: {format_exception(last_error)}"
        )

    def _request_config(self) -> ChatRequestConfig:
        return self.config.to_chat_request_config()


def build_document_markdown(page_results: list[PageResult]) -> str:
    chunks = [
        page.markdown.rstrip()
        for page in sorted(page_results, key=lambda result: result.page_index)
        if page.markdown.strip()
    ]
    markdown = "\n\n".join(chunks).strip()
    return f"{markdown}\n" if markdown else ""


def format_exception(exc: Exception | None) -> str:
    if exc is None:
        return "unknown error"
    message = str(exc).strip()
    return f"{type(exc).__name__}: {message}" if message else type(exc).__name__


def summarize_results(markdown: str, page_results: list[PageResult]) -> ConversionStats:
    return ConversionStats(
        pages=len(page_results),
        chars=len(markdown),
        prompt_tokens=sum(page.usage.prompt_tokens for page in page_results),
        completion_tokens=sum(page.usage.completion_tokens for page in page_results),
    )
