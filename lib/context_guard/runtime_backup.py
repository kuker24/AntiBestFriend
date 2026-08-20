"""Exact previous Context Guard runtime backup / restore with checksums.

Never stores settings.json contents. Tracks file existence only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
from pathlib import Path
from typing import Any

from . import PRODUCT

RUNTIME_FILES = (
    "bin/gbfc-context-guard",
    "bin/claude-chromium-cdp",
    "bin/claude-gbf",
    "config/context-guard.json",
    "config/hook-ownership.json",
    "config/adapter-root.txt",
)

RUNTIME_TREES = ("lib/context_guard",)

PROTECTED = {
    "ledger.json",
    "image.lock",
    "guard.log",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def _copy_file(src: Path, dest: Path) -> dict[str, Any]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    os.chmod(dest, _mode(src))
    return {
        "path": str(src),
        "rel": "",
        "sha256": _sha256(dest),
        "mode": _mode(dest),
        "bytes": dest.stat().st_size,
        "kind": "file",
    }


def _copy_tree(src: Path, dest: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    os.chmod(dest, 0o700)
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        rel_root = Path(root).relative_to(src)
        target_root = dest / rel_root
        target_root.mkdir(parents=True, exist_ok=True)
        os.chmod(target_root, 0o700)
        for name in files:
            if name.endswith(".pyc") or name in PROTECTED:
                continue
            src_file = Path(root) / name
            dest_file = target_root / name
            rec = _copy_file(src_file, dest_file)
            rec["rel"] = str((rel_root / name).as_posix())
            records.append(rec)
    return records


def snapshot_runtime(*, managed: Path, dest: Path, settings: Path) -> dict[str, Any]:
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    os.chmod(dest, 0o700)
    runtime_dir = dest / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    files: dict[str, Any] = {}
    trees: dict[str, Any] = {}

    for rel in RUNTIME_FILES:
        src = managed / rel
        rec: dict[str, Any] = {"rel": rel, "existed": src.is_file()}
        if src.is_file():
            copied = _copy_file(src, runtime_dir / rel)
            rec.update({"sha256": copied["sha256"], "mode": copied["mode"], "bytes": copied["bytes"]})
        files[rel] = rec

    for rel in RUNTIME_TREES:
        src = managed / rel
        rec = {"rel": rel, "existed": src.is_dir() and any(src.rglob("*"))}
        if rec["existed"]:
            members = _copy_tree(src, runtime_dir / rel)
            rec["members"] = [
                {"rel": m["rel"], "sha256": m["sha256"], "mode": m["mode"], "bytes": m["bytes"]}
                for m in members
            ]
        else:
            rec["members"] = []
        trees[rel] = rec

    payload = {
        "product": PRODUCT,
        "kind": "context-guard-runtime",
        "settingsFileExisted": Path(settings).is_file(),
        "files": files,
        "trees": trees,
    }
    manifest = dest / "runtime-manifest.json"
    manifest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.chmod(manifest, 0o600)
    return payload


def _verify_file(path: Path, expected: dict[str, Any]) -> None:
    if not path.is_file():
        raise RuntimeError(f"RUNTIME_RESTORE_MISSING {expected.get('rel')}")
    digest = _sha256(path)
    if digest != expected.get("sha256"):
        raise RuntimeError(f"RUNTIME_RESTORE_CHECKSUM {expected.get('rel')}")


def restore_runtime(*, managed: Path, dest: Path, settings: Path) -> dict[str, Any]:
    dest = Path(dest)
    manifest_path = dest / "runtime-manifest.json"
    if not manifest_path.is_file():
        return {"status": "SKIP", "reason": "NO_RUNTIME_MANIFEST"}
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    runtime_dir = dest / "runtime"
    restored: list[str] = []
    removed: list[str] = []

    for rel, rec in (payload.get("files") or {}).items():
        target = managed / rel
        src = runtime_dir / rel
        if rec.get("existed"):
            if not src.is_file():
                raise RuntimeError(f"RUNTIME_BACKUP_MISSING {rel}")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)
            if rec.get("mode"):
                os.chmod(target, int(rec["mode"]))
            _verify_file(target, rec)
            restored.append(rel)
        elif target.exists() or target.is_symlink():
            if target.is_dir() and not target.is_symlink():
                shutil.rmtree(target)
            else:
                target.unlink()
            removed.append(rel)

    for rel, rec in (payload.get("trees") or {}).items():
        target = managed / rel
        src = runtime_dir / rel
        if rec.get("existed"):
            if target.exists():
                shutil.rmtree(target)
            members = _copy_tree(src, target)
            expected = {m["rel"]: m for m in rec.get("members") or []}
            for member in members:
                exp = expected.get(member["rel"])
                if exp:
                    _verify_file(target / member["rel"], exp)
            restored.append(rel)
        elif target.exists():
            shutil.rmtree(target)
            removed.append(rel)

    # settings.json delete-vs-preserve is owned by presence.apply_tombstones
    # via settings_hooks.maybe_delete_absent_settings. Never unlink here:
    # this step runs before presence and would wipe foreign theme/hooks.
    _ = settings

    return {"status": "OK", "restored": restored, "removed": removed}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="runtime_backup")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("snapshot")
    p.add_argument("--managed", required=True)
    p.add_argument("--dest", required=True)
    p.add_argument("--settings", required=True)
    p = sub.add_parser("restore")
    p.add_argument("--managed", required=True)
    p.add_argument("--dest", required=True)
    p.add_argument("--settings", required=True)
    args = parser.parse_args(argv)
    if args.cmd == "snapshot":
        snapshot_runtime(managed=Path(args.managed), dest=Path(args.dest), settings=Path(args.settings))
        print("RUNTIME_SNAPSHOT OK")
        return 0
    result = restore_runtime(managed=Path(args.managed), dest=Path(args.dest), settings=Path(args.settings))
    print("RUNTIME_RESTORE", result["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
