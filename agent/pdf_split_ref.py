#!/usr/bin/env python3
"""Reference PDF splitter using pypdf.

Use this helper to debug conversion pipelines on large PDFs.
Split a representative page subset first, then run converters on the smaller PDF.

Examples:
  pixi run -e default python agent/pdf_split_ref.py agent/demo.pdf --pages 1-2 -o debug_agent/demo.p1-2.pdf
  pixi run -e default python agent/pdf_split_ref.py agent/demo.pdf --pages 1,3,5-6 --per-page-dir debug_agent/demo_pages
  pixi run -e default python agent/pdf_split_ref.py agent/demo.pdf --pages 0-2 --zero-based -o debug_agent/demo.z0-2.pdf
"""

from __future__ import annotations

import argparse
from pathlib import Path

from pypdf import PdfReader, PdfWriter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Split PDF by page selectors. Selectors support N, A-B, A-, -B "
            "(inclusive ranges)."
        )
    )
    parser.add_argument("input_pdf", help="Input PDF path. Example: agent/demo.pdf.")
    parser.add_argument(
        "--pages",
        required=True,
        help=(
            "Page selector list, comma separated. Example: 1,3,5-7,10-. "
            "Use --zero-based to interpret indices from 0."
        ),
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help=(
            "Merged output PDF path. Default: debug_agent/<stem>.subset.pdf "
            "(unless --per-page-dir is set and --output is omitted)."
        ),
    )
    parser.add_argument(
        "--per-page-dir",
        default=None,
        help="Optional output directory for one PDF per selected page.",
    )
    parser.add_argument(
        "--zero-based",
        action="store_true",
        help="Interpret page indices as zero-based.",
    )
    parser.add_argument(
        "--password",
        default=None,
        help="Password for encrypted PDFs.",
    )
    return parser


def parse_positive_int(value: str, label: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:  # pragma: no cover - defensive validation branch.
        raise ValueError(f"Invalid {label}: {value}") from exc
    return parsed


def expand_selector(
    token: str,
    *,
    lower_bound: int,
    upper_bound: int,
) -> list[int]:
    if "-" not in token:
        value = parse_positive_int(token, "page number")
        return [value]

    start_raw, end_raw = token.split("-", 1)
    if not start_raw and not end_raw:
        raise ValueError("Empty range '-' is not allowed.")

    start = parse_positive_int(start_raw, "range start") if start_raw else lower_bound
    end = parse_positive_int(end_raw, "range end") if end_raw else upper_bound
    if start > end:
        raise ValueError(f"Range start > end: {token}")
    return list(range(start, end + 1))


def parse_pages_spec(spec: str, *, total_pages: int, zero_based: bool) -> list[int]:
    if total_pages <= 0:
        raise ValueError("Input PDF has no pages.")

    min_page = 0 if zero_based else 1
    max_page = total_pages - 1 if zero_based else total_pages
    seen: set[int] = set()
    resolved: list[int] = []

    tokens = [part.strip() for part in spec.split(",") if part.strip()]
    if not tokens:
        raise ValueError("No valid page selectors were provided.")

    for token in tokens:
        for page_number in expand_selector(
            token,
            lower_bound=min_page,
            upper_bound=max_page,
        ):
            if page_number < min_page or page_number > max_page:
                raise ValueError(
                    f"Page {page_number} out of bounds, valid range is "
                    f"{min_page}..{max_page}."
                )
            zero_index = page_number if zero_based else page_number - 1
            if zero_index not in seen:
                seen.add(zero_index)
                resolved.append(zero_index)
    return resolved


def write_subset_pdf(
    reader: PdfReader,
    page_indexes: list[int],
    output_path: Path,
) -> None:
    writer = PdfWriter()
    for index in page_indexes:
        writer.add_page(reader.pages[index])
    if reader.metadata:
        metadata = {
            k: str(v) for k, v in reader.metadata.items() if k and v is not None
        }
        if metadata:
            writer.add_metadata(metadata)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as handle:
        writer.write(handle)


def write_per_page_pdfs(
    reader: PdfReader,
    page_indexes: list[int],
    output_dir: Path,
    *,
    stem: str,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    total_digits = max(4, len(str(len(reader.pages))))
    outputs: list[Path] = []

    for index in page_indexes:
        page_number = index + 1
        output = output_dir / f"{stem}.p{page_number:0{total_digits}d}.pdf"
        writer = PdfWriter()
        writer.add_page(reader.pages[index])
        with output.open("wb") as handle:
            writer.write(handle)
        outputs.append(output)
    return outputs


def main() -> int:
    args = build_parser().parse_args()
    input_pdf = Path(args.input_pdf)
    if not input_pdf.exists():
        raise SystemExit(f"Input PDF not found: {input_pdf}")

    reader = PdfReader(str(input_pdf))
    if reader.is_encrypted:
        if not args.password:
            raise SystemExit("PDF is encrypted. Provide --password.")
        decrypt_status = reader.decrypt(args.password)
        if decrypt_status == 0:
            raise SystemExit("Incorrect password for encrypted PDF.")

    page_indexes = parse_pages_spec(
        args.pages,
        total_pages=len(reader.pages),
        zero_based=args.zero_based,
    )

    merged_output: Path | None = None
    if args.output:
        merged_output = Path(args.output)
    elif args.per_page_dir is None:
        merged_output = Path("debug_agent") / f"{input_pdf.stem}.subset.pdf"

    if merged_output is not None:
        write_subset_pdf(reader, page_indexes, merged_output)
        print(f"[pdf_split] merged output -> {merged_output}")

    if args.per_page_dir is not None:
        per_page_outputs = write_per_page_pdfs(
            reader,
            page_indexes,
            Path(args.per_page_dir),
            stem=input_pdf.stem,
        )
        print(f"[pdf_split] per-page output dir -> {args.per_page_dir}")
        for path in per_page_outputs:
            print(path)

    if merged_output is None and args.per_page_dir is None:
        raise SystemExit("Nothing to write, set --output and/or --per-page-dir.")

    print(
        f"[pdf_split] input={input_pdf} selected_pages={len(page_indexes)} "
        f"total_pages={len(reader.pages)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
