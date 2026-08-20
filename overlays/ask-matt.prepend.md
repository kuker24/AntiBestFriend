<!-- grokbestfriend-claude-overlay:ask-matt -->

# Ask Matt

Follow the thin router in `~/.claude/CLAUDE.md`. If routing is non-obvious, Read `~/.claude/grokbestfriend-claude/rules/00-routing.md`. Route only to skills installed here. Do not load every specialist. One primary specialist, plus at most one verification specialist when a risk or measured-performance trigger is on.

## Installed

**Plan:** `/ask-matt` `/grill-with-docs` `/grilling` `/to-spec` `/to-tickets` `/tdd` · architecture DAG = Claude Plan mode

**Write:** this session. Matt ticket loop only: `/matt-implement`. Test-first: `/tdd`.

**Review:** in-session (default). `/matt-code-review` if they asked two-axis Standards + Spec. `/interrogate` for adversarial multi-review (manual).

**Design:** `/found-this-design` `/impeccable` `/visual-studio` `/scroll-world` `/emil-design-eng`

**Engineering (auto when the description matches):** `/diagnosing-bugs` `/domain-modeling` `/codebase-design` `/writing-for-agents` `/research` `/prototype`

**Engineering (manual / slash only):** `/architect` `/arena` `/blast-radius` `/why` `/figure-it-out` `/decision-log` `/improve-codebase-architecture` `/create-verification-skill` `/maintain-verification-skill` `/technical-writing` `/unslop` `/reflect` `/wizard` `/wait-what`

**Browser / GitHub / risk:** `/browser-act` `/chrome-devtools-axi` `/gh-axi` `/full-audit-keamanan` `/full-performance-audit` `/adhd`

**Not installed — say so, then use the nearest installed skill:** `/design` `/execute-plan` `/implement` `/review` `/code-review` `/imagine` `/docx` `/pdf` `/pptx` `/grill-me` `/handoff` `/triage` `/wayfinder` `/bro` `/poteto-mode` `/swarm` `/setup-matt-pocock-skills` `/pr-babysit` `/create-skill` `/create-workflow` `/build-with-ai` `/resume-claude` `/resume-codex` `/resume-cursor` `game-asset-*`

## Route

1. Repo evidence is enough → do the work.
2. User typed a slash skill → load it.
3. Architecture / PR-plan DAG → Claude Plan mode, then implement in-session after approval.
4. Feature needs an interview, glossary, or ADR → `/grill-with-docs`. Then `/to-spec` → `/to-tickets` only if they asked for tickets or the work is multi-session.
5. Ordinary implementation → write here. `/tdd` when test-first. Do not start `/matt-implement` unless they are on a `/to-tickets` ticket.
6. UI world unknown → `/found-this-design` then `/impeccable`. World already chosen → `/impeccable`.
7. Official library/docs fact → `/research` (Context7). Why *this repo* chose an approach → `/why` (manual).
8. A missing Matt/Pstack name is the only named fit → say it is not installed. Use `/grill-with-docs`, in-session write, in-session review, `/adhd`, or `/impeccable`.

## Phase boundaries

Continue if this session still holds the why. `/clear` if the window is disposable. Agent/Task for a scoped AFK task. `/compact` last. `/handoff` is not installed — write a markdown note instead.
