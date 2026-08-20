---
name: ask-matt
description: Pick the GrokBuild skill or flow that fits. Use when the user asks which skill to use, which workflow, "alur apa", "ask matt", or is choosing between planning, implement, review, and design paths.
when-to-use: "Use when the user is choosing a workflow or asks which skill to run. Skip when the task is already a clear implement, review, design, or UI job."
---
<!-- grokbuild-overlay:ask-matt -->

# Ask Matt

Follow `00-routing.md`. Route only to skills installed here. Do not load every specialist. One primary specialist, plus at most one verification specialist when a risk or measured-performance trigger is on.

## Installed

**Plan:** `/ask-matt` `/grill-with-docs` `/to-spec` `/to-tickets` `/tdd` `/design` `/execute-plan`

**Write:** this session, or user `/implement`. Matt ticket loop only: `/matt-implement`

**Review:** `/review` (default). `/matt-code-review` if they asked two-axis Standards + Spec. `/code-review` if they asked the harsh slash audit.

**Design:** `/found-this-design` `/impeccable` `/visual-studio` `/scroll-world` `/emil-design-eng`

**Browser / GitHub / risk:** `/browser-act` `/chrome-devtools-axi` `/gh-axi` `/full-audit-keamanan` `/full-performance-audit` `/adhd`

**Docs / extras:** `/imagine` `/docx` `/pdf` `/pptx` `/create-skill` `/create-workflow` `/build-with-ai` `/pr-babysit` `/resume-claude` `/resume-codex` `/resume-cursor` `game-asset-*`

**Not installed — say so, then use the nearest installed skill:** `/grill-me` `/grilling` `/handoff` `/prototype` `/triage` `/diagnosing-bugs` `/wayfinder` `/improve-codebase-architecture` `/domain-modeling` `/codebase-design` `/resolving-merge-conflicts` `/research` `/to-questionnaire` `/wizard` `/wait-what` `/teach` `/writing-for-agents` `/setup-matt-pocock-skills`

## Route

1. Repo evidence is enough → do the work.
2. User typed a slash skill → load it.
3. Architecture / PR-plan DAG → `/design`, then `/execute-plan` after approval.
4. Feature needs an interview, glossary, or ADR → `/grill-with-docs`. Then `/to-spec` → `/to-tickets` only if they asked for tickets or the work is multi-session.
5. Ordinary implementation → write here. `/tdd` when test-first. Do not start `/implement` unless they typed it.
6. UI world unknown → `/found-this-design` then `/impeccable`. World already chosen → `/impeccable`.
7. A missing Matt name is the only named fit → say it is not installed. Use `/grill-with-docs`, `/implement` (if they typed it), `/review`, `/adhd`, or `/impeccable`.

## Phase boundaries

Continue if this session still holds the why. `/new` (alias `/clear`) if the window is disposable. `spawn_subagent` for a scoped AFK task. `/compact` last. `/handoff` is not installed — write a markdown note instead.

Read [PHASE-BOUNDARIES.md](PHASE-BOUNDARIES.md) for the ordered tree. Remap `/clear` to `/new`.
