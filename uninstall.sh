#!/usr/bin/env bash
set -euo pipefail
umask 077

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$ROOT/lib/common.sh"
# shellcheck source=/dev/null
source "$ROOT/lib/transaction.sh"

gbfc_lock_begin
trap 'gbfc_lock_end' EXIT

gbfc_info "Uninstalling AntigravityBestFriend..."

# 1. Remove owned plugin
rm -rf -- "$GBFC_PLUGIN_DIR"

# 2. Strip router block from ~/.gemini/GEMINI.md
if [[ -f "$GBFC_GLOBAL_ROUTER" ]]; then
  python3 - "$GBFC_GLOBAL_ROUTER" <<'PY'
import sys
from pathlib import Path
target = Path(sys.argv[1])
if target.is_file():
    text = target.read_text(encoding="utf-8")
    b, e = "<!-- ANTIGRAVITY-BESTFRIEND:BEGIN -->", "<!-- ANTIGRAVITY-BESTFRIEND:END -->"
    if b in text and e in text:
        pre = text.split(b, 1)[0]
        post = text.split(e, 1)[1]
        cleaned = pre.rstrip() + ("\n" + post.lstrip() if post.strip() else "")
        target.write_text(cleaned.strip() + "\n" if cleaned.strip() else "", encoding="utf-8")
PY
fi

# 3. Remove owned MCP servers
python3 "$GBFC_ROOT/lib/mcp.py" remove --name "codebase-memory-mcp" 2>/dev/null || true
python3 "$GBFC_ROOT/lib/mcp.py" remove --name "context7" 2>/dev/null || true
python3 "$GBFC_ROOT/lib/mcp.py" remove --name "shadcn" 2>/dev/null || true
python3 "$GBFC_ROOT/lib/mcp.py" remove --name "serena" 2>/dev/null || true

# 4. Stop Chromium CDP if running
if [[ -x "$GBFC_CDP" ]]; then
  "$GBFC_CDP" stop 2>/dev/null || true
fi

# 5. Restore original agy binary if wrapper was installed
if [[ -f "$HOME/.local/bin/agy-real" ]]; then
  mv -f "$HOME/.local/bin/agy-real" "$HOME/.local/bin/agy"
  chmod +x "$HOME/.local/bin/agy"
fi

# 6. Remove symlinks in ~/.local/bin
rm -f -- "$HOME/.local/bin/agy-bestfriend" "$HOME/.local/bin/agy-chromium-cdp" "$HOME/.local/bin/agy-context-guard"

# 7. Remove managed runtime
rm -rf -- "$GBFC_MANAGED/bin" "$GBFC_MANAGED/components" "$GBFC_MANAGED/lib" "$GBFC_MANAGED/rules" "$GBFC_MANAGED/skills"

gbfc_tx_clear
gbfc_info "AntigravityBestFriend uninstalled cleanly."
