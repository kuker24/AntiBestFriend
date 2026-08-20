---
name: to-tickets
description: Break a plan, spec, or the current conversation into tracer-bullet tickets with blocking edges. Default tracker is local files under .scratch. Use after a spec, or when the user asks to break work into tickets or run /to-tickets.
when-to-use: "Use after a spec, or when the user asks to break work into tickets or run /to-tickets. Skip ordinary single-session implementation."
---

# To Tickets

Break a plan, spec, or conversation into a set of **tickets** — tracer-bullet vertical slices, each declaring the tickets that **block** it.

Default tracker is local files under `.scratch/<feature-slug>/issues/`. Do not run the missing Matt tracker-setup command. If the user asked for GitHub issues and `gh` is authenticated, publish with `/gh-axi`. Otherwise write one file per ticket locally.

## Process

### 1. Gather context

Work from whatever is already in the conversation context. If the user passes a reference (a spec path, an issue number or URL) as an argument, fetch it and read its full body and comments.

### 2. Explore the codebase (optional)

If you have not already explored the codebase, do so to understand the current state of the code. Ticket titles and descriptions should use the project's domain glossary vocabulary, and respect ADRs in the area you're touching. If Codebase Memory has no project for cwd, skip it and use repo files.

Look for opportunities to prefactor the code to make the implementation easier. "Make the change easy, then make the easy change."

### 3. Draft vertical slices

Break the work into **tracer bullet** tickets.

<vertical-slice-rules>

- Each slice cuts a narrow but COMPLETE path through every layer (schema, API, UI, tests) — vertical, NOT a horizontal slice of one layer
- A completed slice is demoable or verifiable on its own
- Each slice is sized to fit in a single fresh context window
- Any prefactoring should be done first

</vertical-slice-rules>

Give each ticket its **blocking edges** — the other tickets that must complete before it can start. A ticket with no blockers can start immediately.

**Wide refactors are the exception to vertical slicing.** A **wide refactor** is one mechanical change — rename a column, retype a shared symbol — whose **blast radius** fans across the whole codebase, so a single edit breaks thousands of call sites at once and no vertical slice can land green. Don't force it into a tracer bullet; sequence it as **expand–contract**. First expand: add the new form beside the old so nothing breaks. Then migrate the call sites over in batches sized by blast radius (per package, per directory), each batch its own ticket blocked by the expand, keeping CI green batch to batch because the old form still exists. Finally contract: delete the old form once no caller remains, in a ticket blocked by every migrate batch. When even the batches can't stay green alone, keep the sequence but let them share an integration branch that all block a final integrate-and-verify ticket — green is promised only there.

### 4. Quiz the user

Present the proposed breakdown as a numbered list. For each ticket, show:

- **Title**: short descriptive name
- **Blocked by**: which other tickets (if any) must complete first
- **What it delivers**: the end-to-end behaviour this ticket makes work
- **Risk / verification**: risk level and the `01-verification.md` profile

Ask the user:

- Does the granularity feel right? (too coarse / too fine)
- Are the blocking edges correct — does each ticket only depend on tickets that genuinely gate it?
- Should any tickets be merged or split further?

Iterate until the user approves the breakdown.

### 5. Publish the tickets

Default: one file per ticket under `.scratch/<feature-slug>/issues/<NN>-<slug>.md`, numbered from `01` in dependency order (blockers first). Each file's "Blocked by" lists the numbers/titles it depends on. Use the per-ticket file template below — one ticket per file, never a single combined file.

GitHub only if the user asked and `gh` is authenticated: publish one issue per ticket in dependency order via `/gh-axi`. Use native blocking / sub-issue links where the platform has them; otherwise set each ticket's "Blocked by" to the blocking issues.

Work the **frontier**: any ticket whose blockers are all done. For a purely linear chain that means top to bottom.

Do NOT close or modify any parent issue.

<local-ticket-template>

# <NN> — <Ticket title>

**What to build:** the end-to-end behaviour this ticket makes work, from the user's perspective — not a layer-by-layer implementation list.

**Blocked by:** the numbers/titles of the tickets that gate this one, or "None — can start immediately".

**Status:** ready-for-agent

**Risk level:** low | medium | high

**Verification profile:** FAST | STANDARD | UI | SECURITY | PERFORMANCE | RELEASE

**Spec / ADR:** path or id of the spec section and any ADR this ticket must respect

**Anchors:** stable module or symbol names (not brittle file paths). Short list only.

**Definition of done:**
- [ ] Acceptance criterion 1
- [ ] Acceptance criterion 2
- [ ] Verification profile ran and required configured checks passed

**Rollback:** what to undo if this ticket ships and must be reverted, or "not shipped yet — delete the branch"

</local-ticket-template>

<issue-template>

## Parent

A reference to the parent issue on the tracker (if the source was an existing issue, otherwise omit this section).

## What to build

The end-to-end behaviour this ticket makes work, from the user's perspective — not layer-by-layer implementation.

## Acceptance criteria

- [ ] Criterion 1
- [ ] Criterion 2

## Blocked by

- A reference to each blocking ticket, or "None — can start immediately".

## Agent-ready

- **Risk level:** low | medium | high
- **Verification profile:** FAST | STANDARD | UI | SECURITY | PERFORMANCE | RELEASE
- **Spec / ADR:** reference
- **Anchors:** stable modules or symbols
- **Definition of done:** what "done" means besides the checkboxes
- **Rollback:** how to undo a bad ship

</issue-template>

Prefer stable module and symbol anchors over file paths. File paths go stale; a short symbol list helps a fresh context. Exception: if a prototype produced a snippet that encodes a decision more precisely than prose can (state machine, reducer, schema, type shape), inline it and note briefly that it came from a prototype. Trim to the decision-rich parts — not a working demo, just the important bits.
