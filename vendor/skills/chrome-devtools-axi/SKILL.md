---
name: chrome-devtools-axi
description: "Control a Chromium session through chrome-devtools-axi after grok-chromium-cdp start. Use when an observed browser issue needs diagnostics (click, form, console, network). Skip if curl or web_fetch is enough. Not for exploratory multi-role QA (use browser-act)."
user-invocable: false
author: Kun Chen (kunchenguid)
metadata:
  hermes:
    tags: [browser, chrome, automation, devtools]
    category: automation
when-to-use: "Use when an observed browser issue needs Chromium diagnostics. Start grok-chromium-cdp first and attach via CHROME_DEVTOOLS_AXI_BROWSER_URL. Skip if curl or web_fetch is enough."

---
## GrokBuild browser contract

Follow the browser engine rules in `00-routing.md`. Invocation only:

1. Start background Chromium: `grok-chromium-cdp start` (or `$HOME/.grok/bin/grok-chromium-cdp start`).
2. Every command: `CHROME_DEVTOOLS_AXI_BROWSER_URL=http://127.0.0.1:9222 npx -y chrome-devtools-axi <command>`.
3. Never set `CHROME_DEVTOOLS_AXI_HEADED=1` or `CHROME_DEVTOOLS_AXI_AUTO_CONNECT=1` unless the user asks to see a window.
4. If the helper prints `NOT_CONFIGURED`, stop. Do not fall back to Google Chrome.


# chrome-devtools-axi

Agent ergonomic interface for diagnosing a Chromium session after `grok-chromium-cdp start`. Prefer `/browser-act` for exploratory multi-role QA.

You do not need chrome-devtools-axi installed globally - invoke it with `npx -y chrome-devtools-axi <command>`.
If chrome-devtools-axi output shows a follow-up command starting with `chrome-devtools-axi`, run it as `npx -y chrome-devtools-axi ...` instead.

## When to use

Use chrome-devtools-axi after an observed browser issue needs diagnostics: click, form, console, or network. Start `grok-chromium-cdp` first and attach with `CHROME_DEVTOOLS_AXI_BROWSER_URL`.

Skip it when a plain `fetch`/`curl` or `web_fetch` suffices. Do not use it for exploratory multi-role QA (`/browser-act`) and do not fall back to Google Chrome.

## Workflow

1. Run `npx -y chrome-devtools-axi open <url>` to navigate. Output includes the page's accessibility snapshot; interactive elements carry `uid=` refs.
2. Interact by ref: `click @<uid>`, `fill @<uid> <text>`, `fillform @<uid>=<val>...`, `hover @<uid>`, `drag @<from> @<to>`, `upload @<uid> <path>`.
3. Pass refs back exactly as printed, including the `g<N>:` generation prefix. If the page re-rendered since the snapshot, the action fails loudly with `STALE_REF` - run `snapshot` again and retry with fresh refs.
4. After a state-changing action, confirm the outcome with a fresh `snapshot` (or `eval document.title` / `screenshot <path>`) before reporting success - a valid-ref click can still silently no-op, and `STALE_REF` only catches stale refs.
5. Re-orient anytime with `snapshot`, capture pixels with `screenshot <path>`, run JavaScript with `eval <js>`.
6. Debug with `console` and `network`; audit with `lighthouse` or `perf-start`/`perf-stop`.
7. Every response ends with contextual next-step hints - follow them. The first command auto-starts a persistent bridge, so the browser session survives across invocations; run `stop` when you are done.

## Commands

```
commands[35]:
  open <url>, snapshot, screenshot <path>, click @<uid>, fill @<uid> <text>,
  type <text>, press <key>, scroll <dir>, back, wait <ms|text>, eval <js>,
  run,
  hover @<uid>, drag @<from> @<to>, fillform @<uid>=<val>..., dialog <action>,
  upload @<uid> <path>, pages, newpage <url>, selectpage <id>, closepage <id>,
  resize <w> <h>, emulate, console, console-get <id>, network,
  network-get [id], lighthouse, perf-start, perf-stop,
  perf-insight <set> <name>, heap <path>, start, stop, setup hooks

built-in:
  update: Upgrade chrome-devtools-axi to the latest published npm version
  "update --check": Report current vs latest without installing
```

Run `npx -y chrome-devtools-axi --help` for flags and environment variables, or `npx -y chrome-devtools-axi <command> --help` for per-command usage.

## Tips

- Pipe output through grep/head to extract specific data from large pages.
- Add `--full` to snapshot-producing commands to disable truncation.
- Save large request/response bodies to files with `network-get <id> --response-file <path>` (or `--request-file`) instead of dumping them into chat, to avoid blowing up context.
- Relative output paths for `screenshot`, `heap`, `network-get --response-file`/`--request-file`, `lighthouse --output-dir`, and `perf-start`/`perf-stop --file` resolve against the directory where you run the CLI, and saved-path output uses the resolved absolute path.
