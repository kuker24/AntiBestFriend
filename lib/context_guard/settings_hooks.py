#!/usr/bin/env python3
"""Surgical hooks-only mutation of Claude settings.json.

Never copies or prints env, tokens, gateway URLs, or model aliases.
Owned hook identity is the exact command path, not the matcher.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any

from . import HOOK_BIN_NAME, OWNED_EVENTS, PRODUCT

FAIL_CLOSED_INVALID_SETTINGS = "FAIL_CLOSED_INVALID_SETTINGS"
FAIL_CLOSED_SETTINGS_RACE = "FAIL_CLOSED_SETTINGS_RACE"
FAIL_CLOSED_IO = "FAIL_CLOSED_IO"

_SETTINGS_LOCK_NAME = ".gbfc-settings-hooks.lock"


class SettingsHooksError(Exception):
    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        super().__init__(detail or code)


def default_command(managed: Path | None = None) -> str:
    root = managed or (Path.home() / ".claude" / "grokbestfriend-claude")
    return str((root / "bin" / HOOK_BIN_NAME).resolve())


def non_hook_canonical(data: dict[str, Any]) -> str:
    filtered = {k: data[k] for k in sorted(data) if k != "hooks"}
    return json.dumps(filtered, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def non_hook_hash(data: dict[str, Any]) -> str:
    return hashlib.sha256(non_hook_canonical(data).encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_settings(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SettingsHooksError(FAIL_CLOSED_IO, str(exc)) from exc
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SettingsHooksError(FAIL_CLOSED_INVALID_SETTINGS, "malformed settings.json") from exc
    if not isinstance(data, dict):
        raise SettingsHooksError(FAIL_CLOSED_INVALID_SETTINGS, "settings.json is not an object")
    return data


def disable_all_hooks_state(data: dict[str, Any]) -> str:
    if "disableAllHooks" not in data:
        return "NOT_SET"
    return "TRUE" if data.get("disableAllHooks") is True else "SET"


def _is_owned_command(command: Any, owned_command: str) -> bool:
    if not isinstance(command, str) or not command.strip():
        return False
    left = os.path.expanduser(command.strip())
    right = os.path.expanduser(owned_command.strip())
    try:
        return Path(left).resolve() == Path(right).resolve()
    except OSError:
        return left == right


def _command_of_hook(entry: Any) -> str | None:
    if not isinstance(entry, dict):
        return None
    cmd = entry.get("command")
    return cmd if isinstance(cmd, str) else None


def _iter_hook_commands(group: Any) -> list[str]:
    found: list[str] = []
    if isinstance(group, dict):
        cmd = _command_of_hook(group)
        if cmd:
            found.append(cmd)
        inner = group.get("hooks")
        if isinstance(inner, list):
            for item in inner:
                found.extend(_iter_hook_commands(item))
    elif isinstance(group, list):
        for item in group:
            found.extend(_iter_hook_commands(item))
    return found


def extract_owned(hooks: Any, owned_command: str) -> list[Any]:
    """Return owned matcher-groups (top-level array items) that contain the command."""
    if not isinstance(hooks, dict):
        return []
    owned: list[Any] = []
    for event, groups in hooks.items():
        if not isinstance(groups, list):
            continue
        for group in groups:
            cmds = _iter_hook_commands(group)
            if any(_is_owned_command(cmd, owned_command) for cmd in cmds):
                owned.append({"event": event, "group": group})
    return owned


def hooks_contain_owned(hooks: Any, owned_command: str) -> bool:
    return bool(extract_owned(hooks, owned_command))


def _strip_owned_from_group(group: Any, owned_command: str) -> Any | None:
    """Remove owned command entries. Return None if the group is empty afterwards."""
    if not isinstance(group, dict):
        return group
    if _is_owned_command(group.get("command"), owned_command):
        return None
    inner = group.get("hooks")
    if isinstance(inner, list):
        kept = []
        for item in inner:
            if isinstance(item, dict) and _is_owned_command(item.get("command"), owned_command):
                continue
            stripped = _strip_owned_from_group(item, owned_command)
            if stripped is not None:
                kept.append(stripped)
        if not kept and "command" not in group:
            return None
        out = dict(group)
        out["hooks"] = kept
        return out
    return group


def strip_owned_hooks(hooks: Any, owned_command: str) -> dict[str, Any]:
    if not isinstance(hooks, dict):
        return {}
    result: dict[str, Any] = {}
    for event, groups in hooks.items():
        if not isinstance(groups, list):
            result[event] = groups
            continue
        kept = []
        for group in groups:
            stripped = _strip_owned_from_group(group, owned_command)
            if stripped is not None:
                kept.append(stripped)
        if kept:
            result[event] = kept
    return result


def owned_hook_group(command: str) -> dict[str, Any]:
    return {"hooks": [{"type": "command", "command": command}]}


def build_owned_hooks(command: str) -> dict[str, list[Any]]:
    group = owned_hook_group(command)
    return {event: [dict(group)] for event in OWNED_EVENTS}


def merge_hooks(existing: Any, command: str) -> dict[str, Any]:
    cleaned = strip_owned_hooks(existing, command)
    owned = build_owned_hooks(command)
    for event, groups in owned.items():
        cleaned.setdefault(event, [])
        if not isinstance(cleaned[event], list):
            cleaned[event] = [cleaned[event]]
        cleaned[event].extend(groups)
    return cleaned


def snapshot_owned(data: dict[str, Any], owned_command: str) -> dict[str, Any]:
    hooks = data.get("hooks")
    return {
        "product": PRODUCT,
        "command": owned_command,
        "hooksKeyExisted": "hooks" in data,
        "owned": extract_owned(hooks, owned_command),
    }


def remaining_after_owned_strip(data: dict[str, Any], owned_command: str) -> dict[str, Any]:
    """Return settings after owned hooks are removed. Does not write."""
    if not isinstance(data, dict):
        return {}
    out = dict(data)
    hooks = strip_owned_hooks(data.get("hooks"), owned_command)
    if hooks:
        out["hooks"] = hooks
    else:
        out.pop("hooks", None)
    return out


def settings_is_installer_only(settings_path: Path, owned_command: str) -> bool:
    """True only if the file is missing or nothing foreign remains after owned-hook strip.

    Invalid JSON / non-object → False (fail closed: do not delete).
    Any leftover key (theme, env, model, foreign hooks, …) → False.
    Remaining {} or only empty hooks → True.
    """
    path = Path(settings_path)
    if not path.is_file():
        return True
    try:
        data = load_settings(path)
    except SettingsHooksError:
        return False
    remaining = remaining_after_owned_strip(data, owned_command)
    if not remaining:
        return True
    if list(remaining.keys()) == ["hooks"] and remaining.get("hooks") in ({}, None):
        return True
    return False


def maybe_delete_absent_settings(
    settings_path: Path,
    owned_command: str,
    *,
    lock_dir: Path | None = None,
) -> bool:
    """Unlink settings.json only when it is still installer-only. Single delete site.

    Holds the same settings lock as mutate_hooks. Re-reads and re-validates
    under the lock; a mid-flight change is FAIL_CLOSED_SETTINGS_RACE.
    """
    path = Path(settings_path)
    if not path.is_file():
        return False
    if not settings_is_installer_only(path, owned_command):
        return False

    lock_path = _lock_path(path, lock_dir)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "a+", encoding="utf-8") as lock_file:
        _flock_exclusive(lock_file)
        if not path.is_file():
            return False
        before_sha = file_sha256(path)
        installer_only = settings_is_installer_only(path, owned_command)
        after_exists = path.is_file()
        after_sha = file_sha256(path) if after_exists else ""
        if not after_exists or after_sha != before_sha:
            raise SettingsHooksError(FAIL_CLOSED_SETTINGS_RACE, "settings changed before delete")
        if not installer_only:
            return False
        path.unlink()
        return True


def apply_snapshot(data: dict[str, Any], snapshot: dict[str, Any], owned_command: str) -> dict[str, Any]:
    """Remove current owned hooks, restore previous owned groups, keep foreign."""
    hooks = strip_owned_hooks(data.get("hooks"), owned_command)
    previous = snapshot.get("owned") if isinstance(snapshot, dict) else []
    if isinstance(previous, list):
        for rec in previous:
            if not isinstance(rec, dict):
                continue
            event = rec.get("event")
            group = rec.get("group")
            if not isinstance(event, str) or group is None:
                continue
            hooks.setdefault(event, [])
            if not isinstance(hooks[event], list):
                hooks[event] = [hooks[event]]
            hooks[event].append(group)
    out = dict(data)
    if hooks:
        out["hooks"] = hooks
    elif snapshot.get("hooksKeyExisted"):
        out["hooks"] = {}
    else:
        out.pop("hooks", None)
    return out


def _lock_path(settings_path: Path, lock_dir: Path | None) -> Path:
    if lock_dir is not None:
        lock_dir.mkdir(parents=True, exist_ok=True)
        return lock_dir / _SETTINGS_LOCK_NAME
    return settings_path.parent / _SETTINGS_LOCK_NAME


def _flock_exclusive(lock_file):
    import fcntl

    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)


def _atomic_replace(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    prior_mode = stat.S_IMODE(path.stat().st_mode) if path.is_file() else 0o600
    fd, tmp_name = tempfile.mkstemp(prefix=".gbfc-settings.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_name, prior_mode)
        os.replace(tmp_name, path)
        os.chmod(path, prior_mode)
        dir_fd = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def mutate_hooks(
    settings_path: Path,
    mutator,
    *,
    lock_dir: Path | None = None,
    create: bool = True,
) -> dict[str, Any]:
    """Apply mutator(data) -> data. Touches only the hooks key. Fail closed on race."""
    settings_path = Path(settings_path)
    if not settings_path.is_file() and not create:
        raise SettingsHooksError(FAIL_CLOSED_IO, "settings.json missing")

    lock_path = _lock_path(settings_path, lock_dir)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "a+", encoding="utf-8") as lock_file:
        _flock_exclusive(lock_file)
        before_exists = settings_path.is_file()
        before_sha = file_sha256(settings_path) if before_exists else ""
        data = load_settings(settings_path) if before_exists else {}
        before_non_hook = non_hook_hash(data)
        updated = mutator(dict(data))
        if not isinstance(updated, dict):
            raise SettingsHooksError(FAIL_CLOSED_INVALID_SETTINGS, "mutator returned non-object")
        if non_hook_hash(updated) != before_non_hook:
            raise SettingsHooksError(FAIL_CLOSED_INVALID_SETTINGS, "mutator touched non-hook keys")
        after_exists = settings_path.is_file()
        after_sha = file_sha256(settings_path) if after_exists else ""
        if after_exists != before_exists or after_sha != before_sha:
            raise SettingsHooksError(FAIL_CLOSED_SETTINGS_RACE)
        payload = json.dumps(updated, indent=2, ensure_ascii=False) + "\n"
        if not settings_path.is_file() and not updated:
            return {"status": "OK", "nonHook": "MATCH", "hooks": "UNCHANGED"}
        _atomic_replace(settings_path, payload)
        verify = load_settings(settings_path)
        if non_hook_hash(verify) != before_non_hook:
            raise SettingsHooksError(FAIL_CLOSED_SETTINGS_RACE, "post-write non-hook hash mismatch")
        return {
            "status": "OK",
            "nonHook": "MATCH",
            "hooks": "CHANGED" if data.get("hooks") != verify.get("hooks") else "UNCHANGED",
        }


def write_json(path: Path, payload: dict[str, Any], mode: int = 0o600) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".gbfc.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_name, mode)
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def write_ownership(path: Path, command: str) -> None:
    import time

    write_json(
        path,
        {
            "product": PRODUCT,
            "command": command,
            "events": list(OWNED_EVENTS),
            "configuredAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
    )


def report_settings_keys(data: dict[str, Any]) -> None:
    print("settings.keys", ",".join(sorted(data)))
    for key in (
        "hooks",
        "disableAllHooks",
        "bypassPermissions",
        "permissionMode",
        "model",
        "autoCompactWindow",
        "env",
    ):
        print(key, "SET" if key in data else "NOT_SET")


def _cmd_hash(args: argparse.Namespace) -> int:
    data = load_settings(Path(args.settings))
    # Do not print the digest of secret-bearing keys.
    _ = non_hook_hash(data)
    print("NON_HOOK_SETTINGS_HASH", "COMPUTED")
    return 0


def _cmd_compare_hash(args: argparse.Namespace) -> int:
    left = non_hook_hash(load_settings(Path(args.left)))
    right = non_hook_hash(load_settings(Path(args.right))) if args.right else left
    if args.against:
        right = non_hook_hash(load_settings(Path(args.against)))
    print("NON_HOOK_SETTINGS_HASH", "MATCH" if left == right else "MISMATCH")
    return 0 if left == right else 1


def _cmd_snapshot(args: argparse.Namespace) -> int:
    data = load_settings(Path(args.settings))
    snap = snapshot_owned(data, args.command)
    write_json(Path(args.out), snap)
    print("HOOKS_OWNED_SNAPSHOT", "OK", "count", len(snap["owned"]))
    return 0


def _cmd_merge(args: argparse.Namespace) -> int:
    command = args.command
    ownership = Path(args.ownership) if args.ownership else None

    def mutator(data: dict[str, Any]) -> dict[str, Any]:
        out = dict(data)
        out["hooks"] = merge_hooks(data.get("hooks"), command)
        return out

    result = mutate_hooks(
        Path(args.settings),
        mutator,
        lock_dir=Path(args.lock_dir) if args.lock_dir else None,
        create=True,
    )
    if ownership:
        write_ownership(ownership, command)
    print("HOOKS_MERGE", result["status"], "nonHook", result["nonHook"], "hooks", result["hooks"])
    return 0


def _cmd_unmerge(args: argparse.Namespace) -> int:
    command = args.command
    keep_empty = args.keep_empty

    def mutator(data: dict[str, Any]) -> dict[str, Any]:
        out = dict(data)
        hooks = strip_owned_hooks(data.get("hooks"), command)
        if hooks:
            out["hooks"] = hooks
        elif keep_empty and "hooks" in data:
            out["hooks"] = {}
        else:
            out.pop("hooks", None)
        return out

    result = mutate_hooks(
        Path(args.settings),
        mutator,
        lock_dir=Path(args.lock_dir) if args.lock_dir else None,
        create=False,
    )
    print("HOOKS_UNMERGE", result["status"], "nonHook", result["nonHook"], "hooks", result["hooks"])
    return 0


def _cmd_restore(args: argparse.Namespace) -> int:
    command = args.command
    snapshot = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))

    def mutator(data: dict[str, Any]) -> dict[str, Any]:
        return apply_snapshot(data, snapshot, command)

    result = mutate_hooks(
        Path(args.settings),
        mutator,
        lock_dir=Path(args.lock_dir) if args.lock_dir else None,
        create=False,
    )
    print("HOOKS_RESTORE", result["status"], "nonHook", result["nonHook"], "hooks", result["hooks"])
    return 0


def _cmd_probe(args: argparse.Namespace) -> int:
    path = Path(args.settings)
    if not path.is_file():
        print("settings.json", "NOT_SET")
        return 0
    data = load_settings(path)
    report_settings_keys(data)
    print("disableAllHooks", disable_all_hooks_state(data))
    print("ownedHook", "SET" if hooks_contain_owned(data.get("hooks"), args.command) else "NOT_SET")
    return 0


def _cmd_compare_live(args: argparse.Namespace) -> int:
    """Compare non-hook hash of one file against an in-memory digest file (hex only, no secrets)."""
    current = non_hook_hash(load_settings(Path(args.settings)))
    recorded = Path(args.digest).read_text(encoding="utf-8").strip()
    print("NON_HOOK_SETTINGS_HASH", "MATCH" if current == recorded else "MISMATCH")
    return 0 if current == recorded else 1


def _cmd_write_digest(args: argparse.Namespace) -> int:
    digest = non_hook_hash(load_settings(Path(args.settings)))
    Path(args.out).write_text(digest + "\n", encoding="utf-8")
    os.chmod(args.out, 0o600)
    print("NON_HOOK_SETTINGS_HASH", "RECORDED")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="settings_hooks")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("hash")
    p.add_argument("settings")
    p.set_defaults(func=_cmd_hash)

    p = sub.add_parser("compare")
    p.add_argument("left")
    p.add_argument("right", nargs="?")
    p.add_argument("--against")
    p.set_defaults(func=_cmd_compare_hash)

    p = sub.add_parser("digest")
    p.add_argument("settings")
    p.add_argument("--out", required=True)
    p.set_defaults(func=_cmd_write_digest)

    p = sub.add_parser("compare-digest")
    p.add_argument("settings")
    p.add_argument("--digest", required=True)
    p.set_defaults(func=_cmd_compare_live)

    p = sub.add_parser("snapshot-owned")
    p.add_argument("settings")
    p.add_argument("--command", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=_cmd_snapshot)

    p = sub.add_parser("merge")
    p.add_argument("settings")
    p.add_argument("--command", required=True)
    p.add_argument("--ownership")
    p.add_argument("--lock-dir")
    p.set_defaults(func=_cmd_merge)

    p = sub.add_parser("unmerge")
    p.add_argument("settings")
    p.add_argument("--command", required=True)
    p.add_argument("--lock-dir")
    p.add_argument("--keep-empty", action="store_true")
    p.set_defaults(func=_cmd_unmerge)

    p = sub.add_parser("restore")
    p.add_argument("settings")
    p.add_argument("--command", required=True)
    p.add_argument("--snapshot", required=True)
    p.add_argument("--lock-dir")
    p.set_defaults(func=_cmd_restore)

    p = sub.add_parser("probe")
    p.add_argument("settings")
    p.add_argument("--command", required=True)
    p.set_defaults(func=_cmd_probe)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except SettingsHooksError as exc:
        print(exc.code, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
