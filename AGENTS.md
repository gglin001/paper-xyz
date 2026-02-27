# Repository Guidelines

## Project Structure & Module Organization

This repository follows a convert-then-analyze workflow:

- `pdf/`: source papers provided by users.
- `md/`: generated Markdown used as the primary analysis input.
- `png/`: image files produced during the `pdf-image-ocr-md` process.
- `agent/`: reference materials only (templates/examples/draft scripts), not production pipeline code.
- `scripts/`: directly usable scripts.
- `debug_agent/`: untracked scratch workspace for temp files and local experiments (use this instead of `/tmp`).

Keep filename stems aligned across formats when practical, e.g. `pdf/MyPaper.pdf` -> `md/MyPaper.md` and `png/MyPaper_png/`.

## Build, Test, and Development Commands

Use `pixi` for all local workflows:

- `pixi install`: install or sync the locked environment.
- `pixi run -e markitdown markitdown pdf/<file>.pdf -o md/<file>.md`: run one supported PDF-to-Markdown converter path.
- `mkdir -p debug_agent && cp agent/markitdown_ref.sh debug_agent/markitdown_local.sh && chmod +x debug_agent/markitdown_local.sh`: create a runnable local script from the reference template, then update it as needed.
- `pixi run -e markitdown bash debug_agent/markitdown_local.sh`: execute your local conversion script.
- `pixi run -e default ruff check .`: lint Python code.
- `pixi run -e default ruff format .`: format Python code.
- `pixi run -e default ty check .`: run type checks.
- skip `pre-commit`; handled manually.

`markitdown` is only one option. New conversion backends are welcome as long as they produce analysis-ready Markdown in `md/`.

## Coding Style & Naming Conventions

- Python target: `3.13`; use 4-space indentation and small, focused functions.
- Shell scripts should use `set -euo pipefail` and be composable.
- Prefer descriptive lowercase names with underscores for scripts/modules.
- Do not manually edit generated Markdown except when documenting conversion defects.

## Testing Guidelines

There is no formal automated test suite or coverage gate yet.

- For conversion changes, run at least one real file from `pdf/` and inspect output in `md/`.
- Verify structure and fidelity (headings, equations/tables, references, obvious OCR/layout issues).
- Keep temporary validation artifacts in `debug_agent/`.
- If you add non-trivial Python logic, create tests under `tests/` and document how to run them.

## Commit & Pull Request Guidelines

Recent commits include short lowercase subjects; prefer clearer scoped messages.

- Use `scope: imperative summary`, e.g. `converter: add marker-based batch flow`.
- Keep each commit focused on one logical change.
- PRs should include intent, changed paths, and validation commands executed.
- For conversion behavior changes, include a before/after sample path from `md/` and note which backend was used.

## Agent-Specific Instructions

- Analyze papers from `md/`, not directly from `pdf/`.
- Treat reproducibility as a core requirement.
- Keep reusable references in `agent/`; do not execute them as production scripts.
- Keep directly usable project scripts in `scripts/`; agents may execute these scripts.
- Keep disposable scripts and temporary outputs in `debug_agent/`.
- Design workflows so multiple PDF conversion backends can coexist.
