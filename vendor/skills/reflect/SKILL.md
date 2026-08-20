---
name: reflect
description: "Mine this conversation for durable learnings, classify them, show them, and wait for explicit approval before any skill edit. Use for /reflect. Manual only. Never auto-edit skills."
disable-model-invocation: true
---

# Reflect

Mine the current conversation for durable learnings. Classify them. **Show the user. Wait for explicit approval.** Only then edit.

Do not auto-edit skills. Do not glob private histories. Do not use Cursor `create-skill`. Skill edits, once approved, follow **writing-for-agents** discipline (`SKILL.md` / descriptions / pointers).

## When to invoke

- The user said "reflect" or "/reflect".
- A complex task just landed cleanly and the recipe is worth keeping.
- The agent hit dead ends, found the working path, and the path generalizes.
- The user corrected the agent's approach mid-task.

Skip when the conversation is trivial, off-topic, or already covered by an existing skill the parent followed correctly. One-offs are not learnings.

## Process

### 1. Locate the active transcript

Use only the **active** transcript path the system prompt names. Do not glob `~/.claude/projects/*` or `~/.cursor/projects/*`. If no safe path resolves, write a tight digest of **this** session and use that.

### 2. Review

Read this session (or the digest). Optionally spawn isolated reviewers from `~/.claude/grokbestfriend-claude/config/model-pool.json`. Missing pool or inherit-parent → review inline and set `MODEL_DIVERSITY=false`. Do not invent commercial slugs.

Prompt templates live in `references/` (judgment, tooling, divergent, synthesizer). Reviewers must not write files.

### 3. Classify

Every finding is one of:

- **STRUCTURAL** — a lint rule, script, metadata flag, or runtime check would enforce it better than a skill bullet. File as BACKLOG unless the user asks to implement the gate now.
- **SKILL** — a durable edit to an existing owned skill or a new skill draft.
- **BACKLOG** — tracker item, not a skill edit.

### 4. Show the user. Stop.

Present the full STRUCTURAL / SKILL / BACKLOG list. Wait for **explicit approval** of which subset to apply. The user may redirect or reject everything.

**Do not edit any skill before that approval.** Auto-filing a tracker is also off unless the user asked.

### 5. Apply only the approved SKILL items

- Trivial existing-skill edit (one-line bullet, stale fact): parent does it.
- Substantive skill edit: follow writing-for-agents. Do not invent a Cursor `create-skill` loop.
- New skill: draft a SKILL.md and show it; do not register it as owned product unless the user asked to vendor it.

If this environment has `lib/validate_skills.py`, run it on every touched owned skill before declaring done.

### 6. Summarize

- Edits applied (only approved ones): path + one line.
- Drafts shown, not applied.
- BACKLOG items listed, not filed unless asked.
- Dropped findings + reason.
