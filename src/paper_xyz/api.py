from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from paper_xyz.model_services import TokenParam
from paper_xyz.parsing import extract_message_text
from paper_xyz.types import RenderedPage, TokenUsage


@dataclass(frozen=True, slots=True)
class ChatRequestConfig:
    api_url: str
    model: str
    prompt: str
    max_tokens: int = 8000
    token_param: TokenParam = "max_tokens"
    temperature: float | None = 0.0
    top_p: float | None = None
    top_k: int | None = None
    repetition_penalty: float | None = None
    image_first: bool = True
    text_prefix: str = ""
    accepted_finish_reasons: tuple[str | None, ...] = (None, "stop", "end_turn")

    def prompt_for_page(self, page: RenderedPage) -> str:
        return self.prompt.replace("{width}", str(page.width)).replace(
            "{height}", str(page.height)
        )


def build_chat_payload(
    page: RenderedPage,
    config: ChatRequestConfig,
) -> dict[str, Any]:
    text_part = {
        "type": "text",
        "text": f"{config.text_prefix}{config.prompt_for_page(page)}",
    }
    image_part = {"type": "image_url", "image_url": {"url": page.data_uri}}
    if config.image_first:
        user_content = [image_part, text_part]
    else:
        user_content = [text_part, image_part]

    payload: dict[str, Any] = {
        "model": config.model,
        "messages": [{"role": "user", "content": user_content}],
    }
    payload[config.token_param] = config.max_tokens

    if config.temperature is not None:
        payload["temperature"] = config.temperature
    if config.top_p is not None:
        payload["top_p"] = config.top_p
    if config.top_k is not None:
        payload["top_k"] = config.top_k
    if config.repetition_penalty is not None:
        payload["repetition_penalty"] = config.repetition_penalty
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

    usage_data = data.get("usage") if isinstance(data.get("usage"), dict) else {}
    usage = TokenUsage(
        prompt_tokens=int(usage_data.get("prompt_tokens", 0) or 0),
        completion_tokens=int(usage_data.get("completion_tokens", 0) or 0),
    )

    finish_reason = choice.get("finish_reason")
    if finish_reason not in config.accepted_finish_reasons:
        raise ValueError(
            f"Page {page.page_index} finish_reason={finish_reason} "
            f"prompt_tokens={usage.prompt_tokens} "
            f"completion_tokens={usage.completion_tokens} output_chars={len(text)}"
        )
    return text, usage
