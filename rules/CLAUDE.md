<!-- GROKBESTFRIEND-CLAUDE:BEGIN -->
# grokbestfriend-claude router

```text
pikir dulu → bukti di repo → satu spesialis → cek hasil
```

Availability is not a reason to use a tool. One primary specialist. At most one risk specialist (`/full-audit-keamanan` **or** `/full-performance-audit`). Never print tokens, gateway URLs, or model maps. Model names are opaque aliases. Never enable `bypassPermissions`.

## Default

1. Repo evidence is enough → do the work. No specialist.
2. User typed a slash skill → load that skill. Do not substitute.
3. Choosing a workflow → `/ask-matt`.
4. Architecture DAG → Claude Plan mode, then implement in-session.
5. Interview / glossary / ADR → `/grill-with-docs` → `/to-spec` → `/to-tickets` only if asked or multi-session.
6. Ordinary implementation → this session. `/tdd` when test-first. Never auto `/matt-implement`.
7. Review → in-session. `/matt-code-review` only if two-axis asked.

## Knowledge (lazy)

repo/file → Codebase Memory (skip if no project for cwd) → Serena only if already registered and exact symbol work → Context7 for current lib docs → WebSearch/WebFetch; foreign Exa only if already connected → `/adhd` only for high-ambiguity/high-risk.

## Specialists (load one)

UI direction → `/found-this-design` then `/impeccable`. Motion → `/emil-design-eng`. Media → `/visual-studio`. Scroll/3D → `/scroll-world`. Registry → shadcn MCP. Design Intelligence is internal to Impeccable `new-work`, never a route.

Browser QA → `/browser-act`. Observed cause → `/chrome-devtools-axi` after `claude-chromium-cdp` (`127.0.0.1:9223`). Never Google Chrome. Project Playwright only if the project already has it.

Auth/secret/payment/upload/webhook/privileged/public API → `/full-audit-keamanan`. Measured LCP/INP/CLS/latency/bundle → `/full-performance-audit`. GitHub → `/gh-axi`.

## When routing is non-obvious

Read the file `~/.claude/grokbestfriend-claude/rules/00-routing.md` with the Read tool. Do not `@`-import it.

## When a verification profile is chosen

Read the file `~/.claude/grokbestfriend-claude/rules/01-verification.md` with the Read tool. Profiles: FAST, STANDARD, UI, SECURITY, PERFORMANCE, RELEASE. Missing project command = `NOT_CONFIGURED`, not PASS.

If you need operational principles or prose discipline, Read `~/.claude/grokbestfriend-claude/rules/02-engineering-principles.md` or `03-prose-discipline.md`. Do not `@`-import them.

Images, huge tool dumps, or a Context Guard stop → Read `~/.claude/grokbestfriend-claude/rules/04-context-guard.md`. One image per agentic tool batch.

There is no user `/implement`, `/code-review`, `/design`, or `/imagine` skill.
<!-- GROKBESTFRIEND-CLAUDE:END -->
