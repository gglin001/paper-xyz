# Repository Guidelines

## Project Structure & Module Organization

This repository follows a convert-then-analyze workflow:

- `pdf/`: source papers provided by users.
- `md/`: generated Markdown used as the primary analysis input.
- `png/`:wpagwe images produced during PDF-to-image workflows.
- `agent/`: reference scripts and sample inputs, not production pipeline code.
- `scripts/`: directly usable project scripts.
- `debug_agent/`: untracked scratch workspace for temp files and local experiments.

Keep filename stems aligned across formats when practical, e.g. `pdf/MyPaper.pdf` -> `md/MyPaper.md` and `png/MyPaper/`.

## PDF Conversion

Use `agent/paper_xyz_ref.py` as the primary reference CLI for PDF-to-Markdown conversion. It renders pages locally and calls an OpenAI-compatible `/v1/chat/completions` VLM API page by page.

- Single PDF: `pixi run -e default python agent/paper_xyz_ref.py pdf/<file>.pdf -o md/<file>.md`
- List model presets: `pixi run -e default python agent/paper_xyz_ref.py --list_model_services`
- Batch PDFs: `pixi run -e default python scripts/batch_pdf_convert.py pdf -o md -- pixi run -e default python agent/paper_xyz_ref.py --concurrency 8`

`paper_xyz_ref.py` keeps failed pages as Markdown placeholders by default; use `--fail_fast` when partial output is not acceptable. Use the script's `--help` for model service, API, retry, timeout, and page-range options.

For large or complex PDFs, first split representative pages into `debug_agent/`, tune settings on the subset, then rerun the same settings on the full PDF:

`pixi run -e default python agent/pdf_split_ref.py pdf/<file>.pdf --pages <selector> -o debug_agent/<file>.subset.pdf`

## Build, Test, and Development Commands

- `pixi install`: install or sync the locked environment.
- `pixi run -e default ruff check .`: lint Python code.
- `pixi run -e default ruff format .`: format Python code.
- `pixi run -e default ty check .`: run type checks.
- Skip `pre-commit`; checks are handled manually.

## Coding Style & Naming Conventions

- Python target: `3.13`; use 4-space indentation and small, focused functions.
- Prefer elegant, concise, and intuitive implementations over bloated or over-abstract designs.
- Focus effort and code volume on core paths; keep edge-path handling proportional and minimal.
- Shell scripts should use `set -euo pipefail` and stay simple and composable.
- Prefer descriptive lowercase names with underscores for scripts/modules.

## Testing Guidelines

There is no formal automated test suite or coverage gate yet.

## Commit & Pull Request Guidelines

Recent commits include short lowercase subjects; prefer clearer scoped messages.

## Agent-Specific Instructions

- Analyze papers from `md/`, not directly from `pdf/`.
- Treat reproducibility as a core requirement.
- Keep reusable references in `agent/`; do not execute them as production scripts.
- Keep directly usable project scripts in `scripts/`; agents may execute these scripts.
- Keep disposable scripts and temporary outputs in `debug_agent/`.
- Design workflows so multiple PDF conversion backends can coexist with minimal necessary abstraction.

## Workspace Hygiene and `.gitignore` Policy

- Keep `.gitignore` narrow and targeted; do not switch to a deny-all whitelist pattern unless explicitly requested.
- `.gitignore` only affects Git tracking, so agents may still read ignored files, including relevant code under `third_party/` and safe symlinked contents.
- When searching under `third_party/`, prefer `rg -u` or `rg -uL` so `.gitignore` rules and symlinks do not hide relevant files.
- Put disposable scripts and outputs in `debug_agent/` instead of broadening ignore rules.
