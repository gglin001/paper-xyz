#!/usr/bin/env python3
"""docling reference CLI script, VLM API mode only.

Examples:
  pixi run -e docling python agent/docling_rerf.py agent/demo.pdf -o md/demo.docling.md
  pixi run -e docling python agent/docling_rerf.py --list-presets

Notes:
  - Default endpoint is http://127.0.0.1:11235/v1/chat/completions (from scripts/llama-serve.sh).
  - Default preset is granite_vision, because markdown-style VLMs work best with llama-server OCR models.
"""

from __future__ import annotations

import argparse
import gc
import json
import sys
import time
from pathlib import Path

from docling.datamodel.base_models import ConversionStatus, InputFormat
from docling.datamodel.pipeline_options import VlmConvertOptions, VlmPipelineOptions
from docling.datamodel.vlm_engine_options import ApiVlmEngineOptions, VlmEngineType
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.pipeline.vlm_pipeline import VlmPipeline

HELP_EPILOG = "\n".join((__doc__ or "").strip().splitlines()[2:]).strip()
DEFAULT_PROMPT = "Parse this document and convert it into standard markdown format."
DEFAULT_API = "http://127.0.0.1:11235/v1/chat/completions"


# TODO: use `VlmConvertOptions.register_preset` like:
# VlmConvertOptions.register_preset(stage_model_specs.VLM_CONVERT_GEMMA_27B)
def build_vlm_options(args: argparse.Namespace, api_url: str, model_id: str):
    engine_options = ApiVlmEngineOptions(
        engine_type=VlmEngineType.API,
        url=api_url,
        params={"model": model_id},
        timeout=args.timeout,
        concurrency=args.concurrency,
    )
    vlm_options = VlmConvertOptions.from_preset(
        args.preset,
        engine_options=engine_options,
    )

    if args.prompt:
        vlm_options.model_spec.prompt = args.prompt
    if args.scale is not None:
        vlm_options.scale = args.scale
    if args.max_size is not None:
        vlm_options.max_size = args.max_size

    return vlm_options


def run_with_args(args: argparse.Namespace) -> int:
    if args.list_presets:
        print(json.dumps(VlmConvertOptions.get_preset_info(), indent=2))
        return 0

    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    vlm_options = build_vlm_options(args, args.api, args.model)
    pipeline_options = VlmPipelineOptions(
        vlm_options=vlm_options,
        enable_remote_services=True,
    )

    converter: DocumentConverter | None = None
    start = time.time()
    try:
        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_cls=VlmPipeline,
                    pipeline_options=pipeline_options,
                )
            }
        )
        result = converter.convert(input_path)
        markdown = result.document.export_to_markdown()
    finally:
        # Avoid noisy __del__ logging errors during Python shutdown.
        if converter is not None:
            del converter
        gc.collect()

    if result.status != ConversionStatus.SUCCESS:
        raise RuntimeError(f"docling conversion failed, status={result.status}")

    output_path.write_text(markdown, encoding="utf-8")
    elapsed = time.time() - start

    print(f"[docling] input={input_path}")
    print(f"[docling] output={output_path}")
    print(f"[docling] chars={len(markdown)} total_time={elapsed:.2f}s")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Reference CLI for docling VLM API runtime. "
            "Designed for local OpenAI-compatible servers like llama-server."
        ),
        epilog=HELP_EPILOG or None,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Input PDF path. Example: agent/demo.pdf.",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output markdown path.",
    )
    parser.add_argument(
        "--preset",
        choices=tuple(VlmConvertOptions.list_preset_ids()),
        default="granite_vision",
        help=("Docling VLM preset. Default: granite_vision. "),
    )
    parser.add_argument(
        "--api",
        default=DEFAULT_API,
        help=(f"OpenAI-compatible API base URL or endpoint. Default: {DEFAULT_API}."),
    )
    parser.add_argument(
        "--model",
        default=None,
        help=("Model id sent to the API. Default: None."),
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="HTTP timeout seconds for each request. Default: 120.",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="Concurrent API requests in Docling runtime. Default: 1.",
    )
    parser.add_argument(
        "--prompt",
        default=DEFAULT_PROMPT,
        help="Override the preset prompt.",
    )
    parser.add_argument(
        "--scale",
        type=float,
        help="Override image scale used by the VLM stage.",
    )
    parser.add_argument(
        "--max-size",
        type=int,
        help="Override max image dimension sent to the VLM.",
    )
    parser.add_argument(
        "--list-presets",
        action="store_true",
        help="Print available VLM preset ids and exit.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        return run_with_args(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
