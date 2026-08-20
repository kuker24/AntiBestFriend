---
name: blast-radius
description: "Find what a change could break somewhere else before it ships, and prove the one safety fact by running real code. Use for /blast-radius, 'what could this break', or reviewing a small diff you do not trust. Manual only."
disable-model-invocation: true
---

# Blast radius

Find what a change breaks somewhere else, before it ships. Listing the callers is not the job. The job is the breakage grep will not show you.

Use repo evidence first. Codebase Memory if a project exists for cwd. Do not invoke `/why`, `/arena`, or `/unslop`. Optional multi-candidate compare follows `~/.claude/grokbestfriend-claude/rules/arena-protocol.md` **inline** and only for a wide change.

## Don't trust your own writeup

Find the one or two facts the whole thing depends on and prove them by running code.

### How sure are you

For each fact the change's safety depends on, get it as far down this list as is cheap, and say where it stopped.

1. You said so. Worthless on its own.
2. You pointed at the line. A real `file:line`.
3. You showed the bad case cannot happen. You walked the failure and it does not reach.
4. You ran it. A script or test that calls the real code and fails loud if you are wrong.
5. You reproduced it in the running app.

Any safety fact you cannot get to step 4, say so out loud. Do not write it up as settled.

## Steps

1. Read the change. The diff, the symbols it adds, changes, and deletes, and what it now does differently. Use git / `gh` if authenticated. Do not invoke `/why`.
2. Find the one fact it is safe because of. Spend time here, not on a long list of maybes.
3. Look where grep stops. Read the library you call, pinned version, local patch. Follow JSON, DB columns, wire formats, feature flags, code three hops downstream.
4. Be honest about each risk. Real chance, real cost. Cite a real `file:line`. Never invent a caller or an API.
5. Prove the one fact. Write a script or test that runs the real code, run it, and paste what happened. If you cannot prove it cheaply, mark it unproven.
6. For a big or wide change, optionally follow the arena protocol inline (same prompt, isolated candidates, one judge). Do not invoke `/arena`. Missing model-pool → inherit-parent + `MODEL_DIVERSITY=false`.

## What to hand back

- **What it does.** What changed, including the part that is not obvious.
- **The one fact it is safe because of.** State it, say which step you got it to, and show the proof. If you could not prove it, write unproven.
- **Risks.** Only the real ones. Each names how it breaks, the `file:line`, how likely and how bad, and how to check.
- **Cleared.** What you checked and why it is fine.
- **Before you merge.** The cheapest test or repro that catches the real bug.

Cite real code. Strip anything private before it goes anywhere public.
