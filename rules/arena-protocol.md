# Arena protocol (managed, not a skill)

Used by `/architect` and optionally by `/blast-radius`. Do **not** invoke `/arena` from another manual skill. Path after install:

`~/.gemini/antigravity-bestfriend/rules/arena-protocol.md`

## Model pool

Read `~/.gemini/antigravity-bestfriend/config/model-pool.json` if it exists.

- Missing file or every role is `inherit-parent` → all candidates inherit the parent model. Set `MODEL_DIVERSITY=false`. Do not invent commercial slugs.
- Same-model N candidates are allowed. Label them honestly (`candidate-1` …), not as different families.
- Never print gateway URLs, tokens, or model-mapping values. Model names are opaque aliases.

`templates/model-pool.example.json` in the product checkout is bootstrap/documentation only. It is not a runtime path.

## Phases

1. **Frame.** Name the artifact. Write a 3–6 item rubric that is gradeable. Assign each candidate its own output path (`/tmp/arena-<slug>/candidate-<n>/` or a worktree). Shared writable paths are forbidden.
2. **Fan out.** Spawn N isolated attempts with the same prompt. Each must return the artifact plus a short rationale (alternatives considered and rejected). Dropouts proceed as N-1.
3. **Cross-judge.** One read-only judge scores the rubric. Prefer a different family only when the live pool actually has one. Otherwise inherit-parent and say so.
4. **Pick.** Read every candidate. Score criterion by criterion. Prefer the cleaner boundary when tied.
5. **Graft.** Port one or two ideas from losers into the base by hand. Record grafts and rejections.
6. **Verify.** The synthesized artifact gets the same proof as any other output.

## Honesty flags

- `MODEL_DIVERSITY=false` when only one family is available.
- `DEGRADED_NO_REVIEW_PANEL` when a judge cannot be spawned.
- Do not pretend a single-model run was a multi-model arena.
