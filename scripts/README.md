# Scripts Reference

This directory contains directly usable helper scripts for local model setup, inference, and smoke checks.

## Quick usage

Run all commands from the repository root.

## Script catalog

### `debug.sh`

Purpose: smoke-test an OpenAI-compatible local server by calling `/v1/models` and `/v1/chat/completions`.

Required environment and tools:

- `curl` must be installed.
- Optional env vars: `API_BASE` (default `http://127.0.0.1:11235`), `REQUEST_TIMEOUT_SECONDS` (default `10`).

Stable invocation:

```bash
bash scripts/debug.sh
```

### `llama-cli.sh`

Purpose: run `llama-cli` with a multimodal GGUF model and one input image.

Required environment and tools:

- `llama-cli` binary must be available.
- Model files must exist at configured paths.
- Optional env vars: `LLAMA_CLI_BIN`, `LLAMA_MODEL`, `LLAMA_MMPROJ`, `LLAMA_PROMPT`, `LLAMA_IMAGE`, `LLAMA_STREAM` (`1` enables streaming), `LLAMA_MAX_TOKENS`, `LLAMA_TEMP`.

Stable invocation:

```bash
bash scripts/llama-cli.sh
```

### `mlx_vlm.generate.sh`

Purpose: run `mlx_vlm.generate` via `pixi` for image-to-markdown generation.

Required environment and tools:

- `pixi` must be installed.
- The `mlx` environment must be available (`pixi install`).
- Model path must exist.
- Optional env vars: `PIXI_BIN`, `MLX_MODEL`, `MLX_MAX_TOKENS`, `MLX_TEMPERATURE`, `MLX_PROMPT`, `MLX_IMAGE`.

Stable invocation:

```bash
bash scripts/mlx_vlm.generate.sh
```

### `mlx_lm.server.sh`

Purpose: start `mlx_lm.server` through `pixi` with deterministic preflight checks.

Required environment and tools:

- `pixi` must be installed.
- The `mlx` environment must be available (`pixi install`).
- `MLX_LM_MODEL` must point to an existing local model directory.
- Optional env vars: `PIXI_BIN`, `MLX_LM_MODEL`, `MLX_LM_TEMP`, `MLX_LM_MAX_TOKENS`, `MLX_LM_HOST`, `MLX_LM_PORT`.

Stable invocation:

```bash
MLX_LM_MODEL=third_party/dots.ocr-bf16 bash scripts/mlx_lm.server.sh
```

### `debug_openai_latency.py`

Purpose: measure request latency across repeated calls to OpenAI-compatible APIs.

Required environment and tools:

- `pixi` default environment installed.
- `OPENAI_API_KEY` must be set.
- Optional env vars: `OPENAI_BASE_URL`, `OPENAI_API`, `OPENAI_MODEL`.

Stable invocation:

```bash
OPENAI_API_KEY=sk-local pixi run -e default python scripts/debug_openai_latency.py --runs 5 --api responses --model gpt-5.2
```

### `fetch_hf_ocr_models.py`

Purpose: query Hugging Face model metadata and print OCR-oriented model candidates.

Required environment and tools:

- `pixi` default environment installed, or `requests` installed in your active Python environment.
- Network access to `https://huggingface.co`.

Stable invocation:

```bash
pixi run -e default python scripts/fetch_hf_ocr_models.py
```

### `hfd.sh`

Purpose: batch-download selected OCR model artifacts into `third_party/` via `hfd.sh`.

Required environment and tools:

- External `hfd.sh` downloader command must be installed and in `PATH`.
- `third_party/` directory must exist.
- Optional env vars: `HF_ENDPOINT` (for mirror endpoints, for example `https://hf-mirror.com`).

Stable invocation:

```bash
bash scripts/hfd.sh
```
