# Markdown Paper Analysis Guide

## Purpose

This file defines how to analyze papers from `md/` documents, with focus on accurate understanding, clear explanation, and zero unsupported claims.

## Scope

- Use only Markdown files in `md/` as the primary source.
- Analyze, interpret, and explain paper content.
- Keep this guide limited to analysis behavior (not conversion, tooling, or environment setup).

## Core Rules

1. Evidence first: every important statement must map to a concrete source location in the Markdown (section, table, equation, or quoted sentence fragment).
2. Separate `Fact` and `Inference`: facts come directly from the paper text; inferences are interpretations based on cited facts.
3. Do not invent missing details: if something is not present, write `Not stated in paper` or `Unclear from converted Markdown`.
4. Mark possible conversion noise (broken formulas, OCR errors, table misalignment, missing captions) as `conversion_issue`.
5. Prefer conservative wording when evidence is weak or incomplete.

## Standard Analysis Workflow

1. Check document structure: title, abstract, section hierarchy, figures/tables, references.
2. Extract core content: problem, method, data, metrics, main results, limitations.
3. Build claim-to-evidence links for each key conclusion.
4. Write explanation in plain language while preserving technical meaning.
5. Run a final consistency check: remove or revise any claim without clear evidence.

## Required Output Structure

- `Paper Snapshot`: one-sentence problem, one-sentence method, one-sentence main result.
- `Key Claims with Evidence`: each claim paired with source location.
- `Method Explanation`: components, assumptions, and what is novel.
- `Experiment Interpretation`: setup, baselines, metrics, and what results actually show.
- `Limitations and Risks`: paper-stated limits plus confidence impact from conversion issues.
- `Open Questions`: unclear or missing items needed for stronger interpretation.

## Anti-Hallucination Checklist

- Are all major claims backed by specific evidence?
- Are speculative points explicitly labeled as inference?
- Are missing details explicitly marked instead of guessed?
- Are conversion issues documented where they affect meaning?
- Is certainty level proportional to evidence quality?

## What Not To Do

- Do not summarize from memory of other papers.
- Do not treat assumptions as facts.
- Do not fill data gaps with typical values from the field.
- Do not hide uncertainty when the Markdown is ambiguous.
