from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any

import requests

from paper_xyz._types import ApiVlmEngineOptions


@dataclass(slots=True)
class ApiMarkdownResponse:
    text: str
    total_tokens: int | None = None
    finish_reason: str | None = None
    model: str | None = None


def _compact_dict(payload: dict[str, Any]) -> dict[str, Any]:
    compacted: dict[str, Any] = {}
    for key, value in payload.items():
        if value is None:
            continue
        if isinstance(value, dict):
            compacted[key] = _compact_dict(value)
            continue
        compacted[key] = value
    return compacted


def _extract_text_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks: list[str] = []
        for item in content:
            if isinstance(item, str):
                chunks.append(item)
                continue
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if isinstance(text, str):
                chunks.append(text)
        return "".join(chunks)
    if isinstance(content, dict):
        text = content.get("text")
        if isinstance(text, str):
            return text
    return ""


def _strip_outer_markdown_fence(text: str) -> str:
    stripped = text.strip()
    lines = stripped.splitlines()
    if len(lines) < 2:
        return stripped
    first_line = lines[0].strip().lower()
    last_line = lines[-1].strip()
    if last_line != "```":
        return stripped
    if first_line not in {"```", "```md", "```markdown"}:
        return stripped
    return "\n".join(lines[1:-1]).strip()


def request_markdown(
    png_bytes: bytes,
    *,
    prompt: str,
    engine_options: ApiVlmEngineOptions,
    params: dict[str, Any],
) -> ApiMarkdownResponse:
    image_base64 = base64.b64encode(png_bytes).decode("utf-8")
    payload = _compact_dict(
        {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                }
            ],
            **params,
        }
    )
    response = requests.post(
        engine_options.url,
        headers=engine_options.headers,
        json=payload,
        timeout=engine_options.timeout,
    )
    if not response.ok:
        body = response.text.strip()
        raise RuntimeError(
            f"VLM API request failed with status={response.status_code}: {body[:1000]}"
        )
    data = response.json()
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("VLM API response does not contain any choices.")
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise RuntimeError("VLM API response choice has an unexpected shape.")
    message = first_choice.get("message") or {}
    if not isinstance(message, dict):
        raise RuntimeError("VLM API response message has an unexpected shape.")
    text = _extract_text_content(message.get("content"))
    usage = data.get("usage") or {}
    total_tokens = usage.get("total_tokens") if isinstance(usage, dict) else None
    return ApiMarkdownResponse(
        text=_strip_outer_markdown_fence(text),
        total_tokens=total_tokens if isinstance(total_tokens, int) else None,
        finish_reason=first_choice.get("finish_reason")
        if isinstance(first_choice.get("finish_reason"), str)
        else None,
        model=data.get("model") if isinstance(data.get("model"), str) else None,
    )
