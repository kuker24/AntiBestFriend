---
name: figure-it-out
description: "Design an auditable playbook when no narrower skill fits: a large migration, an ambitious multi-part change, or work a human reviews after stepping away. Use for /figure-it-out. Manual only. Do not inflate a small task."
disable-model-invocation: true
---

# Figure it out

When the task matches no narrower playbook, design one. The deliverable before any code is the workflow itself: phases that scale rigor to the task, a hypothesis loop, and a decision trail a human can audit.

Do not inflate a small task. A typo, a known-cause bug, ordinary CRUD, or a single-file fix is not this skill.

Read `~/.claude/grokbestfriend-claude/rules/02-engineering-principles.md` first. Log the run with `~/.claude/grokbestfriend-claude/rules/decision-log-protocol.md`. Do **not** invoke `/decision-log`, `/architect`, `/arena`, or `/why` from this skill.

## Start

Open a todolist with the phases below. Do not look for poteto-mode, principle-as-skills, or a companion plugin.

## Phase A: Frame

Do not start the run until you can state:

- The definition of done as a falsifiable predicate. "Done well" has to be checkable.
- Scope, quantified: rough units and effort, plus blockers.
- The rigor level, biased high for one-way doors and high blast radius.

Present the framing before committing to a long run.

## Phase B: Design the workflow

Decompose into atomic, independently-landable units. Sequence riskiest-unknown-first. Scaffold and verification come before features.

- Build the verification harness before the work, with a baseline from the pre-change state.
- For one-way-door design decisions, follow `~/.claude/grokbestfriend-claude/rules/arena-protocol.md` **inline**. Do not invoke `/arena` or `/architect`. Skip the bake-off for mechanical work whose shape is already concrete.
- Parallelize only across genuine seams. Each worker gets its own worktree or branch.
- Write the designed phase list down. That list is what the human reviews.

## Phase C: Run the loop

Each unit is an experiment: state the hypothesis, make the smallest change, measure against the predicate on the real artifact, keep it if it advanced, revert it if it did not.

- Verify by inspecting the artifact, never a self-report.
- A verdict is VERIFIED, NOT VERIFIED, or INCONCLUSIVE. Inconclusive is not a pass.

## Phase D: Keep the audit trail

Follow the decision-log protocol: one TSV, one row per decision, evidence as pointers, no hidden reasoning. Prefer `~/.claude/skills/decision-log/scripts/log.sh` when that helper exists. Commit the trail only when a reviewer needs it.

## Phase E: Verify and hand back

Check the whole against the Phase A predicate on the real product, not just the harness. Encode any recurring correction as a gate, a lint rule, a check, or a script.

**Reply:** the playbook you designed, the rigor level and why, the decision-trail path, what is verified against the predicate, and what is still open.
