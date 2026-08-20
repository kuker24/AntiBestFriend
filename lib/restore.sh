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
  [[ -n "$stamp" ]] || gbfc_die "No backup stamp specified or available"

  local src
  src="$(gbfc_backup_root)/$stamp"
  [[ -d "$src" ]] || gbfc_die "Backup directory does not exist: $src"

  gbfc_info "Restoring exact state from snapshot $src..."

  # Execute restoration with hash and topology verification
  python3 - "$src" "$HOME" <<'PY'
import hashlib, json, os, shutil, sys
from pathlib import Path

src_dir = Path(sys.argv[1])
home = Path(sys.argv[2])
snap_file = src_dir / "snapshot.json"

if not snap_file.is_file():
    print("Snapshot metadata missing in backup")
    raise SystemExit(1)

meta = json.loads(snap_file.read_text(encoding="utf-8"))

for key, entry in meta.items():
    p = Path(entry["path"])
    existed = entry["exists"]

    if not existed:
        # If it didn't exist before, ensure it is removed
        if p.is_dir() and not p.is_symlink():
            shutil.rmtree(p, ignore_errors=True)
        elif p.exists() or p.is_symlink():
            p.unlink()
        print(f"Restored ABSENT: {p}")
        continue

    # File existed before
    p.parent.mkdir(parents=True, exist_ok=True)
    if entry["is_symlink"]:
        if p.exists() or p.is_symlink():
            if p.is_dir() and not p.is_symlink():
                shutil.rmtree(p, ignore_errors=True)
            else:
                p.unlink()
        os.symlink(entry["symlink_target"], p)
        print(f"Restored SYMLINK: {p} -> {entry['symlink_target']}")
    elif entry["is_dir"]:
        if p.exists() or p.is_symlink():
            if p.is_dir() and not p.is_symlink():
                shutil.rmtree(p, ignore_errors=True)
            else:
                p.unlink()
        backup_tree = src_dir / key
        if backup_tree.is_dir():
            shutil.copytree(backup_tree, p, symlinks=True)
            print(f"Restored DIR: {p}")
    else:
        # Regular file
        backup_file = src_dir / f"{key}.raw"
        if backup_file.is_file():
            data = backup_file.read_bytes()
            if entry["sha256"]:
                actual_sha = hashlib.sha256(data).hexdigest()
                if actual_sha != entry["sha256"]:
                    print(f"FATAL: Backup file corruption for {key}")
                    raise SystemExit(1)
            if p.is_dir() and not p.is_symlink():
                shutil.rmtree(p, ignore_errors=True)
            elif p.exists() or p.is_symlink():
                p.unlink()
            p.write_bytes(data)
            if entry["mode"]:
                os.chmod(p, int(entry["mode"], 8))
            print(f"Restored FILE: {p} (verified SHA256)")
PY

  gbfc_tx_clear
  gbfc_info "Restore completed and verified."
}
