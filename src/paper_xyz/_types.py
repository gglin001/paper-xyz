from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, ClassVar


class ConversionStatus(str, Enum):
    PENDING = "pending"
    STARTED = "started"
    FAILURE = "failure"
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"


class InputFormat(str, Enum):
    PDF = "pdf"


class ResponseFormat(str, Enum):
    MARKDOWN = "markdown"


class VlmEngineType(str, Enum):
    TRANSFORMERS = "transformers"
    MLX = "mlx"
    VLLM = "vllm"
    API = "api"
    API_OLLAMA = "api_ollama"
    API_LMSTUDIO = "api_lmstudio"
    API_OPENAI = "api_openai"
    AUTO_INLINE = "auto_inline"

    @classmethod
    def is_api_variant(cls, engine_type: VlmEngineType) -> bool:
        return engine_type in {
            cls.API,
            cls.API_OLLAMA,
            cls.API_LMSTUDIO,
            cls.API_OPENAI,
        }


def _default_api_url(engine_type: VlmEngineType) -> str:
    if engine_type == VlmEngineType.API_OLLAMA:
        return "http://localhost:11434/v1/chat/completions"
    if engine_type == VlmEngineType.API_LMSTUDIO:
        return "http://localhost:1234/v1/chat/completions"
    if engine_type == VlmEngineType.API_OPENAI:
        return "https://api.openai.com/v1/chat/completions"
    return "http://127.0.0.1:11235/v1/chat/completions"


@dataclass(slots=True)
class ApiVlmEngineOptions:
    engine_type: VlmEngineType = VlmEngineType.API
    url: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    params: dict[str, Any] = field(default_factory=dict)
    timeout: float = 60.0
    concurrency: int = 1

    def __post_init__(self) -> None:
        if not VlmEngineType.is_api_variant(self.engine_type):
            raise ValueError(
                f"Unsupported engine type for API runtime: {self.engine_type}"
            )
        if not self.url:
            self.url = _default_api_url(self.engine_type)
        self.timeout = float(self.timeout)
        self.concurrency = max(1, int(self.concurrency))
        self.headers = dict(self.headers)
        self.params = {
            key: value for key, value in self.params.items() if value is not None
        }


@dataclass(slots=True)
class ApiModelConfig:
    params: dict[str, Any] = field(default_factory=dict)

    def merge_with(self, base_params: dict[str, Any]) -> ApiModelConfig:
        return ApiModelConfig(params={**base_params, **self.params})


@dataclass(slots=True)
class VlmModelSpec:
    name: str
    default_repo_id: str | None
    prompt: str
    response_format: ResponseFormat
    supported_engines: set[VlmEngineType] | None = None
    api_overrides: dict[VlmEngineType, ApiModelConfig] = field(default_factory=dict)
    stop_strings: list[str] = field(default_factory=list)
    max_new_tokens: int = 4096

    def get_api_params(self, engine_type: VlmEngineType) -> dict[str, Any]:
        base_params: dict[str, Any] = {}
        if self.default_repo_id not in {None, "", "None"}:
            base_params["model"] = self.default_repo_id
        if engine_type in self.api_overrides:
            return self.api_overrides[engine_type].merge_with(base_params).params
        return base_params

    def is_engine_supported(self, engine_type: VlmEngineType) -> bool:
        if self.supported_engines is None:
            return True
        return engine_type in self.supported_engines


@dataclass(slots=True)
class StageModelPreset:
    preset_id: str
    name: str
    description: str
    model_spec: VlmModelSpec
    default_engine_type: VlmEngineType = VlmEngineType.API
    scale: float = 2.0
    max_size: int | None = None
    stage_options: dict[str, Any] = field(default_factory=dict)


class StagePresetMixin:
    _presets: ClassVar[dict[str, StageModelPreset]]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls._presets = {}

    @classmethod
    def register_preset(cls, preset: StageModelPreset) -> None:
        cls._presets[preset.preset_id] = preset

    @classmethod
    def get_preset(cls, preset_id: str) -> StageModelPreset:
        try:
            return cls._presets[preset_id]
        except KeyError as exc:
            available = ", ".join(sorted(cls._presets)) or "<none>"
            raise ValueError(
                f"Unknown preset `{preset_id}`. Available presets: {available}"
            ) from exc

    @classmethod
    def list_presets(cls) -> list[StageModelPreset]:
        return [cls._presets[key] for key in sorted(cls._presets)]

    @classmethod
    def describe_presets(cls) -> list[dict[str, str]]:
        return [
            {
                "preset_id": preset.preset_id,
                "name": preset.name,
                "description": preset.description,
                "model": preset.model_spec.name,
                "default_engine": preset.default_engine_type.value,
            }
            for preset in cls.list_presets()
        ]


@dataclass(slots=True)
class VlmConvertOptions(StagePresetMixin):
    model_spec: VlmModelSpec
    engine_options: ApiVlmEngineOptions
    scale: float = 2.0
    max_size: int | None = None
    batch_size: int = 1
    force_backend_text: bool = False
    temperature: float = 0.0

    @classmethod
    def from_preset(
        cls,
        preset_id: str,
        engine_options: ApiVlmEngineOptions | None = None,
        **overrides: Any,
    ) -> VlmConvertOptions:
        preset = cls.get_preset(preset_id)
        if engine_options is None:
            if not VlmEngineType.is_api_variant(preset.default_engine_type):
                raise NotImplementedError(
                    "paper_xyz currently only supports API-based VLM runtimes."
                )
            engine_options = ApiVlmEngineOptions(engine_type=preset.default_engine_type)
        instance = cls(
            model_spec=preset.model_spec,
            engine_options=engine_options,
            scale=preset.scale,
            max_size=preset.max_size,
            **preset.stage_options,
        )
        for key, value in overrides.items():
            setattr(instance, key, value)
        return instance

    def resolved_api_params(self) -> dict[str, Any]:
        engine_type = self.engine_options.engine_type
        if not self.model_spec.is_engine_supported(engine_type):
            raise ValueError(
                f"Preset model `{self.model_spec.name}` does not support engine `{engine_type.value}`."
            )
        params = self.model_spec.get_api_params(engine_type)
        params.update(self.engine_options.params)
        if "temperature" not in params:
            params["temperature"] = self.temperature
        return {key: value for key, value in params.items() if value is not None}


@dataclass(slots=True)
class VlmPipelineOptions:
    vlm_options: VlmConvertOptions
    enable_remote_services: bool = False


@dataclass(slots=True)
class MarkdownPage:
    page_no: int
    markdown: str
    token_count: int | None = None


@dataclass(slots=True)
class MarkdownDocument:
    pages: list[MarkdownPage]
    source: Path | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def export_to_markdown(self) -> str:
        parts = [page.markdown.strip() for page in self.pages if page.markdown.strip()]
        if not parts:
            return ""
        return "\n\n".join(parts).rstrip() + "\n"


@dataclass(slots=True)
class ConversionResult:
    status: ConversionStatus
    document: MarkdownDocument
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


DEFAULT_PROMPT = "Parse this document and convert it into standard markdown format."


VlmConvertOptions.register_preset(
    StageModelPreset(
        preset_id="openai_compatible_markdown",
        name="openai_compatible_markdown",
        description="Generic PDF page-to-markdown preset for OpenAI-compatible VLM APIs.",
        model_spec=VlmModelSpec(
            name="openai_compatible_markdown",
            default_repo_id=None,
            prompt=DEFAULT_PROMPT,
            response_format=ResponseFormat.MARKDOWN,
            supported_engines={
                VlmEngineType.API,
                VlmEngineType.API_OLLAMA,
                VlmEngineType.API_LMSTUDIO,
                VlmEngineType.API_OPENAI,
            },
        ),
        default_engine_type=VlmEngineType.API,
        scale=2.0,
    )
)
