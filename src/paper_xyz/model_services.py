from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from paper_xyz.prompts import (
    CHANDRA_OCR_LAYOUT_PROMPT,
    DEEPSEEK_OCR_MARKDOWN_PROMPT,
    DEFAULT_MARKDOWN_PROMPT,
    DOTS_LAYOUT_JSON_PROMPT,
    FIRERED_OCR_MARKDOWN_PROMPT,
    GLM_OCR_MARKDOWN_PROMPT,
)
from paper_xyz.types import ResponseParser

TokenParam = Literal["max_tokens", "max_completion_tokens"]


@dataclass(frozen=True, slots=True)
class ModelServiceProfile:
    name: str
    description: str
    model: str
    prompt: str = DEFAULT_MARKDOWN_PROMPT
    response_parser: ResponseParser = "markdown"
    max_tokens: int = 8000
    token_param: TokenParam = "max_tokens"
    temperature: float | None = 0.0
    top_p: float | None = None
    top_k: int | None = None
    repetition_penalty: float | None = None
    image_first: bool = True
    text_prefix: str = ""
    target_longest_image_dim: int = 1288


MODEL_SERVICE_PROFILES: dict[str, ModelServiceProfile] = {
    "zai-org/GLM-OCR": ModelServiceProfile(
        name="zai-org/GLM-OCR",
        description="GLM-OCR OpenAI-compatible VLM service defaults.",
        model="zai-org/GLM-OCR",
        prompt=GLM_OCR_MARKDOWN_PROMPT,
        response_parser="markdown",
        max_tokens=16384,
        temperature=0.01,
        top_p=0.00001,
        top_k=1,
        repetition_penalty=1.1,
    ),
    "rednote-hilab/dots.mocr": ModelServiceProfile(
        name="rednote-hilab/dots.mocr",
        description="dots.mocr OpenAI-compatible VLM service defaults.",
        model="rednote-hilab/dots.mocr",
        prompt=DOTS_LAYOUT_JSON_PROMPT,
        response_parser="dots_layout_json",
        max_tokens=32768,
        token_param="max_completion_tokens",
        temperature=0.1,
        top_p=0.9,
        text_prefix="<|img|><|imgpad|><|endofimg|>",
    ),
    "rednote-hilab/dots.ocr-1.5": ModelServiceProfile(
        name="rednote-hilab/dots.ocr-1.5",
        description="dots.ocr 1.5 OpenAI-compatible VLM service defaults.",
        model="rednote-hilab/dots.ocr-1.5",
        prompt=DOTS_LAYOUT_JSON_PROMPT,
        response_parser="dots_layout_json",
        max_tokens=32768,
        token_param="max_completion_tokens",
        temperature=0.1,
        top_p=0.9,
        text_prefix="<|img|><|imgpad|><|endofimg|>",
    ),
    "rednote-hilab/dots.ocr": ModelServiceProfile(
        name="rednote-hilab/dots.ocr",
        description="dots.ocr OpenAI-compatible VLM service defaults.",
        model="rednote-hilab/dots.ocr",
        prompt=DOTS_LAYOUT_JSON_PROMPT,
        response_parser="dots_layout_json",
        max_tokens=32768,
        token_param="max_completion_tokens",
        temperature=0.1,
        top_p=0.9,
        text_prefix="<|img|><|imgpad|><|endofimg|>",
    ),
    "deepseek-ai/DeepSeek-OCR": ModelServiceProfile(
        name="deepseek-ai/DeepSeek-OCR",
        description="DeepSeek-OCR OpenAI-compatible VLM service defaults.",
        model="deepseek-ai/DeepSeek-OCR",
        prompt=DEEPSEEK_OCR_MARKDOWN_PROMPT,
        response_parser="markdown",
        max_tokens=8192,
        temperature=0.0,
        text_prefix="<|grounding|>",
    ),
    "FireRedTeam/FireRed-OCR-2B": ModelServiceProfile(
        name="FireRedTeam/FireRed-OCR-2B",
        description="FireRed-OCR OpenAI-compatible VLM service defaults.",
        model="FireRedTeam/FireRed-OCR-2B",
        prompt=FIRERED_OCR_MARKDOWN_PROMPT,
        response_parser="markdown",
        max_tokens=8192,
        temperature=0.0,
    ),
    "datalab-to/chandra-ocr-2": ModelServiceProfile(
        name="datalab-to/chandra-ocr-2",
        description=(
            "Chandra OCR 2 vLLM service defaults from third_party/chandra. "
            "The official vLLM launcher serves the model as 'chandra'."
        ),
        model="datalab-to/chandra-ocr-2",
        prompt=CHANDRA_OCR_LAYOUT_PROMPT,
        response_parser="chandra_html",
        max_tokens=12384,
        temperature=0.0,
        top_p=0.1,
        target_longest_image_dim=2240,
    ),
}

PROFILE_KEYS_BY_LOWER: dict[str, str] = {
    name.lower(): name for name in MODEL_SERVICE_PROFILES
}


def normalize_model_service_name(name: str) -> str:
    stripped = name.strip()
    return PROFILE_KEYS_BY_LOWER.get(stripped.lower(), stripped)


def get_model_service_profile(name: str) -> ModelServiceProfile:
    normalized = normalize_model_service_name(name)
    try:
        return MODEL_SERVICE_PROFILES[normalized]
    except KeyError as exc:
        supported = ", ".join(supported_model_services())
        raise ValueError(
            f"Unsupported model_service={name!r}. Supported: {supported}"
        ) from exc


def supported_model_services() -> tuple[str, ...]:
    return tuple(MODEL_SERVICE_PROFILES)


def iter_model_service_profiles() -> tuple[ModelServiceProfile, ...]:
    return tuple(MODEL_SERVICE_PROFILES.values())
