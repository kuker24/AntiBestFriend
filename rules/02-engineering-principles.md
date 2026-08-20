# Engineering principles (managed, Read on demand)

Read this file only when a skill or the user asks for operational principles. Do not `@`-import it. Path after install:

`~/.gemini/antigravity-bestfriend/rules/02-engineering-principles.md`

These are working rules, not an essay. Apply the smallest set that changes the next action.

1. **Smallest change.** Prefer the edit that solves the stated problem and nothing else.
2. **Foundational thinking.** Scaffold and verification before features when the shape is still wrong.
3. **Subtract before add.** Delete or collapse a wrong layer before introducing a new one.
4. **First principles.** When the current shape fights the work, redesign from the constraint, not from the last patch.
5. **Domain first.** Name the real nouns and seams before inventing modules.
6. **Boundary discipline.** Hide complexity behind a small public surface. Do not leak internals to callers.
7. **Idempotency.** Operations that may retry must be safe to run twice.
8. **Prove it.** A claim needs an artifact: test, command output, screenshot, commit, or file:line.
9. **Root cause.** Fix the cause. Do not paper over the symptom unless the user asked for a temporary guard.
10. **Verifiable units.** Land work in independently checkable pieces. Do not batch verification at the end.
11. **Guard context.** Load one specialist. Do not dump every skill into the window.
12. **Encode lessons.** Recurring corrections become a gate, lint, test, or script — not a memory of “be careful”.
13. **Exhaust the design space only when warranted.** Two structurally different sketches for one-way-door design. Skip for mechanical work whose shape is already concrete.
