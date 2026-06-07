from __future__ import annotations

import base64
from pathlib import Path

import pymupdf

from paper_xyz.types import RenderedPage


def get_page_count(pdf_path: str | Path) -> int:
    document = pymupdf.open(pdf_path)
    try:
        return document.page_count
    finally:
        document.close()


def resolve_page_range(
    *,
    page_count: int,
    start_page: int,
    end_page: int | None,
) -> tuple[int, int]:
    if page_count < 1:
        raise ValueError("Input PDF has no pages")

    resolved_end_page = page_count - 1 if end_page is None else end_page

    if start_page < 0:
        raise ValueError("start_page must be >= 0")
    if resolved_end_page < 0:
        raise ValueError("end_page must be >= 0")
    if start_page > resolved_end_page:
        raise ValueError("start_page must be <= end_page")
    if start_page >= page_count:
        raise ValueError(
            f"start_page {start_page} is out of bounds, valid range is 0..{page_count - 1}"
        )
    if resolved_end_page >= page_count:
        raise ValueError(
            f"end_page {resolved_end_page} is out of bounds, valid range is 0..{page_count - 1}"
        )

    return start_page, resolved_end_page


def render_page_png(
    pdf_path: str | Path,
    page_index: int,
    *,
    target_longest_image_dim: int,
    rotation: int = 0,
) -> RenderedPage:
    if target_longest_image_dim < 1:
        raise ValueError("target_longest_image_dim must be >= 1")
    if rotation not in {0, 90, 180, 270}:
        raise ValueError("rotation must be one of 0, 90, 180, or 270")

    document = pymupdf.open(pdf_path)
    try:
        page = document.load_page(page_index)
        longest_page_dim = max(page.rect.width, page.rect.height)
        scale = target_longest_image_dim / longest_page_dim
        matrix = pymupdf.Matrix(scale, scale).prerotate(rotation)
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        png_bytes = pixmap.tobytes("png")
        return RenderedPage(
            page_index=page_index,
            image_base64=base64.b64encode(png_bytes).decode("ascii"),
            width=pixmap.width,
            height=pixmap.height,
            rotation=rotation,
        )
    finally:
        document.close()
