---
name: grill-with-docs
description: Relentless interview to sharpen a plan. Writes CONTEXT.md, a glossary, and ADRs as you go. Use when a feature still needs a plan, the user wants grilling, or they ask for /grill-with-docs.
when-to-use: "Use when a feature still needs a plan, an interview, a glossary, or ADRs. Skip ordinary implementation, typo fixes, and architecture DAGs (those use bundled /design)."
---
<!-- grokbuild-overlay:grill-with-docs -->

# Grill with docs

Run the interview in this session. Do not delegate to missing Matt interview primitives.

## Goal

Leave the repo with:

- `CONTEXT.md` — problem, decisions, open questions, glossary
- ADRs under `docs/adr/` (or `adr/` if that already exists) for hard-to-reverse choices

## Rules

- You gather facts. The user makes decisions.
- One question at a time when the answer branches. Batch only factual checks.
- Use the project's words. When a term is overloaded, resolve it and write it into the glossary.
- Do not implement code in this skill.
- If Codebase Memory has no project for cwd, skip it and use repo files.
- Stop when you can implement or write `/to-spec` without inventing decisions.

## Loop

1. Read `CONTEXT.md`, existing ADRs, and enough of the repo to speak the domain.
2. State the frontier: what you believe, what is undecided, what would change the design.
3. Ask the next question that most reduces that frontier.
4. After each answered decision, update `CONTEXT.md`. If the decision is hard to reverse, write an ADR.
5. Repeat until the stop condition.

## CONTEXT.md shape

```markdown
# <feature or system>

## Problem

## Decisions

## Open questions

## Glossary

## Sources
```

## ADR shape

```markdown
# ADR <nnn>: <title>

Status: accepted
Date: <ISO date>

## Context

## Decision

## Consequences
```

## After

Tell the user the paths you wrote. If the work is multi-session or they asked for tickets, offer `/to-spec` then `/to-tickets`. Otherwise they can implement in this session or type `/implement`.
