---
name: arena
description: "Spawn N parallel candidates at the same task, pick a base, graft the strongest parts of the losers into it. Use for /arena, 'arena this', or when one attempt at a non-trivial artifact would lock in the wrong shape. Manual only."
disable-model-invocation: true
---

# Arena

Fan out N parallel attempts at the same task. Read every candidate end to end. Pick the strongest as the base. Graft the best ideas from the others into it. Verify the synthesized result.

Read `~/.claude/grokbestfriend-claude/rules/arena-protocol.md` first. That file is the protocol. This skill is the slash entry.

## Model pool

Read `~/.claude/grokbestfriend-claude/config/model-pool.json` if it exists.

- Missing file, or every role is `inherit-parent` → all candidates inherit the parent model. Set `MODEL_DIVERSITY=false`. Do not invent commercial slugs.
- Same-model N candidates are allowed. Label them honestly (`candidate-1` …), not as different families.
- Never print gateway URLs, tokens, or model-mapping values. Model names are opaque aliases.
- `templates/model-pool.example.json` in the product checkout is bootstrap only. It is not a runtime path.

## Start

Open a todolist with one entry per phase before launching anything.

1. Frame
2. Fan out
3. Cross-judge
4. Pick
5. Graft
6. Verify

## Phase A: Frame

The N candidates receive the same prompt, so the prompt is the contract.

1. State the artifact each candidate is producing.
2. Derive the rubric. 3–6 concrete gradeable criteria. Concrete: `Adds a --dry-run flag that skips writes`. Vague: `code is correct`.
3. Pick the runners from the live model pool (`builders`). Default inherit-parent.
4. Assign output paths. Each candidate writes to its own location (a git worktree where possible, otherwise `/tmp/arena-<slug>/candidate-<n>/`). Shared writable paths are forbidden.

## Phase B: Fan out

Spawn all N isolated attempts with the same prompt, each with the shared grounding, its own output path, and instructions to produce both the artifact and a short rationale.

The rationale is mandatory. Each rationale names the alternatives the candidate considered and what it rejected.

If a candidate fails to produce output, proceed with N-1 and note the dropout.

## Phase C: Cross-judge

After all Phase B candidates complete, pick a judge from the live pool (`judges`). Prefer a different family only when the live pool actually has one. Otherwise inherit-parent and set `DEGRADED_NO_REVIEW_PANEL` if a judge cannot be spawned.

The judge sees the rubric and the candidates by path label, scores each criterion, and recommends a base. Do not spawn the judge while candidates are still writing.

## Phase D: Pick a base

Read every candidate end to end before picking. Score criterion by criterion. Compare against the cross-judge. Prefer the cleaner boundary or smaller surface when two feel tied.

Record the pick and the reason in a short synthesis note.

## Phase E: Graft

Walk each losing candidate once more. Port one or two ideas into the base by hand. Record grafts and rejections.

When N candidates converge, ship the consensus shape. When they wildly diverge, Phase A was under-specified. Reframe and re-run rather than averaging.

## Phase F: Verify

The synthesized artifact gets the same proof as any other output. The arena does not earn a pass.

## Outputs

One synthesized artifact. One short synthesis note naming the base, the grafts, the rejections, the dropouts if any, `MODEL_DIVERSITY`, and the verification result.
