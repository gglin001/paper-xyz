from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from paper_xyz.prompts import DEFAULT_MARKDOWN_PROMPT

TokenParam = Literal["max_tokens", "max_completion_tokens"]
ImagePlacement = Literal["before_text", "after_text"]


@dataclass(frozen=True, slots=True)
class ModelServiceProfile:
    name: str
    description: str
    model: str
    prompt: str = DEFAULT_MARKDOWN_PROMPT
    max_tokens: int = 8000
    token_param: TokenParam = "max_tokens"
    temperature: float | None = 0.0
    top_p: float | None = None
    top_k: int | None = None
    frequency_penalty: float | None = None
    presence_penalty: float | None = None
    repetition_penalty: float | None = None
    image_placement: ImagePlacement = "after_text"
    text_prefix: str = ""
    text_suffix: str = ""
    system_prompt: str | None = None


MODEL_SERVICE_PROFILES: dict[str, ModelServiceProfile] = {
    "zai-org/GLM-OCR": ModelServiceProfile(
        name="zai-org/GLM-OCR",
        description="GLM-OCR OpenAI-compatible VLM service defaults.",
        model="zai-org/GLM-OCR",
        max_tokens=16384,
        temperature=0.01,
        top_p=0.00001,
        top_k=1,
        repetition_penalty=1.1,
        image_placement="before_text",
    ),
    "rednote-hilab/dots.mocr": ModelServiceProfile(
        name="rednote-hilab/dots.mocr",
        description="dots.mocr OpenAI-compatible VLM service defaults.",
        model="rednote-hilab/dots.mocr",
        max_tokens=32768,
        token_param="max_completion_tokens",
        temperature=0.1,
        top_p=0.9,
        image_placement="before_text",
        text_prefix="<|img|><|imgpad|><|endofimg|>",
    ),
    "rednote-hilab/dots.ocr-1.5": ModelServiceProfile(
        name="rednote-hilab/dots.ocr-1.5",
        description="dots.ocr 1.5 OpenAI-compatible VLM service defaults.",
        model="rednote-hilab/dots.ocr-1.5",
        max_tokens=32768,
        token_param="max_completion_tokens",
        temperature=0.1,
        top_p=0.9,
        image_placement="before_text",
        text_prefix="<|img|><|imgpad|><|endofimg|>",
    ),
    "rednote-hilab/dots.ocr": ModelServiceProfile(
        name="rednote-hilab/dots.ocr",
        description="dots.ocr OpenAI-compatible VLM service defaults.",
        model="rednote-hilab/dots.ocr",
        max_tokens=32768,
        token_param="max_completion_tokens",
        temperature=0.1,
        top_p=0.9,
        image_placement="before_text",
        text_prefix="<|img|><|imgpad|><|endofimg|>",
    ),
    "deepseek-ai/DeepSeek-OCR": ModelServiceProfile(
        name="deepseek-ai/DeepSeek-OCR",
        description="DeepSeek-OCR OpenAI-compatible VLM service defaults.",
        model="deepseek-ai/DeepSeek-OCR",
        max_tokens=8192,
        temperature=0.0,
        image_placement="before_text",
        text_prefix="<|grounding|>",
    ),
    "FireRedTeam/FireRed-OCR-2B": ModelServiceProfile(
        name="FireRedTeam/FireRed-OCR-2B",
        description="FireRed-OCR OpenAI-compatible VLM service defaults.",
        model="FireRedTeam/FireRed-OCR-2B",
        max_tokens=8192,
        temperature=0.0,
        image_placement="before_text",
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
