---
name: interrogate
description: "Adversarial multi-reviewer challenge of a pinned change. Use for /interrogate, 'adversarial review', or 'tear this apart'. Do not auto-apply. Manual only. Default two-axis review is /matt-code-review."
disable-model-invocation: true
---

# Interrogate

Spawn independent reviewers to adversarially review code changes. The deliverable is a synthesized verdict. Do **not** auto-apply changes.

This is not `/matt-code-review` (two-axis Standards + Spec of a pinned diff). Use that when the user asked for those two axes.

## Model pool

Read `~/.claude/grokbestfriend-claude/config/model-pool.json` if it exists. Use `reviewers`. Missing file or `inherit-parent` → inherit the parent model. Same-model N reviewers are allowed; label them `reviewer-1` … and set `MODEL_DIVERSITY=false`. Do not invent commercial slugs. Never print gateway URLs or model maps.

If a review panel cannot be spawned, run one lead review in this session and mark `DEGRADED_NO_REVIEW_PANEL`.

## Step 1. Determine scope

- If the user points at specific files or a diff, use that.
- If on a feature branch, run `git diff main...HEAD` (or the appropriate base) for the full changeset.
- If the user's message references recent work, gather the relevant files.

## Step 2. State the intent

Write one clear paragraph of what the code is trying to accomplish. Reviewers challenge whether the work achieves the intent well, not whether the intent itself is correct. If unsure, ask the user.

## Step 3. Spawn reviewers

Launch reviewers from the live pool. If the pool is inherit-parent only, spawn N same-model reviewers or fall back to one lead review (`DEGRADED_NO_REVIEW_PANEL`).

Fill `references/reviewer-prompt.md` with:

1. The stated intent
2. The diff or file contents
3. The review rubric from `references/rubric.md`
4. The code-quality lens from `references/code-quality-review.md`

The same filled template goes to all reviewers.

## Step 4. Synthesize

1. Parse all findings.
2. Consensus (2+ independent reviewers) is highest signal.
3. Lone-model findings stay, at lower confidence.
4. Deduplicate.
5. Note disagreements.

## Step 5. Lead judgment

Read `references/lead-judgment.md`. Categorize every finding:

- **ACT_ON** — correctness, security, or maintainability that would block a real PR.
- **CONSIDER** — legitimate, cost unclear.
- **NOTED** — valid but not actionable now.
- **DISMISSED** — wrong, nitpicky, or missing context. Brief why.

Do not auto-apply any finding.

## Output

### Intent
> [paragraph from Step 2]

### Reviewers
- Reviewer [label]: [opaque alias or inherit-parent], [N findings]

### ACT_ON
### CONSIDER
### NOTED
### DISMISSED
### Agreement Map
