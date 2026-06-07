from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from paper_xyz.parsing import extract_message_text
from paper_xyz.prompts import GUIDED_FRONT_MATTER_REGEX
from paper_xyz.types import RenderedPage, TokenUsage


@dataclass(frozen=True, slots=True)
class ChatRequestConfig:
    api_url: str
    model: str
    prompt: str
    max_tokens: int = 8000
    token_param: str = "max_tokens"
    temperature: float = 0.0
    top_p: float | None = None
    top_k: int | None = None
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    repetition_penalty: float | None = None
    guided_decoding: bool = False


def build_chat_payload(
    page: RenderedPage,
    config: ChatRequestConfig,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": config.model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": config.prompt},
                    {"type": "image_url", "image_url": {"url": page.data_uri}},
                ],
            }
        ],
        "temperature": config.temperature,
    }
    payload[config.token_param] = config.max_tokens

    if config.top_p is not None:
        payload["top_p"] = config.top_p
    if config.top_k is not None:
        payload["top_k"] = config.top_k
    if config.frequency_penalty:
        payload["frequency_penalty"] = config.frequency_penalty
    if config.presence_penalty:
        payload["presence_penalty"] = config.presence_penalty
    if config.repetition_penalty is not None:
        payload["repetition_penalty"] = config.repetition_penalty
    if config.guided_decoding:
        payload["guided_regex"] = GUIDED_FRONT_MATTER_REGEX

    return payload


async def request_chat_completion(
    client: httpx.AsyncClient,
    page: RenderedPage,
    config: ChatRequestConfig,
) -> tuple[str, TokenUsage]:
    response = await client.post(config.api_url, json=build_chat_payload(page, config))
    response.raise_for_status()
    data = response.json()

    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError(f"Page {page.page_index} response is missing choices")

    choice = choices[0]
    if not isinstance(choice, dict):
        raise ValueError(f"Page {page.page_index} response choice is invalid")

    message = choice.get("message")
    if not isinstance(message, dict):
        raise ValueError(f"Page {page.page_index} response is missing message")

    text = extract_message_text(message.get("content"))
    if not text.strip():
        raise ValueError(f"Page {page.page_index} response content is empty")

    finish_reason = choice.get("finish_reason")
    if finish_reason not in (None, "stop", "end_turn"):
        raise ValueError(
            f"Page {page.page_index} finish_reason={finish_reason} output_chars={len(text)}"
        )

    usage_data = data.get("usage") if isinstance(data.get("usage"), dict) else {}
    usage = TokenUsage(
        prompt_tokens=int(usage_data.get("prompt_tokens", 0) or 0),
        completion_tokens=int(usage_data.get("completion_tokens", 0) or 0),
    )
    return text, usage
