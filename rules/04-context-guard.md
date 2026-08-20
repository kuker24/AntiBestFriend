# Context Guard

Read this file when a turn will Read images, dump large tool output, or a previous batch was stopped by Context Guard.

```text
PREVENT > REDUCE > OFFLOAD > CIRCUIT BREAK > AUTOCOMPACT
```

## Rules

1. **One image per agentic tool batch.** Sequential A → analyze → B in one user turn is allowed. A+B+C in one parallel batch is not.
2. Prefer DOM, a11y tree, console, and network before pixels.
3. Tall screenshots: low-res overview first, then a targeted crop in a later batch. Do **not** auto-crop the top.
4. Caps: long edge ≤ 1200px **and** file ≤ 384KiB. If Context Guard denies a raw image, retry only the derived path it names.
5. Do not claim a global token meter. Batch/turn numbers are **new payload** only.
6. Oversized unknown tool output stops the loop. Do not retry the same call.
7. Autocompact is last resort. It runs at the start of a turn, not mid-batch.
8. Circuit **halt** is for a fat batch, multi-image, or unknown oversized. Sequential QA in one user turn may accumulate past the turn cap on small payloads — that warns and continues (pressure valve), it does not stop the loop.

This rule does not change `CLAUDE_CODE_MAX_CONTEXT_TOKENS` or `autoCompactWindow`.
