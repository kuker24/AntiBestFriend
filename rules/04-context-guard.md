# Context Guard

Read this file when a turn will view images, or a previous batch was stopped by Context Guard.

```text
PREVENT > CIRCUIT BREAK (image budget)
```

## What Context Guard Actually Does

Context Guard is an image budgeting hook registered via Antigravity lifecycle hooks (`PreToolUse`). It:

- **Limits images to one per agentic tool batch.** Sequential A → analyze → B in one user turn is allowed. A+B+C in one parallel batch is not.
- **Derives smaller images** when the source exceeds size caps (long edge ≤ 1200px, file ≤ 384KiB).
- **Denies** a second image in the same batch.

Context Guard does **not** rewrite tool output, compact context, or manage token budgets. Those capabilities are not available in the current Antigravity hook surface.

## Rules

1. **One image per agentic tool batch.** Sequential A → analyze → B in one user turn is allowed. A+B+C in one parallel batch is not.
2. Prefer DOM, a11y tree, console, and network before pixels.
3. Tall screenshots: low-res overview first, then a targeted crop in a later batch. Do **not** auto-crop the top.
4. Caps: long edge ≤ 1200px **and** file ≤ 384KiB. If Context Guard denies a raw image, retry only the derived path it names.
5. Do not claim a global token meter. Batch/turn numbers are **new payload** only.
