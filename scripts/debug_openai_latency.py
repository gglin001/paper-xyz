#!/usr/bin/env python3
"""Measure OpenAI API latency with simple repeated requests.

Examples:
  pixi run -e default python scripts/debug_openai_latency.py
  pixi run -e default python scripts/debug_openai_latency.py --runs 10 --model gpt-5.2
  pixi run -e default python scripts/debug_openai_latency.py --api responses --model gpt-5.2
  pixi run -e default python scripts/debug_openai_latency.py --api chat.completions --model gpt-5.2
"""

from __future__ import annotations

import argparse
import os
import re
import statistics
import sys
import time

import httpx
from openai import OpenAI


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test OpenAI API latency.")
    parser.add_argument(
        "--api-base",
        default=os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:11235/v1"),
    )
    parser.add_argument(
        "--api",
        choices=("responses", "chat.completions"),
        default=os.getenv("OPENAI_API", "responses"),
    )
    parser.add_argument(
        "--model",
        default=os.getenv("OPENAI_MODEL", "gpt-5.2"),
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=5,
    )
    parser.add_argument(
        "--prompt",
        default="Reply with OK only.",
    )
    parser.add_argument(
        "--max-output-tokens",
        type=int,
        default=16,
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-request details.",
    )
    parser.add_argument(
        "--use-env-proxy",
        action="store_true",
        help=(
            "Respect HTTP(S)_PROXY and ALL_PROXY from environment. "
            "Default is off to avoid noisy proxy-related errors."
        ),
    )
    return parser.parse_args()


def one_line_error(exc: Exception) -> str:
    """Format an exception into a short single-line message."""
    message = " ".join(str(exc).strip().split()) or exc.__class__.__name__
    lower_message = message.lower()
    if "<!doctype html" in lower_message or "<html" in lower_message:
        title_match = re.search(r"<title>([^<]+)</title>", message, flags=re.IGNORECASE)
        code_match = re.search(r"error code\s*(\d{3})", message, flags=re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else "HTML error page"
        code = code_match.group(1) if code_match else None
        if code:
            message = (
                f"Remote server returned HTML error page, HTTP {code}, title={title}"
            )
        else:
            message = f"Remote server returned HTML error page, title={title}"
    if len(message) > 220:
        message = f"{message[:217]}..."
    return message


def send_one_request(client: OpenAI, args: argparse.Namespace) -> None:
    if args.api == "responses":
        client.responses.create(
            model=args.model,
            input=args.prompt,
            max_output_tokens=args.max_output_tokens,
        )
        return

    client.chat.completions.create(
        model=args.model,
        messages=[{"role": "user", "content": args.prompt}],
        max_completion_tokens=args.max_output_tokens,
    )


def main() -> None:
    args = parse_args()

    if args.runs <= 0:
        print("Error: --runs must be > 0", file=sys.stderr)
        raise SystemExit(2)

    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY is not set.", file=sys.stderr)
        raise SystemExit(2)

    base_url = args.api_base
    try:
        http_client = httpx.Client(trust_env=args.use_env_proxy)
        client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=base_url,
            http_client=http_client,
        )
    except Exception as exc:
        message = one_line_error(exc)
        print(f"Error: failed to initialize OpenAI client. {message}", file=sys.stderr)
        if "socksio" in message.lower():
            print(
                "Hint: SOCKS proxy detected. Install socksio/httpx[socks], "
                "or rerun without --use-env-proxy.",
                file=sys.stderr,
            )
        raise SystemExit(1)

    latencies_ms: list[float] = []
    success_count = 0
    failed_count = 0
    first_error: str | None = None

    print(
        f"api={args.api} model={args.model} runs={args.runs} max_output_tokens={args.max_output_tokens}"
    )
    if base_url:
        print(f"base_url={base_url}")
    print(f"use_env_proxy={args.use_env_proxy}")

    try:
        for i in range(1, args.runs + 1):
            start = time.perf_counter()
            try:
                send_one_request(client, args)
            except Exception as exc:
                elapsed_ms = (time.perf_counter() - start) * 1000
                failed_count += 1
                if first_error is None:
                    first_error = one_line_error(exc)
                if args.verbose:
                    print(
                        f"run={i} status=failed latency_ms={elapsed_ms:.1f} error={one_line_error(exc)}"
                    )
                continue

            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies_ms.append(elapsed_ms)
            success_count += 1
            if args.verbose:
                print(f"run={i} status=ok latency_ms={elapsed_ms:.1f}")
    finally:
        http_client.close()

    print(f"success={success_count}/{args.runs}")
    if failed_count:
        print(f"failed={failed_count}/{args.runs}")
    if first_error:
        print(f"first_error={first_error}")

    if not latencies_ms:
        print("Error: no successful request.", file=sys.stderr)
        raise SystemExit(1)

    print(
        "latency_ms "
        f"min={min(latencies_ms):.1f} "
        f"avg={statistics.mean(latencies_ms):.1f} "
        f"median={statistics.median(latencies_ms):.1f} "
        f"max={max(latencies_ms):.1f}"
    )


if __name__ == "__main__":
    main()
