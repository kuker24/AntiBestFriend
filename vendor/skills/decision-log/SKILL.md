---
name: decision-log
description: "Keep a reviewable operational decision trail for long-running work: a TSV log with one row per decision (what, why, evidence, result). Use for /decision-log. Do not record hidden reasoning."
disable-model-invocation: true
---

# Decision log

For work a human reviews after the fact, a decision trail lets them reconstruct what was decided, why, and on what evidence, without rerunning the work or reading the whole transcript.

Read `~/.claude/grokbestfriend-claude/rules/decision-log-protocol.md`. That file is the protocol. This skill is the slash entry.

Never ask the model to reveal chain-of-thought, hidden reasoning, or "think out loud for the log". Log **operational decisions** only.

## The format

A single TSV file, one row per decision. Cells stay single-line. Evidence is a pointer, not prose.

Copy `references/decision-log-template.tsv` (the header row) to start a clean log. Columns:

- **ts.** ISO8601 timestamp.
- **phase.** The phase or workstream.
- **decision.** What was chosen or done, one line.
- **why.** The reason in plain words. A constraint, a measurement, or a user call. Not a principle-skill tag.
- **evidence.** A link or path that proves it: commit SHA, PR number, `file:line`, test name, artifact path, log path. Never a paragraph.
- **result.** The outcome or predicate state: `tests green`, `reverted`, `pixel-diff 0`, `INCONCLUSIVE`, `open`.

An example, illustration only; do not copy these rows into a real log.

```
ts	phase	decision	why	evidence	result
2026-05-24T09:02:00Z	frame	counted the work first, about 100 components and roughly 75 hours	wanted to know the size before starting a long run	commit 3a9f1c2	found 5 things to sort out before starting
2026-05-24T09:40:00Z	harness	took screenshots of the old version before changing anything	so we can compare old against new	scripts/snapshot.sh, baseline/	saved 120 reference screenshots
```

## Logging a row

Use the helper so rows stay well-formed: `scripts/log.sh <logfile> <phase> <decision> <why> <evidence> <result>`. It stamps `ts`, writes the header on first use, strips stray tabs/newlines, and prefixes any cell starting with `=`, `+`, `-`, or `@` with a single quote so a reviewer opening the log in a spreadsheet does not trigger formula execution.

Log decision points and checkpoints, not every action: a fork chosen, a unit completed with its verification result, a pivot or revert, a blocker, a gate fixed. Skip the trivial.

## Where it lives

By default the log is a working artifact, not committed. Keep it at `decisions.tsv` in the work dir, or `.audit/<task-slug>.tsv`. Commit it only when a reviewer needs the trail to trust the result.

## Rules

- One row is one decision or checkpoint.
- Append-only. A wrong call gets a new row that supersedes it.
- Prefer evidence produced by committed scripts over hand-made one-offs.

## Audit the log against the transcript

If you audit the log against the session, use only the **active** transcript path the system prompt names. Do not glob `~/.claude/projects/*` or `~/.cursor/projects/*`. If no safe path exists, write a short session digest instead.

Walk the log against what actually happened:

- Every row maps to a real action. Cut invented entries.
- Each row's evidence resolves.
- A fork, pivot, or abandoned approach that shaped the work but is not logged is a gap. Add it.

Fix the log, not the story.

## Reviewing the trail

Read top to bottom, follow the evidence pointers, spot-check. `column -s$'\t' -t decisions.tsv` renders it in a terminal.
