## Claude browser contract

Follow the browser engine rules. Invocation only:

- After this skill loads, run `browser-act` via Bash.
- `browser open` without `--headed`. Add `--headed` only if the user asks to see a window.
- Create browsers only with `--type chrome`. Never `--type chrome-direct`.
- Do not reuse a `chrome-direct` browser (including `pulse-test`).
- `stealth-extract` is allowed for sessionless fetch.
- Do not invent a raw bash one-liner as a substitute for this skill.

## Context Guard

One image per agentic tool batch. Do not batch several screenshot Reads. Prefer DOM/a11y/console before pixels. Tall pages: low-res overview, then a targeted crop in a later batch. Never auto-crop the top. Sequential A → analyze → B in one user turn is allowed.

