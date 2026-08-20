---
name: to-spec
description: Turn the current conversation into a spec and publish it locally under .scratch — no interview, just synthesis of what you already discussed. Use after grilling, or when the user asks for a spec or /to-spec.
when-to-use: "Use after /grill-with-docs, or when the user asks to write a spec or run /to-spec. Do not interview. Skip ordinary implementation."
---

This skill takes the current conversation context and codebase understanding and produces a spec. Do NOT interview the user — just synthesize what you already know. If a test-seam decision is already implied by the conversation, ADRs, or existing tests, write it down. Do not stop to ask.

Default tracker is local files. Do not run the missing Matt tracker-setup command. If the user asked for GitHub issues and `gh` is authenticated, publish with `/gh-axi`. Otherwise write the spec under `.scratch/<feature-slug>/spec.md`.

## Process

1. Explore the repo to understand the current state of the codebase, if you haven't already. Use the project's domain glossary vocabulary throughout the spec, and respect any ADRs in the area you're touching. If Codebase Memory has no project for cwd, skip it and use repo files.

2. Sketch the seams at which the feature will be tested. Prefer existing seams to new ones. Use the highest seam possible. The fewer seams across the codebase, the better — the ideal number is one. Record the seams in the spec; do not interview.

3. Write the spec using the template below, then publish it. Local default: `.scratch/<feature-slug>/spec.md`. GitHub only if the user asked and `gh` is authenticated.

<spec-template>

## Problem Statement

The problem that the user is facing, from the user's perspective.

## Solution

The solution to the problem, from the user's perspective.

## User Stories

A **minimum sufficient** numbered list. Each story must change at least one of: implementation, tests, security, migration, observability, performance, rollout, or rollback. Drop repetitive actor/benefit restatements. Format:

1. As an <actor>, I want a <feature>, so that <benefit>

<user-story-example>
1. As a mobile bank customer, I want to see balance on my accounts, so that I can make better informed decisions about my spending
</user-story-example>

Do not pad the list to look complete. If five stories cover the work, write five.

## Implementation Decisions

A list of implementation decisions that were made. This can include:

- The modules that will be built/modified
- The interfaces of those modules that will be modified
- Technical clarifications from the developer
- Architectural decisions
- Schema changes
- API contracts
- Specific interactions

Do NOT include brittle file paths or large code dumps. They go stale fast.

Exception: if a prototype produced a snippet that encodes a decision more precisely than prose can (state machine, reducer, schema, type shape), inline it within the relevant decision and note briefly that it came from a prototype. Trim to the decision-rich parts.

Stable module or symbol anchors are allowed when they save a later agent from re-reading the whole repo.

## Testing Decisions

A list of testing decisions that were made. Include:

- A description of what makes a good test (only test external behavior, not implementation details)
- Which modules will be tested
- Prior art for the tests (i.e. similar types of tests in the codebase)
- The verification profile from `01-verification.md` (FAST, STANDARD, UI, SECURITY, PERFORMANCE, or RELEASE)

## Out of Scope

A description of the things that are out of scope for this spec.

## Rollout and rollback

How this ships, and what happens if it must be undone.

## Further Notes

Any further notes about the feature.

</spec-template>
