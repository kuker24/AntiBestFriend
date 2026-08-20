---
name: architect
description: "Sketch types, signatures, and module structure before code, then stay in the loop while implementation fills in. Use for /architect when jumping to code would lock in the wrong shape. Manual only. Module/seam vocabulary lives in codebase-design; this skill is the bake-off."
disable-model-invocation: true
---

# Architect

Design before implementing. Sketch types, function signatures, class shapes, and module boundaries with `not implemented` bodies and pseudocode. Compare at least two structurally distinct candidates, then fill in code against the chosen sketch. If implementation proves the sketch wrong, throw it out and redesign.

Do **not** invoke `/arena` or `/why`. Follow `~/.claude/grokbestfriend-claude/rules/arena-protocol.md` for the compare step. Use **domain-modeling** and **codebase-design** as shared disciplines (glossary, module/seam/interface vocabulary) when those apply. Read `~/.claude/grokbestfriend-claude/rules/02-engineering-principles.md` for operational gates.

This is not `/codebase-design` (one module/seam/interface question). This is not Plan mode (architecture DAG / PR plan).

## Start

Open a todolist with one entry per phase.

1. Ground
2. Sketch
3. Agree
4. Implement
5. Scrap

## Phase A: Ground the problem

Build a real mental model of every system the new code touches. Trace callers, owners, and data from the repo (and Codebase Memory if a project exists for cwd). Naming a file is not grounding.

If the design redefines ownership or layering, gather existing rationale from repo docs, ADRs, and git. Do not invoke `/why`.

Skip Phase A only when the work is genuinely greenfield with no surrounding system.

## Phase B: Sketch

Follow the arena protocol (frame / fan-out / cross-judge / pick / graft / verify) **inline**. Do not load `/arena`.

Pass `references/runner-prompt.md` as each candidate's prompt. Each candidate produces a design package shaped per `references/rationale-template.md`: the caller's usage written first, then the type sketch, function signatures, module map, and prose rationale.

Read `~/.claude/grokbestfriend-claude/config/model-pool.json`. Missing or inherit-parent → `MODEL_DIVERSITY=false`. Same-model N candidates are allowed. Do not invent commercial slugs.

Require at least two structurally distinct candidates before synthesis. Whole-shape alternatives, not point fixes inside one shape.

Screen every candidate against [`references/design-red-flags.md`](references/design-red-flags.md). Reject or revise shallow modules, information leakage, temporal decomposition, and pass-through methods.

Compare viable candidates on interface depth. Prefer the design that hides more complexity behind a smaller public surface.

## Phase C: Agree (opt-in)

Default: proceed to implementation with the synthesized design.

Opt in to a checkpoint when the invoker asks ("/architect with checkpoint", "stop and show me before implementing"). Then surface the synthesized design and pause.

If the human pushes back, treat that as Phase A evidence. Re-ground and re-run Phase B before writing more code.

Do not invoke `/interrogate` from this skill.

## Phase D: Implement against the sketch

Replace `not implemented` bodies with code. The synthesized sketch is the contract.

Deviations are signal. Surface them; do not bolt them on silently.

## Phase E: Scrap when the architecture is wrong

If implementation keeps producing friction the sketch cannot absorb, throw the sketch out. The signal is a *pattern*, not single instances:

- The same workaround appearing repeatedly.
- Multiple unrelated edge cases that all need special-case branches.
- Types that need escape hatches to compile.
- Callers having to know the abstraction's internal rules.
- Two or more independent Phase D deviations of the same shape.

When you scrap:

1. Re-trace what was built. Implementation lessons enter the new design as inputs.
2. Redesign as if the new constraints had been day-one assumptions.
3. Subtract before adding. The new sketch should be smaller than the old one before it grows.
4. Return to Phase B.

## Outputs

The caller's usage is written first and the type sketch derived from it. One file with new types and signatures for small changes; module map plus type definitions for larger work. The rationale ships alongside, shaped per `references/rationale-template.md`.
