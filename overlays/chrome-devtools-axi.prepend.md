## Claude browser contract

Follow the browser engine rules. Invocation only:

1. Start background Chromium: `claude-chromium-cdp start` (or `$HOME/.claude/grokbestfriend-claude/bin/claude-chromium-cdp start`).
2. Every command: `CHROME_DEVTOOLS_AXI_BROWSER_URL=http://127.0.0.1:9223 npx -y chrome-devtools-axi <command>`.
3. Never set `CHROME_DEVTOOLS_AXI_HEADED=1` or `CHROME_DEVTOOLS_AXI_AUTO_CONNECT=1` unless the user asks to see a window.
4. If the helper prints `NOT_CONFIGURED`, stop. Do not fall back to Google Chrome.

## Context Guard

One image per agentic tool batch. A screenshot is a confirm-success last resort, not a parallel dump. Prefer console, network, and DOM before pixels. Tall pages: overview, then a targeted crop later. Never auto-crop the top.

