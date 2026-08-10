from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from pathlib import Path

import httpx

from paper_xyz.api import (
    ChatRequestConfig,
    NonRetryableChatResponseError,
    request_chat_completion,
)
from paper_xyz.images import extract_document_images
from paper_xyz.model_services import get_model_service_profile
from paper_xyz.parsing import parse_page_response
from paper_xyz.pdf import render_page_image
from paper_xyz.types import (
    ImageExtractionConfig,
    ImageRenderProfile,
    PageMetadata,
    PageResult,
    ResponseParser,
    TokenUsage,
)

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
    allow_page_failures: bool = True
    include_page_numbers: bool = False
    image_extraction: ImageExtractionConfig = ImageExtractionConfig()

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
    failed_pages: int
    chars: int
    prompt_tokens: int
    completion_tokens: int
    extracted_images: int = 0


class PdfToMarkdownConverter:
    def __init__(self, config: ConversionConfig) -> None:
        self.config = config

    async def convert(
        self,
        pdf_path: str | Path,
        *,
        start_page: int,
        end_page: int,
        output_path: str | Path | None = None,
    ) -> tuple[str, list[PageResult]]:
        if self.config.image_extraction.enabled:
            if output_path is None:
                raise ValueError(
                    "output_path is required when image extraction is enabled"
                )
            if Path(output_path).suffix.lower() != ".md":
                raise ValueError("output_path must end with .md")

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

        if self.config.image_extraction.enabled:
            assert output_path is not None
            images_by_page = await asyncio.to_thread(
                extract_document_images,
                pdf_path,
                output_path,
                start_page=start_page,
                end_page=end_page,
                config=self.config.image_extraction,
            )
            for page_result in page_results:
                page_result.extracted_images = images_by_page.get(
                    page_result.page_index, ()
                )

        return (
            build_document_markdown(
                page_results,
                include_page_numbers=self.config.include_page_numbers,
                resolve_images=self.config.image_extraction.enabled,
            ),
            page_results,
        )

    async def convert_page(
        self,
        client: httpx.AsyncClient,
        pdf_path: Path,
        page_index: int,
    ) -> PageResult:
        last_result: PageResult | None = None
        last_error: Exception | None = None
        last_image_width = 0
        last_image_height = 0
        last_usage = TokenUsage()
        attempts_used = 0
        cumulative_rotation = 0
        request_config = self._request_config()
        response_parser = self.config.response_parser()

        for attempt in range(1, self.config.max_page_retries + 1):
            attempts_used = attempt
            try:
                rendered_page = await asyncio.to_thread(
                    render_page_image,
                    pdf_path,
                    page_index,
                    profile=self.config.image_render_profile(),
                    rotation=cumulative_rotation,
                )
                last_image_width = rendered_page.width
                last_image_height = rendered_page.height
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
            except NonRetryableChatResponseError as exc:
                last_error = exc
                last_usage = exc.usage
                logger.warning(
                    "page=%s attempt=%s failed without retry: %s",
                    page_index,
                    attempt,
                    format_exception(exc),
                )
                break
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

        if self.config.allow_page_failures:
            error = format_exception(last_error)
            logger.error(
                "page=%s attempts=%s keeping failed-page placeholder: %s",
                page_index,
                attempts_used,
                error,
            )
            return build_failed_page_result(
                page_index=page_index,
                attempts=attempts_used,
                applied_rotation=cumulative_rotation,
                image_width=last_image_width,
                image_height=last_image_height,
                usage=last_usage,
                error=error,
            )

        raise RuntimeError(
            f"conversion failed for page {page_index}: {format_exception(last_error)}"
        )

    def _request_config(self) -> ChatRequestConfig:
        return self.config.to_chat_request_config()


MODEL_IMAGE_PLACEHOLDER_RE = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<target>[^)]*)\)")


def build_document_markdown(
    page_results: list[PageResult],
    *,
    include_page_numbers: bool = False,
    resolve_images: bool = False,
) -> str:
    chunks = []
    for page in sorted(page_results, key=lambda result: result.page_index):
        page_markdown = resolve_page_images(page) if resolve_images else page.markdown
        if include_page_numbers:
            page_marker = (
                "<!-- "
                f"paper_xyz: page_index={page.page_index} "
                f"pdf_page={page.page_index + 1}"
                " -->"
            )
            page_markdown = f"{page_marker}\n\n{page_markdown}".rstrip()
        if page_markdown.strip():
            chunks.append(page_markdown)

    markdown = "\n\n".join(chunks).strip()
    return f"{markdown}\n" if markdown else ""


def resolve_page_images(page: PageResult) -> str:
    markdown = page.markdown.rstrip()
    images = list(page.extracted_images)
    if not images:
        return remove_model_image_placeholders(markdown)

    next_image_index = 0

    def replace_placeholder(match: re.Match[str]) -> str:
        nonlocal next_image_index
        if not is_model_image_placeholder(match.group("target")):
            return match.group(0)
        if next_image_index >= len(images):
            return ""

        image = images[next_image_index]
        next_image_index += 1
        alt = normalized_image_alt(
            match.group("alt"), page.page_index, image.image_index
        )
        return f"![{alt}]({image.relative_path})"

    markdown = MODEL_IMAGE_PLACEHOLDER_RE.sub(replace_placeholder, markdown).rstrip()
    remaining_images = images[next_image_index:]
    if remaining_images:
        references = "\n\n".join(
            f"![Page {page.page_index + 1} image {image.image_index}]"
            f"({image.relative_path})"
            for image in remaining_images
        )
        markdown = f"{markdown}\n\n{references}".strip()
    return markdown


def remove_model_image_placeholders(markdown: str) -> str:
    def remove_placeholder(match: re.Match[str]) -> str:
        if is_model_image_placeholder(match.group("target")):
            return ""
        return match.group(0)

    return MODEL_IMAGE_PLACEHOLDER_RE.sub(remove_placeholder, markdown).rstrip()


def is_model_image_placeholder(target: str) -> bool:
    normalized = target.strip()
    return (
        not normalized
        or normalized == "image.png"
        or (normalized.startswith("page_") and normalized.endswith(".png"))
    )


def normalized_image_alt(alt: str, page_index: int, image_index: int) -> str:
    normalized = alt.strip()
    if normalized and normalized.lower() not in {"picture", "image"}:
        return normalized
    return f"Page {page_index + 1} image {image_index}"


def build_failed_page_result(
    *,
    page_index: int,
    attempts: int,
    applied_rotation: int,
    image_width: int,
    image_height: int,
    usage: TokenUsage,
    error: str,
) -> PageResult:
    return PageResult(
        page_index=page_index,
        metadata=PageMetadata(
            primary_language=None,
            is_rotation_valid=True,
            rotation_correction=0,
            is_table=False,
            is_diagram=False,
        ),
        markdown=failed_page_markdown(
            page_index=page_index,
            attempts=attempts,
            error=error,
        ),
        raw_response="",
        usage=usage,
        attempts=attempts,
        applied_rotation=applied_rotation,
        image_width=image_width,
        image_height=image_height,
        error=error,
    )


def failed_page_markdown(*, page_index: int, attempts: int, error: str) -> str:
    safe_error = " ".join(error.split()).replace("--", "- -")
    return (
        "<!-- "
        f"paper_xyz: page_index={page_index} pdf_page={page_index + 1} "
        f"conversion_failed_after_attempts={attempts} error={safe_error}"
        " -->"
    )


def format_exception(exc: Exception | None) -> str:
    if exc is None:
        return "unknown error"
    message = str(exc).strip()
    return f"{type(exc).__name__}: {message}" if message else type(exc).__name__


def summarize_results(markdown: str, page_results: list[PageResult]) -> ConversionStats:
    return ConversionStats(
        pages=len(page_results),
        failed_pages=sum(1 for page in page_results if page.error is not None),
        chars=len(markdown),
        prompt_tokens=sum(page.usage.prompt_tokens for page in page_results),
        completion_tokens=sum(page.usage.completion_tokens for page in page_results),
        extracted_images=sum(len(page.extracted_images) for page in page_results),
    )
