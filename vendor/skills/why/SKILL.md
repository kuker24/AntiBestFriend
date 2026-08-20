---
name: why
description: "Why this repo chose an approach: git history, ADRs, PRs, local docs. Use for /why, 'why does this repo do X', design rationale, regressions. Manual only. Official library docs use research / Context7. GitHub ops use /gh-axi."
disable-model-invocation: true
---

# Why

Investigate the motivation and intent behind **this repository's** code. Why was it built this way? What alternatives were rejected?

This is not `/research` (official docs, specs, first-party APIs). This is not `/gh-axi` (GitHub operations).

## Always available

Use these every run:

- git: `blame`, `log --follow`, merge commits
- repo docs: `CONTEXT.md`, `docs/adr/`, README, comments, tests
- `gh` **if already authenticated**: PR bodies, reviews, linked issues

Do **not** install Slack, Sentry, Datadog, Linear, Notion, or any other MCP from this skill. Optional sources only if the tool is already connected. A missing optional source is `NOT_CONFIGURED`, not a reason to add it.

## Operating posture

- Evidence before narrative.
- Precision over polish. Cite or it is inference.
- Name the gaps.
- Do not infer intent from code shape alone.

Read `references/epistemics.md` for the confidence framework.

## Step 1. Understand the target

Parse the target (file, pattern, feature, named decision) and the question (rationale, tradeoff, edge case, constraint, history). If vague, state your interpretation and proceed.

## Step 2. Establish the code anchor

- File path(s) and line range(s)
- Key symbols
- Recent commits touching the target
- PR numbers from merge commits

```bash
git blame -L <start>,<end> <file>
git log --follow -p -- <file>
git log --oneline -20 -- <file>
```

If `gh` is authenticated:

```bash
gh pr view <number> --json title,body,author,createdAt,mergedAt,labels,closingIssuesReferences,comments,reviews
```

## Step 3. Search what is actually available

Always: source control + repo docs.

If `gh` is authenticated: PRs and issues.

Optional, only if already connected: issue tracker MCP, long-form docs MCP, chat MCP, observability MCP, error tracker, analytics warehouse. Skip with an explicit `NOT_CONFIGURED` line. Do not spawn a panel of investigators for tools that are not there.

## Step 4. Present

Keep this structure. Do not collapse confidence.

**The Question.** Restate what the user asked.

**The Code in Question.** File paths, line ranges, key symbols.

**DIRECT EVIDENCE.** Claims with citations (commit, PR, ADR, `file:line`).

**INFERENCE.** Claims supported by indirect evidence. Hedge. Explain the chain.

**COMPETING HYPOTHESES.** If the record fits more than one story, list them with evidence for and against.

**UNKNOWN.** Explicit gaps. Searches that returned empty.

**SOURCES CONSULTED.** One line per source, including the ones that returned nothing or were `NOT_CONFIGURED`.
