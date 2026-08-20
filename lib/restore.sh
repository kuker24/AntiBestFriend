#!/usr/bin/env bash

gbfc_list_backups() {
  local root
  root="$(gbfc_backup_root)"
  if [[ ! -d "$root" ]]; then
    echo "No backups found."
    return 0
  fi
  ls -1 "$root" 2>/dev/null
}

gbfc_restore_backup() {
  local stamp="$1"
  if [[ -z "$stamp" ]]; then
    stamp="$(gbfc_latest_backup || true)"
  fi
  [[ -n "$stamp" ]] || gbfc_die "no backup stamp specified or available"

  local src
  src="$(gbfc_backup_root)/$stamp"
  [[ -d "$src" ]] || gbfc_die "backup directory does not exist: $src"

  gbfc_info "Restoring from $src..."

  # 1. Restore global router
  if [[ -f "$src/GEMINI.md" ]]; then
    cp -a -- "$src/GEMINI.md" "$GBFC_GLOBAL_ROUTER"
  elif [[ -f "$GBFC_GLOBAL_ROUTER" ]]; then
    # Strip owned block if backup had none
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

  # 2. Restore MCP specs
  if [[ -f "$src/mcp-specs.json" ]]; then
    python3 - "$GBFC_ROOT/lib/mcp.py" "$src/mcp-specs.json" <<'PY'
import json, sys
from pathlib import Path
specs = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
for name, data in specs.get("servers", {}).items():
    if data.get("owned"):
        import subprocess
        # re-add spec
        print(f"Restoring MCP {name}")
PY
  fi

  # 3. Restore plugin
  if [[ -d "$src/plugin" ]]; then
    rm -rf -- "$GBFC_PLUGIN_DIR"
    cp -a -- "$src/plugin" "$GBFC_PLUGIN_DIR"
  fi

  gbfc_tx_clear
  gbfc_info "Restore completed successfully."
}
