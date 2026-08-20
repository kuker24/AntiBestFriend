---
name: research
description: "Investigate a question against official docs, specs, or first-party APIs and write cited Markdown if asked. Use for external/library facts. Skip why *this repo* chose an approach (/why)."
---

Investigate against **primary sources** first: official docs, source code, specs, first-party APIs. Follow every claim back to the source that owns it.

Use a subagent if this session supports one; otherwise research inline. Do not require a background agent.

Current library or framework docs: MCP `context7` when repo evidence is not enough. Broader web: `WebSearch` / `WebFetch`. Foreign `exa` only if already connected.

If the user asked for a note, write one Markdown file in the repo (match existing convention). Cite each claim. If they only wanted an answer, do not create a file.

This is not `/why`. Repo history, PRs, and local design rationale stay on `/why`.
