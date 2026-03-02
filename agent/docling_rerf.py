#!/usr/bin/env python3
"""docling reference CLI script, VLM API mode only.

Examples:
  pixi run -e docling python agent/docling_rerf.py agent/demo.pdf -o md/demo.docling.md
  pixi run -e docling python agent/docling_rerf.py pdf/paper.pdf -o md/paper.docling.md --model GLM-OCR-Q8_0.gguf
  pixi run -e docling python agent/docling_rerf.py --list-presets

Notes:
  - Default endpoint is http://127.0.0.1:11235 (from scripts/llama-serve.sh).
  - Default preset is granite_vision, because markdown-style VLMs work best with llama-server OCR models.
"""

from __future__ import annotations

import argparse
import gc
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from docling.datamodel.base_models import ConversionStatus, InputFormat
from docling.datamodel.pipeline_options import VlmConvertOptions, VlmPipelineOptions
from docling.datamodel.vlm_engine_options import ApiVlmEngineOptions, VlmEngineType
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.pipeline.vlm_pipeline import VlmPipeline

HELP_EPILOG = "\n".join((__doc__ or "").strip().splitlines()[2:]).strip()
PRESET_IDS = tuple(VlmConvertOptions.list_preset_ids())
DEFAULT_PRESET = "granite_vision" if "granite_vision" in PRESET_IDS else PRESET_IDS[0]
DEFAULT_API_BASE = "http://127.0.0.1:11235"


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
        choices=PRESET_IDS,
        default=DEFAULT_PRESET,
        help=(
            "Docling VLM preset. Default: granite_vision. "
            "Use markdown-style presets when serving OCR models via llama-server."
        ),
    )
    parser.add_argument(
        "--api-base",
        default=DEFAULT_API_BASE,
        help=(
            f"OpenAI-compatible API base URL or endpoint. Default: {DEFAULT_API_BASE}."
        ),
    )
    parser.add_argument(
        "--model",
        help=(
            "Model id sent to the API. "
            "If omitted, the script tries to auto-detect from /v1/models."
        ),
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
    parser.add_argument(
        "--print-config",
        action="store_true",
        help="Print effective runtime config as JSON.",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.list_presets:
        return

    if not args.input:
        raise ValueError("input is required unless --list-presets is set")
    if not args.output:
        raise ValueError("--output is required unless --list-presets is set")

    input_path = Path(args.input)
    if not input_path.exists():
        raise ValueError(f"Input file not found: {input_path}")
    if input_path.suffix.lower() != ".pdf":
        raise ValueError(f"Input must be a PDF file: {input_path}")

    if args.timeout <= 0:
        raise ValueError("--timeout must be > 0")
    if args.concurrency <= 0:
        raise ValueError("--concurrency must be > 0")
    if args.scale is not None and args.scale <= 0:
        raise ValueError("--scale must be > 0")
    if args.max_size is not None and args.max_size <= 0:
        raise ValueError("--max-size must be > 0")


def ensure_url(value: str) -> str:
    raw = value.strip()
    if not raw:
        raise ValueError("API URL is empty")
    if "://" not in raw:
        raw = f"http://{raw}"

    parsed = urllib.parse.urlsplit(raw)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Invalid API URL: {value}")
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def normalize_chat_completions_url(api_base: str) -> str:
    normalized = ensure_url(api_base)
    parsed = urllib.parse.urlsplit(normalized)
    path = parsed.path.rstrip("/")

    if path.endswith("/v1/chat/completions"):
        chat_path = path
    elif path.endswith("/chat/completions"):
        chat_path = path
    elif path.endswith("/v1"):
        chat_path = f"{path}/chat/completions"
    else:
        chat_path = f"{path}/v1/chat/completions" if path else "/v1/chat/completions"

    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, chat_path, "", ""))


def normalize_models_url(api_base: str) -> str:
    normalized = ensure_url(api_base)
    parsed = urllib.parse.urlsplit(normalized)
    path = parsed.path.rstrip("/")

    if path.endswith("/v1/models"):
        models_path = path
    elif path.endswith("/v1/chat/completions"):
        models_path = path[: -len("/chat/completions")] + "/models"
    elif path.endswith("/chat/completions"):
        models_path = path[: -len("/chat/completions")] + "/models"
    elif path.endswith("/v1"):
        models_path = f"{path}/models"
    else:
        models_path = f"{path}/v1/models" if path else "/v1/models"

    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, models_path, "", ""))


def extract_model_ids(payload: dict[str, Any]) -> list[str]:
    ids: list[str] = []

    def push(model_id: Any) -> None:
        if not isinstance(model_id, str):
            return
        cleaned = model_id.strip()
        if cleaned and cleaned not in ids:
            ids.append(cleaned)

    for item in payload.get("data", []):
        if isinstance(item, dict):
            push(item.get("id"))
            push(item.get("model"))
            push(item.get("name"))

    for item in payload.get("models", []):
        if isinstance(item, dict):
            push(item.get("id"))
            push(item.get("model"))
            push(item.get("name"))

    return ids


def detect_first_model_id(api_base: str, timeout: float) -> str | None:
    models_url = normalize_models_url(api_base)
    request = urllib.request.Request(models_url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.URLError:
        return None
    except TimeoutError:
        return None

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return None

    model_ids = extract_model_ids(payload)
    return model_ids[0] if model_ids else None


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

    api_url = normalize_chat_completions_url(args.api_base)
    model_id = args.model or detect_first_model_id(args.api_base, args.timeout)
    if not model_id:
        raise ValueError(
            "Cannot detect model id from API. "
            "Please provide --model explicitly, e.g. --model GLM-OCR-Q8_0.gguf."
        )

    vlm_options = build_vlm_options(args, api_url, model_id)
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

    if args.print_config:
        cfg = {
            "input": str(input_path),
            "output": str(output_path),
            "preset": args.preset,
            "api_url": api_url,
            "model": model_id,
            "timeout": args.timeout,
            "concurrency": args.concurrency,
            "scale": vlm_options.scale,
            "max_size": vlm_options.max_size,
            "prompt": vlm_options.model_spec.prompt,
            "response_format": vlm_options.model_spec.response_format.value,
        }
        print(json.dumps(cfg, indent=2, ensure_ascii=False))

    print(f"[docling] preset={args.preset} model={model_id}")
    print(f"[docling] api={api_url}")
    print(f"[docling] input={input_path}")
    print(f"[docling] output={output_path}")
    print(f"[docling] chars={len(markdown)} total_time={elapsed:.2f}s")
    return 0


def main() -> int:
    args = parse_args()
    try:
        validate_args(args)
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
