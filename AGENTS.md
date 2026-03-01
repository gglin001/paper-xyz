# Repository Guidelines

## Project Structure & Module Organization

This repository follows a convert-then-analyze workflow:

- `pdf/`: source papers provided by users.
- `md/`: generated Markdown used as the primary analysis input.
- `png/`: image files produced during the `pdf-image-ocr-md` process.
- `agent/`: reference materials only (templates/examples/draft scripts), not production pipeline code.
- `scripts/`: directly usable scripts.
- `debug_agent/`: untracked scratch workspace for temp files and local experiments (use this instead of `/tmp`).

Keep filename stems aligned across formats when practical, e.g. `pdf/MyPaper.pdf` -> `md/MyPaper.md` and `png/MyPaper/`.

## Build, Test, and Development Commands

Use `pixi` for all local workflows:

- `pixi install`: install or sync the locked environment.
- `pixi run -e default python agent/pdf_split_ref.py pdf/<file>.pdf --pages <selector> -o debug_agent/<file>.subset.pdf`: extract representative pages for large/complex PDF debug and test loops.
- Conversion backend selection and exact usage live in `agent/README.md`; check that file first, then use each script's `--help` for final arguments.
- `pixi run -e default ruff check .`: lint Python code.
- `pixi run -e default ruff format .`: format Python code.
- `pixi run -e default ty check .`: run type checks.
- skip `pre-commit`; handled manually.

## Large or Complex PDF Debug/Test Workflow

When source PDFs are large or structurally complex, or when you need fast debug/test iteration:

1. Split first with `agent/pdf_split_ref.py`, and save subset PDFs under `debug_agent/`.
2. Pick representative pages, especially layout-heavy or error-prone pages, for parameter tuning and troubleshooting.
3. Run conversion backends against the subset PDF until prompts/parameters are stable, then run lightweight checks/tests on the same subset.
4. Re-run the same settings on the full source PDF in `pdf/` after the subset workflow is stable.
5. Keep temporary subset files in `debug_agent/`, and keep final analysis inputs in `md/`.

## Coding Style & Naming Conventions

- Python target: `3.13`; use 4-space indentation and small, focused functions.
- Shell scripts should use `set -euo pipefail` and be composable.
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
- Design workflows so multiple PDF conversion backends can coexist.

## Workspace Hygiene and `.gitignore` Policy

The repository uses a narrow `.gitignore` strategy (targeted ignores), not a global deny-all pattern like `*` + whitelist.

- Keep analysis inputs such as `md/` readable and visible to normal workflows.
- Do not switch to a deny-all ignore pattern unless explicitly requested.
- Assume `.gitignore` controls Git tracking only; it does not block local file reading by agents.
- Prefer putting disposable outputs in `debug_agent/` instead of expanding broad ignore rules.
