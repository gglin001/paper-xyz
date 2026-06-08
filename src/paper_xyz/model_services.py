from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from paper_xyz.prompts import (
    CHANDRA_OCR_LAYOUT_PROMPT,
    DEEPSEEK_OCR_MARKDOWN_PROMPT,
    DEFAULT_MARKDOWN_PROMPT,
    DOTS_IMAGE_TO_SVG_PROMPT,
    DOTS_LAYOUT_JSON_PROMPT,
    FIRERED_OCR_MARKDOWN_PROMPT,
    GLM_OCR_MARKDOWN_PROMPT,
)
from paper_xyz.types import ImageRenderProfile, ResponseParser

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
    extra_body: dict[str, Any] = field(default_factory=dict)
    image_first: bool = True
    text_prefix: str = ""
    target_longest_image_dim: int = 1288
    image_render_profile: ImageRenderProfile | None = None
    accepted_finish_reasons: tuple[str | None, ...] = (None, "stop", "end_turn")

    def render_profile(self) -> ImageRenderProfile:
        if self.image_render_profile is not None:
            return self.image_render_profile
        return ImageRenderProfile(target_longest_dim=self.target_longest_image_dim)


GLM_RENDER_PROFILE = ImageRenderProfile(
    render_dpi=200,
    target_longest_dim=None,
    max_longest_dim=3500,
    resize_factor=28,
    min_pixels=112 * 112,
    max_pixels=14 * 14 * 4 * 1280,
    pixel_count_factor=2,
    image_format="JPEG",
)

DOTS_RENDER_PROFILE = ImageRenderProfile(
    render_dpi=200,
    target_longest_dim=None,
    max_longest_dim=4500,
    image_format="PNG",
)

DEEPSEEK_RENDER_PROFILE = ImageRenderProfile(
    render_dpi=144,
    target_longest_dim=None,
    image_format="PNG",
)

FIRERED_RENDER_PROFILE = ImageRenderProfile(
    render_dpi=200,
    target_longest_dim=None,
    max_longest_dim=3500,
    image_format="PNG",
)

CHANDRA_RENDER_PROFILE = ImageRenderProfile(
    render_dpi=192,
    target_longest_dim=None,
    min_shortest_dim=1024,
    resize_factor=28,
    min_pixels=1792 * 28,
    max_pixels=3072 * 2048,
    resize_strategy="chandra",
    resample="lanczos",
    image_format="PNG",
)


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
        image_render_profile=GLM_RENDER_PROFILE,
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
        image_render_profile=DOTS_RENDER_PROFILE,
    ),
    "rednote-hilab/dots.mocr-svg": ModelServiceProfile(
        name="rednote-hilab/dots.mocr-svg",
        description=(
            "dots.mocr-svg OpenAI-compatible VLM service defaults for image-to-SVG "
            "parsing."
        ),
        model="rednote-hilab/dots.mocr-svg",
        prompt=DOTS_IMAGE_TO_SVG_PROMPT,
        response_parser="svg",
        max_tokens=32768,
        token_param="max_completion_tokens",
        temperature=0.9,
        top_p=1.0,
        text_prefix="<|img|><|imgpad|><|endofimg|>",
        image_render_profile=DOTS_RENDER_PROFILE,
        accepted_finish_reasons=(None, "stop", "end_turn", "length"),
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
        image_render_profile=DOTS_RENDER_PROFILE,
    ),
    "rednote-hilab/dots.ocr-1.5-svg": ModelServiceProfile(
        name="rednote-hilab/dots.ocr-1.5-svg",
        description=(
            "dots.ocr 1.5 SVG OpenAI-compatible VLM service defaults for "
            "image-to-SVG parsing."
        ),
        model="rednote-hilab/dots.ocr-1.5-svg",
        prompt=DOTS_IMAGE_TO_SVG_PROMPT,
        response_parser="svg",
        max_tokens=32768,
        token_param="max_completion_tokens",
        temperature=0.9,
        top_p=1.0,
        text_prefix="<|img|><|imgpad|><|endofimg|>",
        image_render_profile=DOTS_RENDER_PROFILE,
        accepted_finish_reasons=(None, "stop", "end_turn", "length"),
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
        image_render_profile=DOTS_RENDER_PROFILE,
    ),
    "deepseek-ai/DeepSeek-OCR": ModelServiceProfile(
        name="deepseek-ai/DeepSeek-OCR",
        description="DeepSeek-OCR OpenAI-compatible VLM service defaults.",
        model="deepseek-ai/DeepSeek-OCR",
        prompt=DEEPSEEK_OCR_MARKDOWN_PROMPT,
        response_parser="deepseek_markdown",
        max_tokens=8192,
        temperature=0.0,
        extra_body={
            "include_stop_str_in_output": True,
            "skip_special_tokens": False,
        },
        text_prefix="<|grounding|>",
        image_render_profile=DEEPSEEK_RENDER_PROFILE,
    ),
    "FireRedTeam/FireRed-OCR-2B": ModelServiceProfile(
        name="FireRedTeam/FireRed-OCR-2B",
        description="FireRed-OCR OpenAI-compatible VLM service defaults.",
        model="FireRedTeam/FireRed-OCR-2B",
        prompt=FIRERED_OCR_MARKDOWN_PROMPT,
        response_parser="markdown",
        max_tokens=8192,
        temperature=0.0,
        image_render_profile=FIRERED_RENDER_PROFILE,
    ),
    "datalab-to/chandra-ocr-2": ModelServiceProfile(
        name="datalab-to/chandra-ocr-2",
        description=(
            "Chandra OCR 2 vLLM service defaults from third_party/chandra. "
            "The official vLLM launcher serves the model as 'chandra'."
        ),
        model="chandra",
        prompt=CHANDRA_OCR_LAYOUT_PROMPT,
        response_parser="chandra_html",
        max_tokens=12384,
        temperature=0.0,
        top_p=0.1,
        image_render_profile=CHANDRA_RENDER_PROFILE,
    ),
}

MODEL_SERVICE_ALIASES: dict[str, str] = {
    "chandra": "datalab-to/chandra-ocr-2",
    "glm-ocr": "zai-org/GLM-OCR",
    "glmocr": "zai-org/GLM-OCR",
    "deepseek-ocr": "deepseek-ai/DeepSeek-OCR",
    "dots.mocr": "rednote-hilab/dots.mocr",
    "dots.mocr-svg": "rednote-hilab/dots.mocr-svg",
    "dots.ocr": "rednote-hilab/dots.ocr-1.5",
    "dots.ocr-1.5": "rednote-hilab/dots.ocr-1.5",
    "dots.ocr-1.5-svg": "rednote-hilab/dots.ocr-1.5-svg",
    "firered-ocr": "FireRedTeam/FireRed-OCR-2B",
    "firered-ocr-2b": "FireRedTeam/FireRed-OCR-2B",
}

PROFILE_KEYS_BY_LOWER: dict[str, str] = {
    name.lower(): name for name in MODEL_SERVICE_PROFILES
}
PROFILE_KEYS_BY_LOWER.update(
    {alias.lower(): target for alias, target in MODEL_SERVICE_ALIASES.items()}
)


def normalize_model_service_name(name: str) -> str:
    stripped = name.strip().rstrip("/")
    lower = stripped.lower()
    if lower in PROFILE_KEYS_BY_LOWER:
        return PROFILE_KEYS_BY_LOWER[lower]
    return stripped


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
