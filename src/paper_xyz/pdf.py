from __future__ import annotations

import base64
import io
import math
from pathlib import Path

import pymupdf
from PIL import Image

from paper_xyz.types import ImageRenderProfile, RenderedPage

RESAMPLE_BY_NAME = {
    "bicubic": Image.Resampling.BICUBIC,
    "lanczos": Image.Resampling.LANCZOS,
}
MIME_TYPE_BY_IMAGE_FORMAT = {
    "PNG": "image/png",
    "JPEG": "image/jpeg",
    "WEBP": "image/webp",
}


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
    return render_page_image(
        pdf_path,
        page_index,
        profile=ImageRenderProfile(target_longest_dim=target_longest_image_dim),
        rotation=rotation,
    )


def render_page_image(
    pdf_path: str | Path,
    page_index: int,
    *,
    profile: ImageRenderProfile,
    rotation: int = 0,
) -> RenderedPage:
    if rotation not in {0, 90, 180, 270}:
        raise ValueError("rotation must be one of 0, 90, 180, or 270")

    document = pymupdf.open(pdf_path)
    try:
        page = document.load_page(page_index)
        scale = page_render_scale(page, profile)
        matrix = pymupdf.Matrix(scale, scale).prerotate(rotation)
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
        image = resize_image_for_profile(image, profile)
        image_bytes = encode_image(image, profile)
        return RenderedPage(
            page_index=page_index,
            image_base64=base64.b64encode(image_bytes).decode("ascii"),
            width=image.width,
            height=image.height,
            rotation=rotation,
            image_mime_type=MIME_TYPE_BY_IMAGE_FORMAT[profile.image_format],
        )
    finally:
        document.close()


def page_render_scale(page: pymupdf.Page, profile: ImageRenderProfile) -> float:
    page_width = page.rect.width
    page_height = page.rect.height
    if page_width <= 0 or page_height <= 0:
        raise ValueError("PDF page has invalid dimensions")

    if profile.render_dpi is not None:
        scale = profile.render_dpi / 72.0
    elif profile.target_longest_dim is not None:
        scale = profile.target_longest_dim / max(page_width, page_height)
    else:
        raise ValueError("render_dpi or target_longest_dim must be set")

    if profile.min_shortest_dim is not None:
        shortest_dim = min(page_width, page_height) * scale
        if shortest_dim < profile.min_shortest_dim:
            scale = profile.min_shortest_dim / min(page_width, page_height)

    if profile.max_longest_dim is not None:
        longest_dim = max(page_width, page_height) * scale
        if longest_dim > profile.max_longest_dim:
            scale = profile.max_longest_dim / max(page_width, page_height)

    return scale


def resize_image_for_profile(
    image: Image.Image, profile: ImageRenderProfile
) -> Image.Image:
    if (
        profile.resize_factor is None
        and profile.min_pixels is None
        and profile.max_pixels is None
    ):
        return image
    if profile.resize_factor is None:
        raise ValueError("resize_factor must be set when pixel bounds are used")

    if profile.resize_strategy == "chandra":
        width, height = chandra_resize_size(image, profile)
    else:
        width, height = smart_resize_size(image, profile)

    if (width, height) == image.size:
        return image
    return image.resize((width, height), RESAMPLE_BY_NAME[profile.resample])


def smart_resize_size(
    image: Image.Image, profile: ImageRenderProfile
) -> tuple[int, int]:
    factor = profile.resize_factor
    if factor is None:
        return image.size

    width, height = image.size
    width_bar = max(factor, round_by_factor(width, factor))
    height_bar = max(factor, round_by_factor(height, factor))

    if (
        profile.max_pixels is not None
        and profile.pixel_count_factor * width_bar * height_bar > profile.max_pixels
    ):
        beta = math.sqrt(
            (profile.pixel_count_factor * width * height) / profile.max_pixels
        )
        width_bar = max(factor, floor_by_factor(width / beta, factor))
        height_bar = max(factor, floor_by_factor(height / beta, factor))
    elif (
        profile.min_pixels is not None
        and profile.pixel_count_factor * width_bar * height_bar < profile.min_pixels
    ):
        beta = math.sqrt(
            profile.min_pixels / (profile.pixel_count_factor * width * height)
        )
        width_bar = ceil_by_factor(width * beta, factor)
        height_bar = ceil_by_factor(height * beta, factor)
        if (
            profile.max_pixels is not None
            and profile.pixel_count_factor * width_bar * height_bar > profile.max_pixels
        ):
            beta = math.sqrt(
                (profile.pixel_count_factor * width_bar * height_bar)
                / profile.max_pixels
            )
            width_bar = max(factor, floor_by_factor(width_bar / beta, factor))
            height_bar = max(factor, floor_by_factor(height_bar / beta, factor))

    return width_bar, height_bar


def chandra_resize_size(
    image: Image.Image, profile: ImageRenderProfile
) -> tuple[int, int]:
    factor = profile.resize_factor
    if factor is None:
        return image.size

    width, height = image.size
    if width <= 0 or height <= 0:
        return image.size

    current_pixels = width * height
    scale = 1.0
    if profile.max_pixels is not None and current_pixels > profile.max_pixels:
        scale = math.sqrt(profile.max_pixels / current_pixels)
    elif profile.min_pixels is not None and current_pixels < profile.min_pixels:
        scale = math.sqrt(profile.min_pixels / current_pixels)

    original_ar = width / height
    width_blocks = max(1, round((width * scale) / factor))
    height_blocks = max(1, round((height * scale) / factor))

    if profile.max_pixels is not None:
        while width_blocks * height_blocks * factor * factor > profile.max_pixels:
            if width_blocks == 1 and height_blocks == 1:
                break
            if width_blocks == 1:
                height_blocks -= 1
                continue
            if height_blocks == 1:
                width_blocks -= 1
                continue

            width_loss = abs(((width_blocks - 1) / height_blocks) - original_ar)
            height_loss = abs((width_blocks / (height_blocks - 1)) - original_ar)
            if width_loss < height_loss:
                width_blocks -= 1
            else:
                height_blocks -= 1

    return width_blocks * factor, height_blocks * factor


def encode_image(image: Image.Image, profile: ImageRenderProfile) -> bytes:
    image_format = profile.image_format
    if image_format == "JPEG" and image.mode != "RGB":
        image = image.convert("RGB")

    save_kwargs = {}
    if profile.image_quality is not None and image_format in {"JPEG", "WEBP"}:
        save_kwargs["quality"] = profile.image_quality

    buffer = io.BytesIO()
    image.save(buffer, format=image_format, **save_kwargs)
    return buffer.getvalue()


def round_by_factor(number: float, factor: int) -> int:
    return round(number / factor) * factor


def ceil_by_factor(number: float, factor: int) -> int:
    return math.ceil(number / factor) * factor


def floor_by_factor(number: float, factor: int) -> int:
    return math.floor(number / factor) * factor
