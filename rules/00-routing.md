# Antigravity CLI specialist routing (antigravity-bestfriend)

Read this file only when routing is non-obvious. Do not load every specialist.

Use tools lazily. Prefer current repository evidence before external tools. Use one primary specialist per problem. If a risk trigger is active (auth, authorization, secrets, public APIs, payment, upload, webhook, privileged operations), also load at most one verification specialist (`/full-audit-keamanan`). If the concern is a measured performance regression (LCP, INP, CLS, latency, bundle, query, memory), the verification specialist is `/full-performance-audit`. Do not load a second implementation specialist. Availability is not a reason to activate a tool.

```text
pikir dulu → bukti di repo → satu spesialis → cek hasil
```

Do not infer a model provider from a logical model name. Treat custom-gateway aliases as opaque. Never print tokens, gateway URLs, or model-mapping values.

## Default path

1. **Repo evidence is enough** → do the work. No specialist. Verification: FAST or STANDARD.
2. **User typed a slash skill** → load that skill. Do not substitute.
3. **User is choosing a workflow** (`which skill`, `alur apa`, `ask matt`) → load `/ask-matt`.
4. **Architecture / PR-plan DAG** → Antigravity /plan mode. After approval → implement in this session. There is no bundled `/design` or `/execute-plan`.
5. **Feature still needs a plan** (interview, glossary, ADR) → `/grill-with-docs`. Then `/to-spec` → `/to-tickets` only if the user asked for tickets or the work is multi-session.
6. **Ordinary implementation** → write in this session. Use `/tdd` when test-first. Do **not** auto-start `/matt-implement`. There is no user `/implement` skill.
7. **User asked for the Matt ticket loop** → `/matt-implement` only for a `/to-tickets` ticket.
8. **Review** → in-session review. `/matt-code-review` only if the user asked for two-axis Standards + Spec. There is no user `/code-review` skill.
9. **Verification** → pick a profile, then Read `~/.gemini/antigravity-bestfriend/rules/01-verification.md`. Required configured failures block a completion claim.

## Knowledge

- Repository structure and impact: MCP `codebase-memory-mcp` first. If Codebase Memory has no project for cwd, skip it and use repo files. Do not retry.
- Exact cross-file symbol work: MCP `serena` only if already registered and only after Codebase Memory and simpler repo evidence are not enough. Do not run Serena and Codebase Memory as the main brain at the same time. If Serena is absent, say so; do not `agy mcp add serena` from a session unless the user asked. Helper: `agy-bestfriend serena enable`.
- Current library or framework docs: MCP `context7` only when repo evidence is insufficient.
- Installable React/shadcn registry items: MCP `shadcn` (pinned CLI `shadcn@4.18.0`). Search, inspect, then install. Context7 stays documentation.
- Broader web research: built-in `WebSearch` and `WebFetch`. MCP `exa` is foreign/pre-existing and ON_DEMAND. Use it only if already connected and research needs it. Never add or remove `exa`.
- Hard, high-impact, divergent decisions, fuzzy debugging, API or schema alternatives, trap detection: `/adhd` on demand only. Skip ADHD for typos, ordinary CRUD, or bugs with a known cause.
- Official library, spec, or first-party API facts: `/research` (Context7 when repo evidence is not enough). Why *this repo* chose an approach: suggest `/why` (manual). Do not mix the two.
- Fuzzy or conflicting domain terms, glossary, CONTEXT.md / ADR writing: `/domain-modeling`. Full product interviews that should leave CONTEXT.md/ADRs: `/grill-with-docs`.
- Module, interface, seam, testability, abstraction: `/codebase-design`. Multi-sketch bake-off: suggest `/architect` (manual). Do not auto-start `/architect`.
- Throwaway evidence for one design question: `/prototype`. Skip ordinary implementation, ADHD, and `/arena`.
- Unknown / hard bugs, regressions, measured slowdown: `/diagnosing-bugs`. Skip typos, known-cause, and test-first known fixes (`/tdd`).
- Authoring SKILL.md / CLAUDE.md / AGENTS.md / skill descriptions / context pointers: `/writing-for-agents`. Workflow choice stays `/ask-matt`.

## UI and browser

- Matching or choosing a visual direction from the local design bank (Refero / Motionsites): `/found-this-design` first. Then `/impeccable` after a pick. Bank root comes from `~/.gemini/antigravity-bestfriend/config/design-bank.json` (optional override `GROK_DESIGN_BANK` / `CLAUDE_DESIGN_BANK`).
- Visual UI once a world is chosen or the brief is already visual: `/impeccable` first.
- Design Intelligence is an internal, lazy retrieval stage of Impeccable `new-work`, never a primary route or specialist.
- Installable UI components: MCP `shadcn` only. Do not add Magic UI, Kibo, 21st.dev, or community UI MCP servers.
- Use the hub only when cwd has `components.json`. Never silent `shadcn init` on this adapter, a backend or Python tree, or a non-UI cwd.
- Scroll-scrub fly-through or 3D-world landing: `/scroll-world`.
- Photoreal stills / ads / identity with no UI surface: `/visual-studio`.
- Motion after Impeccable: `/emil-design-eng`.
- Image/video generation: use Antigravity-native image tools if the session exposes them. Otherwise write prompt files and mark DEGRADED. Do not invent `image_gen`.
- Exploratory real-user QA: `/browser-act`. Load the skill before any `browser-act` command. Never `--type chrome-direct`.
- Observed browser cause: `/chrome-devtools-axi` after `agy-chromium-cdp start` on `http://127.0.0.1:9223`. Never Google Chrome.
- Deterministic browser regression: project Playwright only if that project already has it.

## Risk and GitHub

- Auth, authorization, secrets, public APIs, payment, upload, webhook, privileged operations: `/full-audit-keamanan` plus `semgrep`, `osv-scanner`, `gitleaks`. Do not print secret values.
- Measured regressions in bundle, query, memory, latency, or Core Web Vitals (LCP, INP, CLS): `/full-performance-audit`. FID is legacy.
- GitHub issues, PRs, Actions, releases: `/gh-axi` via `npx -y gh-axi`. If `gh` is not logged in, ask the human to run `gh auth login`.

## Matt flow versus Claude natives

- Planning and tickets stay on Matt skills: `/grill-with-docs`, `/to-spec`, `/to-tickets`, `/tdd`.
- Architecture DAG: Antigravity /plan mode, not a skill.
- Ordinary writes stay in this session. `/matt-implement` is only for a ticket that `/to-tickets` produced.
- Default review is in-session. Two-axis: `/matt-code-review`.
- Choosing a workflow: `/ask-matt`. Route only to skills that exist. Missing names (`/grill-me`, `/handoff`, `/triage`, `/wayfinder`, `/setup-matt-pocock-skills`, `/bro`, `/poteto-mode`, `/swarm`, …) are not available.
- Manual / slash-only (do not auto-start): `/blast-radius`, `/create-verification-skill`, `/maintain-verification-skill`, `/unslop`, `/technical-writing`, `/arena`, `/interrogate`, `/architect`, `/why`, `/reflect`, `/figure-it-out`, `/decision-log`, `/wizard`, `/wait-what`, `/improve-codebase-architecture`. Suggest them when the user names the job; do not load them as the default path.

## Grok bundled names (do not fake)

| Grok name | Claude |
| --- | --- |
| `/design` `/execute-plan` | Plan mode, then in-session write |
| `/implement` | in-session write (no user skill) |
| `/review` `/code-review` | in-session review; `/matt-code-review` if two-axis |
| `/imagine` | NOT_APPLICABLE; directors stay visual-studio / scroll-world |
| `/docx` `/pdf` `/pptx` | in-session write or NOT_APPLICABLE |
| `/pr-babysit` | `/gh-axi` |
| `game-asset-*` `/resume-*` `/build-with-ai` | NOT_APPLICABLE |

## Plugins and extra MCP

- No extra marketplace plugins. Foundation = skills + MCP + thin CLAUDE.md + runtime helpers.
- User MCP: `codebase-memory-mcp`, `context7`, and `shadcn` on; `serena` absent until a human enables it; `exa` foreign.
- Never auto-edit rules or skills from a learning log.

## Do not

- Do not enable every specialist in one turn.
- Do not `@`-import the full routing or verification files into CLAUDE.md.
- Do not register 21st.dev, Magic UI MCP, Kibo MCP, or unofficial React Bits / Aceternity MCP.
- Do not run `shadcn init` on this adapter, backend, or Python repositories.
- Do not use Serena before Codebase Memory.
- Do not use ADHD for ordinary work.
- Do not use Emil for static UI, or Impeccable for motion-only work.
- Do not use BrowserAct as a stand-in for project Playwright.
- Do not claim TypeScript, Vitest, coverage, Knip, or Playwright exist unless the current project has them.
- Do not copy or print tokens, gateway URLs, or model-mapping values.
- Do not depend on `~/.grok` at runtime.
