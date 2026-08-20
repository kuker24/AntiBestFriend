# Decision-log protocol (managed, not a skill)

Used by `/figure-it-out` and any long unattended run that needs an audit trail. Do **not** invoke `/decision-log` from another manual skill unless the user typed that slash. Path after install:

`~/.claude/grokbestfriend-claude/rules/decision-log-protocol.md`

## What this is

One append-only TSV of **operational decisions**. Not a dump of hidden reasoning. Never ask the model to reveal chain-of-thought or “think out loud for the log”.

Columns:

| ts | phase | decision | why | evidence | result |
| --- | --- | --- | --- | --- | --- |

- **ts** — ISO8601 UTC
- **phase** — workstream name
- **decision** — what was chosen or done, one line
- **why** — plain reason (constraint, measurement, user call). Not a principle-skill tag.
- **evidence** — pointer only: commit SHA, `file:line`, test name, artifact path, log path, PR number
- **result** — `tests green`, `reverted`, `INCONCLUSIVE`, `open`, a measured delta

## Where

Default: `decisions.tsv` in the work dir, or `.audit/<task-slug>.tsv`. Leave it uncommitted unless a reviewer needs the trail.

## How to write a row

Prefer `~/.claude/skills/decision-log/scripts/log.sh <logfile> <phase> <decision> <why> <evidence> <result>` when that skill is installed. The helper:

- writes the header on first use
- strips tabs/newlines
- prefixes cells that start with `=`, `+`, `-`, or `@` with a single quote (spreadsheet formula injection)

## Transcript

If you audit the log against the session, use only the **active** transcript path the system prompt names. Do not glob `~/.claude/projects/*` or `~/.cursor/projects/*`. If no safe path exists, write a short session digest instead.

## Rules

- One row = one decision or checkpoint.
- Append-only. A wrong call gets a new row.
- Do not log hidden reasoning, scratch thoughts, or every tool call.
