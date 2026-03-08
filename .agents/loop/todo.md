# Project Goals

- Make `scripts/` the reliable entrypoint for reproducible local tooling, while keeping `agent/` as reference-only.
- Normalize shell helper scripts to runnable strict-mode wrappers with explicit defaults and clear failure messages.
- Keep script documentation aligned with actual commands and expected validation steps.
- Finish migrating remaining legacy helper scripts to the same strict-mode and reproducibility baseline.

# Todo Entries

Use one line per entry with this format:

`- [status] TID | title | notes`

Rules:

- `status` must be `todo` or `done`.
- `TID` should be stable, for example `T001`.
- Keep entries ordered by execution priority.
- Prefer small, implementation-ready entries.

# Todo list

- [done] T000 | initialize autonomous loop files | create `.agents/loop/loop.md` and seed `.agents/loop/todo.md`
- [done] T001 | harden `scripts/debug.sh` into a safe smoke-test command | add shebang, `set -euo pipefail`, and `curl` flags that fail loudly
- [done] T002 | harden `scripts/llama-cli.sh` and `scripts/mlx_vlm.generate.sh` | add shebang, `set -euo pipefail`, and minimal env-driven input overrides
- [done] T003 | make `scripts/mlx_lm.server.sh` actionable | replace ambiguous TODO note with a deterministic preflight check and clear failure hint
- [done] T004 | document directly usable scripts in `scripts/README.md` | list purpose, required env, and one stable invocation per script
- [done] T005 | run repository quality checks after script edits | execute `pixi run -e default ruff check .` and `pixi run -e default ty check .` and resolve issues in touched files
- [done] T006 | harden `scripts/hfd.sh` into a strict wrapper | add shebang and `set -euo pipefail`, enforce required commands and paths, and move model downloads into explicit configurable defaults
- [done] T007 | sync `scripts/README.md` for `hfd.sh` behavior and validate script syntax | document env vars and stable invocation after T006, then run `bash -n scripts/hfd.sh` plus repository checks
