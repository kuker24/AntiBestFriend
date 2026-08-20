<!-- grokbestfriend-claude-overlay:grill-with-docs -->

# Grill with docs

Run the interview in this session. Compose two owned disciplines:

- `/grilling` — design-tree + frontier rounds (one frontier per round; facts via tools, decisions via the user)
- `/domain-modeling` — glossary, CONTEXT.md, ADRs for hard-to-reverse choices

Use `/codebase-design` only when the conversation reaches a module, interface, or seam. Architecture DAGs still use Claude Plan mode, not this skill.

## Goal

Leave the repo with:

- `CONTEXT.md` — problem, decisions, open questions, glossary
- ADRs under `docs/adr/` (or `adr/` if that already exists) for hard-to-reverse choices

## Rules

- You gather facts. The user makes decisions.
- One question at a time when the answer branches. Batch only factual checks. A grilling frontier round may batch independent questions.
- Use the project's words. When a term is overloaded, resolve it and write it into the glossary.
- Do not implement code in this skill.
- If Codebase Memory has no project for cwd, skip it and use repo files.
- Architecture DAGs use Claude Plan mode, not this skill.
- There is no Grok `/implement`. Ordinary writes stay in-session after the interview.
- Stop when you can implement or write `/to-spec` without inventing decisions.

## Loop

1. Read `CONTEXT.md`, existing ADRs, and enough of the repo to speak the domain.
2. State the frontier: what you believe, what is undecided, what would change the design.
3. Ask the next question (or independent frontier) that most reduces that frontier.
4. After each answered decision, update `CONTEXT.md`. If the decision is hard to reverse, write an ADR.
5. Repeat until the stop condition.

## CONTEXT.md shape

```markdown
# <feature or system>

## Problem

## Decisions

## Open questions

## Glossary
```
