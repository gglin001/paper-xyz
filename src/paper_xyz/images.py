from __future__ import annotations

from pathlib import Path
from typing import Any

import pymupdf

from paper_xyz.types import ExtractedImage, ImageExtractionConfig


def extract_document_images(
    pdf_path: str | Path,
    output_markdown_path: str | Path,
    *,
    start_page: int,
    end_page: int,
    config: ImageExtractionConfig,
) -> dict[int, tuple[ExtractedImage, ...]]:
    if not config.enabled:
        return {}

    markdown_path = Path(output_markdown_path)
    if markdown_path.suffix.lower() != ".md":
        raise ValueError("output_markdown_path must end with .md")
    image_dir = markdown_path.with_suffix("")
    relative_dir = image_dir.relative_to(markdown_path.parent).as_posix()
    return extract_images_to_directory(
        pdf_path,
        image_dir,
        start_page=start_page,
        end_page=end_page,
        config=config,
        relative_path_prefix=relative_dir,
    )


def extract_images_to_directory(
    pdf_path: str | Path,
    output_dir: str | Path,
    *,
    start_page: int,
    end_page: int,
    config: ImageExtractionConfig,
    relative_path_prefix: str | None = None,
) -> dict[int, tuple[ExtractedImage, ...]]:
    if not config.enabled:
        return {}

    image_dir = Path(output_dir)
    image_dir.mkdir(parents=True, exist_ok=True)
    relative_dir = relative_path_prefix or image_dir.name
    images_by_page: dict[int, tuple[ExtractedImage, ...]] = {}

    with pymupdf.open(pdf_path) as document:
        for page_index in range(start_page, end_page + 1):
            page = document.load_page(page_index)
            image_infos = filtered_image_infos(page, config)
            extracted_images: list[ExtractedImage] = []

            for image_index, image_info in enumerate(image_infos, start=1):
                filename = f"page-{page_index + 1}-image-{image_index}.png"
                output_path = image_dir / filename
                save_image_as_png(document, page, image_info, output_path)

                extracted_images.append(
                    ExtractedImage(
                        page_index=page_index,
                        image_index=image_index,
                        relative_path=(
                            f"{relative_dir}/{filename}" if relative_dir else filename
                        ),
                        bbox=normalize_bbox(image_info["bbox"]),
                        width=int(image_info["width"]),
                        height=int(image_info["height"]),
                    )
                )

            images_by_page[page_index] = tuple(extracted_images)

    return images_by_page


def filtered_image_infos(
    page: pymupdf.Page,
    config: ImageExtractionConfig,
) -> list[dict[str, Any]]:
    smasks_by_xref = {
        int(image[0]): int(image[1])
        for image in page.get_images(full=True)
        if int(image[0]) > 0 and int(image[1]) > 0
    }
    candidates = []
    for raw_image_info in page.get_image_info(hashes=True, xrefs=True):
        if int(raw_image_info.get("width", 0)) < config.min_width:
            continue
        if int(raw_image_info.get("height", 0)) < config.min_height:
            continue

        image_info = dict(raw_image_info)
        image_info["smask"] = smasks_by_xref.get(int(image_info.get("xref", 0) or 0), 0)
        candidates.append(image_info)
    candidates.sort(key=image_reading_order)

    unique: list[dict[str, Any]] = []
    for candidate in candidates:
        if any(
            same_image_occurrence(candidate, previous, config.bbox_tolerance)
            for previous in unique
        ):
            continue
        unique.append(candidate)
    return unique


def image_reading_order(
    image_info: dict[str, Any],
) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = normalize_bbox(image_info["bbox"])
    return y0, x0, y1, x1


def same_image_occurrence(
    left: dict[str, Any],
    right: dict[str, Any],
    tolerance: float,
) -> bool:
    left_digest = left.get("digest")
    right_digest = right.get("digest")
    left_xref = int(left.get("xref", 0) or 0)
    right_xref = int(right.get("xref", 0) or 0)
    same_source = (
        left_digest is not None
        and right_digest is not None
        and left_digest == right_digest
    ) or (left_xref > 0 and left_xref == right_xref)
    if not same_source:
        return False

    return all(
        abs(left_coord - right_coord) <= tolerance
        for left_coord, right_coord in zip(
            normalize_bbox(left["bbox"]),
            normalize_bbox(right["bbox"]),
            strict=True,
        )
    )


def normalize_bbox(value: Any) -> tuple[float, float, float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise ValueError(f"Invalid image bbox: {value!r}")
    x0, y0, x1, y1 = value
    return float(x0), float(y0), float(x1), float(y1)


def save_image_as_png(
    document: pymupdf.Document,
    page: pymupdf.Page,
    image_info: dict[str, Any],
    output_path: Path,
) -> None:
    xref = int(image_info.get("xref", 0) or 0)
    if xref > 0:
        try:
            pixmap = pymupdf.Pixmap(document, xref)
            smask = int(image_info.get("smask", 0) or 0)
            if smask > 0:
                mask = pymupdf.Pixmap(document, smask)
                pixmap = pymupdf.Pixmap(pixmap, mask)
            if pixmap.colorspace is not None and pixmap.colorspace.n > 3:
                pixmap = pymupdf.Pixmap(pymupdf.csRGB, pixmap)
            pixmap.save(output_path)
            return
        except (RuntimeError, ValueError):
            pass

    bbox = pymupdf.Rect(normalize_bbox(image_info["bbox"]))
    pixmap = page.get_pixmap(clip=bbox, dpi=200, alpha=False)
    pixmap.save(output_path)
