#!/usr/bin/env python3
"""docling reference CLI script, VLM API mode only.

Examples:
  pixi run -e default python agent/docling_rerf.py agent/demo.pdf -o md/demo.docling.md
  pixi run -e default python agent/docling_rerf.py agent/demo.pdf -o md/demo.docling.md --concurrency 10
  pixi run -e default python agent/docling_rerf.py --list-presets

Notes:
  Default args works with `agent/llama-serve.sh`
"""

from __future__ import annotations

import argparse
import gc
import logging
import time
from pathlib import Path

from docling.datamodel import stage_model_specs
from docling.datamodel.base_models import ConversionStatus, InputFormat
from docling.datamodel.pipeline_options import VlmConvertOptions, VlmPipelineOptions
from docling.datamodel.pipeline_options_vlm_model import ResponseFormat
from docling.datamodel.vlm_engine_options import ApiVlmEngineOptions, VlmEngineType
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.pipeline.vlm_pipeline import VlmPipeline

HELP_EPILOG = "\n".join((__doc__ or "").strip().splitlines()[2:]).strip()
DEFAULT_PROMPT = "Parse this document and convert it into standard markdown format."
DEFAULT_API = "http://127.0.0.1:11235/v1/chat/completions"
LOG_FORMAT = "%(asctime)s\t%(levelname)s\t%(name)s: %(message)s"


def register_presets(args: argparse.Namespace):
    llama_cpp = stage_model_specs.StageModelPreset(
        preset_id="llama_cpp",
        name="llama_cpp",
        description=("works with llama-serve api."),
        model_spec=stage_model_specs.VlmModelSpec(
            name="llama_cpp",
            default_repo_id="None",
            prompt=args.prompt,
            response_format=ResponseFormat.MARKDOWN,
            supported_engines={
                VlmEngineType.API,
            },
            api_overrides={
                VlmEngineType.API: stage_model_specs.ApiModelConfig(
                    params={"model": None},
                ),
            },
        ),
        default_engine_type=VlmEngineType.API,
        # TODO: tune params
        scale=args.scale,
        max_size=args.max_size,
        stage_options={
            "batch_size": 1,
            "force_backend_text": False,
        },
    )
    VlmConvertOptions.register_preset(llama_cpp)

    # TODO: add a custom gemini/gpt preset


def run_with_args(args: argparse.Namespace) -> int:
    register_presets(args)

    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    engine_options = ApiVlmEngineOptions(
        engine_type=VlmEngineType.API,
        url=args.api,
        timeout=args.timeout,
        concurrency=args.concurrency,
    )

    vlm_options = VlmConvertOptions.from_preset(
        args.preset,
        engine_options=engine_options,
    )

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

    logging.info("[docling] input=%s", input_path)
    logging.info("[docling] output=%s", output_path)
    logging.info("[docling] chars=%s total_time=%.2fs", len(markdown), elapsed)
    return 0


def configure_logging(verbose: int) -> None:
    if verbose <= 1:
        logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    else:
        logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)


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
        default="llama_cpp",
    )
    parser.add_argument(
        "--api",
        default=DEFAULT_API,
    )
    parser.add_argument(
        "--model",
        default=None,
    )
    parser.add_argument(
        "--timeout",
        default=120.0,
    )
    parser.add_argument(
        "--concurrency",
        default=5,
    )
    parser.add_argument(
        "--prompt",
        default=DEFAULT_PROMPT,
    )
    parser.add_argument(
        "--scale",
        default=2.0,
    )
    parser.add_argument(
        "--max-size",
        type=int,
        default=None,
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="Set the verbosity level. -v for info logging, -vv for debug logging.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    configure_logging(args.verbose)
    try:
        return run_with_args(args)
    except ValueError as exc:
        logging.error("%s", exc)
        return 1
    except RuntimeError as exc:
        logging.error("%s", exc)
        return 2
    except KeyboardInterrupt:
        logging.warning("Interrupted")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
