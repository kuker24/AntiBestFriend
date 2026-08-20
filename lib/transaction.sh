#!/usr/bin/env bash

gbfc_lock_file() { printf '%s\n' "$GBFC_MANAGED/tx/install.lock"; }
gbfc_tx_path() { printf '%s\n' "$GBFC_MANAGED/tx/current.json"; }
gbfc_backup_root() { printf '%s\n' "$GBFC_MANAGED/backups"; }
gbfc_stage_root() { printf '%s\n' "$GBFC_MANAGED/stage"; }

gbfc_lock_begin() {
  if [[ "$GBFC_DRY_RUN" == 1 ]]; then
    gbfc_info "WOULD_LOCK $(gbfc_lock_file)"
    return 0
  fi
  mkdir -p -- "$GBFC_MANAGED/tx"
  local lock
  lock="$(gbfc_lock_file)"
  exec {GBFC_LOCK_FD}>"$lock"
  if ! flock -n "$GBFC_LOCK_FD"; then
    eval "exec ${GBFC_LOCK_FD}>&-"
    GBFC_LOCK_FD=""
    gbfc_die "another antigravity-bestfriend install/restore holds the lock: $lock"
  fi
}

gbfc_lock_end() {
  if [[ "$GBFC_DRY_RUN" == 1 ]]; then
    return 0
  fi
  if [[ -n "${GBFC_LOCK_FD:-}" ]]; then
    flock -u "$GBFC_LOCK_FD" 2>/dev/null || true
    eval "exec ${GBFC_LOCK_FD}>&-"
    GBFC_LOCK_FD=""
  fi
}

gbfc_tx_set_state() {
  local state="$1"
  if [[ "$GBFC_DRY_RUN" == 1 ]]; then
    gbfc_info "WOULD_STATE $state"
    return 0
  fi
  mkdir -p -- "$GBFC_MANAGED/tx"
  python3 - "$(gbfc_tx_path)" "$state" "${GBFC_BACKUP_STAMP:-}" <<'PY'
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
state, stamp = sys.argv[2], sys.argv[3]
data = {}
if path.is_file():
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
data["state"] = state
data["product"] = "antigravity-bestfriend"
if stamp:
    data["backupStamp"] = stamp
path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY
}

gbfc_tx_state() {
  python3 - "$(gbfc_tx_path)" <<'PY'
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
if not path.is_file():
    print("")
    raise SystemExit(0)
try:
    data = json.loads(path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError):
    print("")
    raise SystemExit(0)
print(data.get("state") or "")
PY
}

gbfc_tx_clear() {
  rm -f -- "$(gbfc_tx_path)"
}

gbfc_tx_check_stale() {
  local state
  state="$(gbfc_tx_state)"
  case "$state" in
    ""|COMMITTED) return 0 ;;
    *)
      gbfc_die "stale transaction in $state — run ./restore.sh or ./install.sh --recover"
      ;;
  esac
}

gbfc_prune_backups() {
  local root
  root="$(gbfc_backup_root)"
  [[ -d "$root" ]] || return 0
  python3 - "$root" <<'PY'
import sys
from pathlib import Path
root = Path(sys.argv[1])
dirs = sorted([p for p in root.iterdir() if p.is_dir()], key=lambda p: p.name)
for old in dirs[:-3]:
    import shutil
    shutil.rmtree(old)
PY
}

gbfc_backup_owned() {
  local dest
  GBFC_BACKUP_STAMP="$(gbfc_stamp)"
  dest="$(gbfc_backup_root)/$GBFC_BACKUP_STAMP"
  if [[ "$GBFC_DRY_RUN" == 1 ]]; then
    gbfc_info "WOULD_BACKUP $dest"
    return 0
  fi
  mkdir -p -- "$dest/config" "$dest/rules" "$dest/plugin"
  [[ -f "$GBFC_GLOBAL_ROUTER" ]] && cp -a -- "$GBFC_GLOBAL_ROUTER" "$dest/GEMINI.md"
  [[ -f "$GBFC_MANIFEST" ]] && cp -a -- "$GBFC_MANIFEST" "$dest/MANIFEST.json"
  [[ -f "$GBFC_OWNERSHIP" ]] && cp -a -- "$GBFC_OWNERSHIP" "$dest/mcp-ownership.json"
  [[ -f "$GBFC_DESIGN_BANK_CFG" ]] && cp -a -- "$GBFC_DESIGN_BANK_CFG" "$dest/design-bank.json"
  [[ -d "$GBFC_PLUGIN_DIR" ]] && cp -a -- "$GBFC_PLUGIN_DIR" "$dest/plugin/"

  local mcp_py="$GBFC_ROOT/lib/mcp.py"
  python3 "$mcp_py" snapshot-owned --out "$dest/mcp-specs.json" \
    || gbfc_die "mcp snapshot-owned failed"

  gbfc_prune_backups
  gbfc_info "BACKUP $dest"
}

gbfc_latest_backup() {
  local root
  root="$(gbfc_backup_root)"
  [[ -d "$root" ]] || return 1
  ls -1 "$root" 2>/dev/null | tail -n 1
}
