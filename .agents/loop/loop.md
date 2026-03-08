# Codex Autonomous Development Baseline

## Goal

Run Codex in repeated rounds with one stable control prompt. The model inspects repository state, chooses focus, executes, validates, and closes the round.

## Shared State File

Both `loop-arch` and `loop-build` must use `.agents/loop/todo.md` as the shared dynamic state.

- `todo.md` stores project-level goals.
- `todo.md` stores ordered todo entries for upcoming slices.
- `todo.md` stores execution state for each todo (`todo` or `done`).
- `todo.md` is dynamic. Goals and todo entries can be updated based on the latest repository state.

## Single Control Prompt Template

Use this exact structure each round:

```text
You are the project engineer. Run one autonomous development round.

Inputs:
- Current repository state.
- Current user goal or backlog note.
- Project rules from AGENTS.md.
- Shared todo state from .agents/loop/todo.md.

Round contract:
1. Inspect current state first (files, git diff, failed checks, and .agents/loop/todo.md).
2. Decide one primary focus for this round: loop-arch or loop-build, using the startup rules in loop.md.
3. If loop-arch, update goals or todo entries in .agents/loop/todo.md and produce a concrete next loop-build slice.
4. If loop-build, pick one unprocessed todo entry from .agents/loop/todo.md, implement it, and mark it done.
5. Keep scope small, deterministic, and reproducible.
6. Run relevant checks and report real results.
7. If there are changes, use the loop-git skill to create one commit and push for this round.
8. Finish with clear round output:
   - focus selected
   - changes made
   - checks run
   - todo.md updates
   - loop-git commit and push result
   - next smallest step
```

## Trigger Reference

Use this flow to trigger one autonomous round in Codex.

1. Ensure `.agents/loop/todo.md` exists. If missing, create it from the project template.
2. Start a new Codex turn in repository root.
3. Send one control message that asks Codex to execute exactly one round using `.agents/loop/loop.md`.

Reference control message:

```text
Run one autonomous development round using .agents/loop/loop.md.

Requirements:
- Follow the startup selection rules to choose loop-arch or loop-build.
- Read and update .agents/loop/todo.md as required by the selected skill.
- Run relevant validation checks.
- If files changed, finalize with loop-git (stage, commit, push).
- Return the round output contract fields.
```

Run the same trigger message again for the next round.

## Startup Focus Selection Rules

At the start of every round, evaluate `.agents/loop/todo.md` first.

1. If `.agents/loop/todo.md` does not exist, start `loop-arch`.
2. If `.agents/loop/todo.md` exists but has no valid todo entries, start `loop-arch`.
3. If pending todo count (`status = todo`) is `>= 5`, start `loop-build`.
4. If `done_ratio` is in `[0.65, 0.75]`, randomly start `loop-arch` or `loop-build` with equal probability.
5. Otherwise, if there is any pending todo, start `loop-build`.
6. Otherwise, if all todos are done, start `loop-arch`.

Definitions:

- `total_count`: number of valid todo entries.
- `done_count`: number of entries with `status = done`.
- `pending_count`: number of entries with `status = todo`.
- `done_ratio = done_count / total_count` when `total_count > 0`.

Randomization note:

- In the random branch, use a simple 50 or 50 coin flip.
- Record the random outcome in the round output for traceability.

Do not run `loop-arch` and `loop-build` as dual primary focus in one round.

## Skill Ownership Contract

- `loop-arch` owns todo planning quality.
- `loop-arch` updates project goals when they drift.
- `loop-arch` adds, splits, merges, reorders, or removes todo entries.
- `loop-arch` keeps each todo entry implementation-ready.
- `loop-build` owns execution.
- `loop-build` selects unprocessed todo entries (`status = todo`).
- `loop-build` implements one minimal slice per round.
- `loop-build` marks completed entries to `status = done`.
- `loop-build` does not rewrite global goals unless required for correctness.
- `loop-git` owns commit and push finalization for both `loop-arch` and `loop-build`.
- `loop-arch` and `loop-build` must call `loop-git` when round changes exist.

## Round Output Contract

Each round should leave:

- A concrete code or document delta in repository.
- Validation evidence (commands and pass or fail status).
- Updated `.agents/loop/todo.md` state when applicable.
- One commit and push completed through `loop-git` skill when delta exists.
- The next minimal executable step.

## Shared Principles for Autonomous Rounds

- Inspect current repository state before deciding actions.
- Define a clear round target and explicit non-goals.
- Keep scope to one minimal executable slice.
- Prefer deterministic commands and reproducible outputs.
- Report facts and command results directly, without hiding failures.

## Testing Principles

- Run the smallest relevant checks for changed scope in every loop-build round.
- If full checks are expensive, run targeted checks first, then broader checks when needed.
- Treat failing checks as first-class outcomes, and include failure cause and impact.
- Never claim completion without validation evidence.

## Commit Principles

- One commit should represent one coherent change slice.
- Commit messages should be short, scoped, and behavior oriented.
- Do not mix unrelated refactor with functional changes.
- Include only files needed by the decided round scope.
- Use the `loop-git` skill for staging, commit, and push operations.
- If no files changed, skip commit and push, and report why.
