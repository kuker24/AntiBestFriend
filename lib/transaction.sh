#!/usr/bin/env bash

gbfc_lock_file() {
  printf '%s/tx/install.lock\n' "$GBFC_MANAGED"
}

gbfc_lock_begin() {
  local lock
  lock="$(gbfc_lock_file)"
  mkdir -p -- "$(dirname -- "$lock")"
  exec {GBFC_LOCK_FD}>"$lock"
  flock -n "$GBFC_LOCK_FD" || gbfc_die "Another AntiBestFriend process holds the lock: $lock"
}

gbfc_lock_end() {
  if [[ -n "${GBFC_LOCK_FD:-}" ]]; then
    flock -u "$GBFC_LOCK_FD" 2>/dev/null || true
    exec {GBFC_LOCK_FD}>&- 2>/dev/null || true
    GBFC_LOCK_FD=""
  fi
}

gbfc_tx_file() {
  printf '%s/tx/current.json\n' "$GBFC_MANAGED"
}

gbfc_tx_set_state() {
  local state="$1"
  if [[ "$GBFC_DRY_RUN" == 1 ]]; then
    gbfc_info "WOULD_STATE $state"
    return 0
  fi
  local tx_f
  tx_f="$(gbfc_tx_file)"
  mkdir -p -- "$(dirname -- "$tx_f")"
  python3 - "$tx_f" "$state" "$(gbfc_now)" "${GBFC_BACKUP_STAMP:-}" <<'PY'
import json, sys
from pathlib import Path

target, state, now, stamp = sys.argv[1:5]
data = {}
p = Path(target)
if p.is_file():
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        pass

data["state"] = state
data["updatedAt"] = now
if stamp:
    data["backupStamp"] = stamp

p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY
}

gbfc_tx_current_state() {
  local tx_f
  tx_f="$(gbfc_tx_file)"
  if [[ -f "$tx_f" ]]; then
    python3 - "$tx_f" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
try:
    data = json.loads(p.read_text(encoding="utf-8"))
    print(data.get("state", "NONE"))
except Exception:
    print("NONE")
PY
  else
    printf '%s\n' "NONE"
  fi
}

gbfc_tx_backup_stamp() {
  local tx_f
  tx_f="$(gbfc_tx_file)"
  if [[ -f "$tx_f" ]]; then
    python3 - "$tx_f" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
try:
    data = json.loads(p.read_text(encoding="utf-8"))
    print(data.get("backupStamp", ""))
except Exception:
    print("")
PY
  fi
}

gbfc_tx_check_stale() {
  local state
  state="$(gbfc_tx_current_state)"
  if [[ "$state" != "NONE" && "$state" != "COMMITTED" ]]; then
    gbfc_die "Stale transaction in state: $state — run ./restore.sh or ./install.sh --recover"
  fi
}

gbfc_tx_clear() {
  rm -f -- "$(gbfc_tx_file)"
}

gbfc_backup_owned() {
  if [[ "$GBFC_DRY_RUN" == 1 ]]; then
    gbfc_info "WOULD_BACKUP -> $GBFC_MANAGED/backups"
    return 0
  fi
  local stamp
  stamp="$(gbfc_now)"
  GBFC_BACKUP_STAMP="$stamp"
  local dest="$GBFC_MANAGED/backups/$stamp"
  mkdir -p -- "$dest"

  python3 - "$dest" "$HOME" <<'PY'
import hashlib, json, os, shutil, sys
from pathlib import Path

dest_dir = Path(sys.argv[1])
home = Path(sys.argv[2])

surfaces = {
    "agy": home / ".local/bin/agy",
    "agy_real": home / ".local/bin/agy-real",
    "gemini_md": home / ".gemini/GEMINI.md",
    "mcp_config": home / ".gemini/config/mcp_config.json",
    "plugin_dir_config": home / ".gemini/config/plugins/antigravity-bestfriend",
    "plugin_dir_cli": home / ".gemini/antigravity-cli/plugins/antigravity-bestfriend",
    "ownership": home / ".gemini/antigravity-bestfriend/config/mcp-ownership.json",
    "design_bank_cfg": home / ".gemini/antigravity-bestfriend/config/design-bank.json",
}

manifest = {}

for key, p in surfaces.items():
    entry = {
        "path": str(p),
        "exists": p.exists() or p.is_symlink(),
        "is_symlink": p.is_symlink(),
        "is_dir": p.is_dir() and not p.is_symlink(),
        "mode": oct(p.stat().st_mode) if (p.exists() or p.is_symlink()) else None,
        "sha256": None,
        "symlink_target": str(p.readlink()) if p.is_symlink() else None,
    }
    if entry["exists"]:
        if p.is_file() and not p.is_symlink():
            data = p.read_bytes()
            entry["sha256"] = hashlib.sha256(data).hexdigest()
            backup_file = dest_dir / f"{key}.raw"
            backup_file.write_bytes(data)
        elif p.is_dir() and not p.is_symlink():
            backup_tree = dest_dir / key
            shutil.copytree(p, backup_tree, symlinks=True)
    manifest[key] = entry

(dest_dir / "snapshot.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
PY

  gbfc_info "BACKUP $dest"
}

gbfc_tx_recover() {
  local state
  state="$(gbfc_tx_current_state)"
  if [[ "$state" == "NONE" || "$state" == "COMMITTED" ]]; then
    gbfc_info "No interrupted transaction to recover."
    gbfc_tx_clear
    return 0
  fi

  local stamp
  stamp="$(gbfc_tx_backup_stamp)"
  if [[ -n "$stamp" ]]; then
    # shellcheck source=/dev/null
    source "$GBFC_ROOT/lib/restore.sh"
    gbfc_restore_backup "$stamp"
  else
    gbfc_info "Transaction interrupted before backup was written; cleaning."
  fi
  gbfc_tx_clear
  gbfc_info "Recovery completed."
}
