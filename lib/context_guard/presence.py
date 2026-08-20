#!/usr/bin/env python3
"""First-install presence tombstones.

Surfaces that did not exist before install must be removed on restore.
Never records settings.json contents.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from . import HOOK_BIN_NAME, PRODUCT
from .settings_hooks import maybe_delete_absent_settings

MANAGED_REL = (
    ("manifest", "MANIFEST.json"),
    ("mcp_ownership", "config/mcp-ownership.json"),
    ("design_bank", "config/design-bank.json"),
    ("hook_ownership", "config/hook-ownership.json"),
    ("context_guard_config", "config/context-guard.json"),
    ("context_guard_bin", "bin/agy-context-guard"),
    ("context_guard_lib", "lib/context_guard"),
    ("managed_rules", "rules"),
    ("managed_bin", "bin"),
    ("adapter_root", "config/adapter-root.txt"),
)


def _exists(path: Path) -> bool:
    """True for files, or directories that already contain something.

    Installer mkdir of empty config/bin/tx must not count as pre-existing.
    """
    try:
        if path.is_file() or path.is_symlink():
            return True
        if path.is_dir():
            return any(path.iterdir())
        return False
    except OSError:
        return False


def snapshot(
    *,
    claude_home: Path,
    managed: Path,
    skills: Path,
    allowlist: list[str],
    hooks_key: bool,
) -> dict[str, Any]:
    surfaces: dict[str, Any] = {
        "claude_md": {"path": "CLAUDE.md", "existed": _exists(claude_home / "CLAUDE.md")},
        "settings_file": {
            "path": "settings.json",
            "existed": (claude_home / "settings.json").is_file(),
        },
        "hooks_key": {"path": "settings.json#hooks", "existed": hooks_key},
        "managed_root": {"path": str(managed), "existed": _exists(managed)},
    }
    for key, rel in MANAGED_REL:
        surfaces[key] = {"path": rel, "existed": _exists(managed / rel)}
    user_bin = _user_bin_claude_gbf()
    surfaces["user_bin_claude_gbf"] = {
        "path": str(user_bin),
        "existed": user_bin.exists() or user_bin.is_symlink(),
    }
    skill_map: dict[str, bool] = {}
    for name in allowlist:
        skill_map[name] = _exists(skills / name)
    return {
        "product": PRODUCT,
        "claudeHome": str(claude_home),
        "managed": str(managed),
        "skills": str(skills),
        "surfaces": surfaces,
        "ownedSkills": skill_map,
    }


def load_allowlist(path: Path) -> list[str]:
    names: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            names.append(line)
    return names


def _user_bin_claude_gbf() -> Path:
    return Path.home() / ".local" / "bin" / "agy-bestfriend"


def _owned_user_bin_symlink(link: Path, managed: Path) -> bool:
    if not link.is_symlink():
        return False
    try:
        target = link.readlink()
    except OSError:
        return False
    expected = (Path(managed) / "bin" / "agy-bestfriend")
    return Path(target) == expected


def _rm(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if path.is_symlink() or path.is_file():
        path.unlink()
        return
    if path.is_dir():
        shutil.rmtree(path)


def _owned_skill(path: Path) -> bool:
    marker = path / ".gbf-claude-owned.json"
    if not marker.is_file():
        return False
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(data, dict) and data.get("product") == PRODUCT


def apply_tombstones(
    presence: dict[str, Any],
    *,
    claude_home: Path,
    managed: Path,
    skills: Path,
    owned_command: str | None = None,
    lock_dir: Path | None = None,
) -> list[str]:
    """Delete surfaces that did not exist before install (owned only)."""
    removed: list[str] = []
    surfaces = presence.get("surfaces") or {}

    if not (surfaces.get("claude_md") or {}).get("existed"):
        md = claude_home / "CLAUDE.md"
        if md.is_file():
            text = md.read_text(encoding="utf-8")
            begin = "<!-- GROKBESTFRIEND-CLAUDE:BEGIN -->"
            end = "<!-- GROKBESTFRIEND-CLAUDE:END -->"
            if begin in text and end in text:
                pre = text.split(begin, 1)[0]
                post = text.split(end, 1)[1]
                remain = (pre + post).strip()
                if remain:
                    md.write_text(remain + "\n", encoding="utf-8")
                else:
                    md.unlink()
                    removed.append("CLAUDE.md")
            elif text.strip() == "" or "GROKBESTFRIEND-CLAUDE" in text:
                md.unlink()
                removed.append("CLAUDE.md")

    for key, rel in MANAGED_REL:
        rec = surfaces.get(key) or {}
        if rec.get("existed"):
            continue
        target = managed / rel
        if _exists(target):
            _rm(target)
            removed.append(rel)

    for name, existed in (presence.get("ownedSkills") or {}).items():
        if existed:
            continue
        dest = skills / name
        if dest.is_dir() and _owned_skill(dest):
            _rm(dest)
            removed.append(f"skills/{name}")

    user_bin_rec = surfaces.get("user_bin_claude_gbf")
    if isinstance(user_bin_rec, dict) and user_bin_rec.get("existed") is False:
        link = _user_bin_claude_gbf()
        if _owned_user_bin_symlink(link, managed):
            link.unlink()
            removed.append(str(link))

    # Only delete settings.json when this backup explicitly recorded that
    # the file did not exist. A missing key (1.4.1 backups) must not delete it.
    # After owned-hook removal, keep the file if any foreign/non-owned content remains.
    settings_rec = surfaces.get("settings_file")
    if isinstance(settings_rec, dict) and settings_rec.get("existed") is False:
        settings_path = claude_home / "settings.json"
        command = owned_command or str((Path(managed) / "bin" / HOOK_BIN_NAME).resolve())
        if maybe_delete_absent_settings(settings_path, command, lock_dir=lock_dir):
            removed.append("settings.json")

    # Do not delete foreign skills. Do not delete managed root here —
    # restore/uninstall decide that after hooks are unmerged.
    return removed


def write_presence(path: Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="presence")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("snapshot")
    p.add_argument("--claude-home", required=True)
    p.add_argument("--managed", required=True)
    p.add_argument("--skills", required=True)
    p.add_argument("--allowlist", required=True)
    p.add_argument("--hooks-key", choices=("true", "false"), required=True)
    p.add_argument("--out", required=True)

    p = sub.add_parser("apply")
    p.add_argument("--presence", required=True)
    p.add_argument("--claude-home", required=True)
    p.add_argument("--managed", required=True)
    p.add_argument("--skills", required=True)
    p.add_argument("--command", default="")
    p.add_argument("--lock-dir", default="")

    args = parser.parse_args(argv)
    if args.cmd == "snapshot":
        payload = snapshot(
            claude_home=Path(args.gemini_home),
            managed=Path(args.managed),
            skills=Path(args.skills),
            allowlist=load_allowlist(Path(args.allowlist)),
            hooks_key=args.hooks_key == "true",
        )
        write_presence(Path(args.out), payload)
        print("PRESENCE_SNAPSHOT", "OK")
        return 0
    presence = json.loads(Path(args.presence).read_text(encoding="utf-8"))
    command = args.command.strip() or None
    lock_dir = Path(args.lock_dir) if args.lock_dir else None
    removed = apply_tombstones(
        presence,
        claude_home=Path(args.gemini_home),
        managed=Path(args.managed),
        skills=Path(args.skills),
        owned_command=command,
        lock_dir=lock_dir,
    )
    print("PRESENCE_TOMBSTONES", "removed", str(len(removed)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
