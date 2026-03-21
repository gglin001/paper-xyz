from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz


@dataclass(slots=True)
class RenderedPdfPage:
    page_no: int
    width: int
    height: int
    png_bytes: bytes


def _effective_scale(
    page: fitz.Page, requested_scale: float, max_size: int | None
) -> float:
    if max_size is None:
        return requested_scale
    page_rect = page.rect
    largest_edge = max(page_rect.width, page_rect.height)
    if largest_edge <= 0:
        return requested_scale
    return min(requested_scale, max_size / largest_edge)


def render_pdf_pages(
    pdf_path: Path,
    *,
    scale: float,
    max_size: int | None,
) -> list[RenderedPdfPage]:
    rendered_pages: list[RenderedPdfPage] = []
    with fitz.open(pdf_path) as document:
        if document.page_count == 0:
            raise ValueError(f"PDF has no pages: {pdf_path}")
        for page_index in range(document.page_count):
            page = document.load_page(page_index)
            effective_scale = _effective_scale(page, scale, max_size)
            matrix = fitz.Matrix(effective_scale, effective_scale)
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            rendered_pages.append(
                RenderedPdfPage(
                    page_no=page_index + 1,
                    width=pixmap.width,
                    height=pixmap.height,
                    png_bytes=pixmap.tobytes("png"),
                )
            )
    return rendered_pages
