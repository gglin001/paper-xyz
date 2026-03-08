#!/usr/bin/env bash
set -euo pipefail

# https://hf-mirror.com/
# export HF_ENDPOINT=https://hf-mirror.com

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
HFD_BIN="${HFD_BIN:-hfd.sh}"
HFD_WORK_DIR="${HFD_WORK_DIR:-${REPO_ROOT}/third_party}"

if ! command -v "${HFD_BIN}" >/dev/null 2>&1; then
  echo "error: ${HFD_BIN} is required but not installed" >&2
  exit 127
fi

if [[ ! -d "${HFD_WORK_DIR}" ]]; then
  echo "error: target directory does not exist: ${HFD_WORK_DIR}" >&2
  echo "hint: create it or set HFD_WORK_DIR to an existing directory" >&2
  exit 2
fi

if [[ ! -w "${HFD_WORK_DIR}" ]]; then
  echo "error: target directory is not writable: ${HFD_WORK_DIR}" >&2
  exit 2
fi

run_hfd() {
  local repo="$1"
  shift
  "${HFD_BIN}" "${repo}" "$@"
}

GLM_GGML_REPO="${GLM_GGML_REPO:-ggml-org/GLM-OCR-GGUF}"
GLM_GGML_INCLUDE_MODEL="${GLM_GGML_INCLUDE_MODEL:-GLM-OCR-Q8_0.gguf}"
GLM_GGML_INCLUDE_MMPROJ="${GLM_GGML_INCLUDE_MMPROJ:-mmproj-GLM-OCR-Q8_0.gguf}"

GLM_MRADERMACHER_REPO="${GLM_MRADERMACHER_REPO:-mradermacher/GLM-OCR-GGUF}"
GLM_MRADERMACHER_LOCAL_DIR="${GLM_MRADERMACHER_LOCAL_DIR:-GLM-OCR-GGUF-mradermacher}"
GLM_MRADERMACHER_INCLUDE_F16="${GLM_MRADERMACHER_INCLUDE_F16:-GLM-OCR.f16.gguf}"
GLM_MRADERMACHER_INCLUDE_MM_F16="${GLM_MRADERMACHER_INCLUDE_MM_F16:-GLM-OCR.mmproj-f16.gguf}"
GLM_MRADERMACHER_INCLUDE_Q8="${GLM_MRADERMACHER_INCLUDE_Q8:-GLM-OCR.Q8_0.gguf}"
GLM_MRADERMACHER_INCLUDE_MM_Q8="${GLM_MRADERMACHER_INCLUDE_MM_Q8:-GLM-OCR.mmproj-Q8_0.gguf}"

FIRERED_REPO="${FIRERED_REPO:-mradermacher/FireRed-OCR-GGUF}"
FIRERED_INCLUDE_Q8="${FIRERED_INCLUDE_Q8:-FireRed-OCR.Q8_0.gguf}"
FIRERED_INCLUDE_MM_Q8="${FIRERED_INCLUDE_MM_Q8:-FireRed-OCR.mmproj-Q8_0.gguf}"

LIGHTON_REPO="${LIGHTON_REPO:-mradermacher/LightOnOCR-2-1B-GGUF}"
LIGHTON_INCLUDE_Q8="${LIGHTON_INCLUDE_Q8:-LightOnOCR-2-1B.Q8_0.gguf}"
LIGHTON_INCLUDE_MM_Q8="${LIGHTON_INCLUDE_MM_Q8:-LightOnOCR-2-1B.mmproj-Q8_0.gguf}"
LIGHTON_INCLUDE_F16="${LIGHTON_INCLUDE_F16:-LightOnOCR-2-1B.f16.gguf}"
LIGHTON_INCLUDE_MM_F16="${LIGHTON_INCLUDE_MM_F16:-LightOnOCR-2-1B.mmproj-f16.gguf}"

GRANITE_REPO="${GRANITE_REPO:-ggml-org/granite-docling-258M-GGUF}"

MLX_GLM_BF16_REPO="${MLX_GLM_BF16_REPO:-mlx-community/GLM-OCR-bf16}"
MLX_GLM_8BIT_REPO="${MLX_GLM_8BIT_REPO:-mlx-community/GLM-OCR-8bit}"
MLX_DEEPSEEK_8BIT_REPO="${MLX_DEEPSEEK_8BIT_REPO:-mlx-community/DeepSeek-OCR-2-8bit}"
MLX_DOTS_BF16_REPO="${MLX_DOTS_BF16_REPO:-mlx-community/dots.ocr-bf16}"

(
  cd -- "${HFD_WORK_DIR}"

  run_hfd "${GLM_GGML_REPO}" \
    --include "${GLM_GGML_INCLUDE_MODEL}" \
    --include "${GLM_GGML_INCLUDE_MMPROJ}"

  run_hfd "${GLM_MRADERMACHER_REPO}" \
    --include "${GLM_MRADERMACHER_INCLUDE_F16}" \
    --include "${GLM_MRADERMACHER_INCLUDE_MM_F16}" \
    --include "${GLM_MRADERMACHER_INCLUDE_Q8}" \
    --include "${GLM_MRADERMACHER_INCLUDE_MM_Q8}" \
    --local-dir "${GLM_MRADERMACHER_LOCAL_DIR}"

  run_hfd "${FIRERED_REPO}" \
    --include "${FIRERED_INCLUDE_Q8}" \
    --include "${FIRERED_INCLUDE_MM_Q8}"

  run_hfd "${LIGHTON_REPO}" \
    --include "${LIGHTON_INCLUDE_Q8}" \
    --include "${LIGHTON_INCLUDE_MM_Q8}" \
    --include "${LIGHTON_INCLUDE_F16}" \
    --include "${LIGHTON_INCLUDE_MM_F16}"

  run_hfd "${GRANITE_REPO}"
  run_hfd "${MLX_GLM_BF16_REPO}"
  run_hfd "${MLX_GLM_8BIT_REPO}"
  run_hfd "${MLX_DEEPSEEK_8BIT_REPO}"
  run_hfd "${MLX_DOTS_BF16_REPO}"
)
