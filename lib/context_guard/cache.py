"""Sensitive context-cache: 0600/0700, size + retention limits, no secret raw cache."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from pathlib import Path
from typing import Any

from .policy import load_policy, managed_paths


def ensure_dir(path: Path) -> Path:
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, 0o700)
    return path


def write_bytes(path: Path, data: bytes) -> None:
    path = Path(path)
    ensure_dir(path.parent)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)
    os.chmod(path, 0o600)


def write_text(path: Path, text: str) -> None:
    write_bytes(path, text.encode("utf-8"))


def dir_size(path: Path) -> int:
    total = 0
    if not path.exists():
        return 0
    for root, dirs, files in os.walk(path):
        for name in files:
            try:
                total += (Path(root) / name).stat().st_size
            except OSError:
                continue
        _ = dirs
    return total


def resolve_policy(
    *,
    policy: dict[str, Any] | None = None,
    policy_path: Path | None = None,
    managed: Path | None = None,
) -> dict[str, Any]:
    if policy is not None:
        return policy
    if policy_path is not None:
        return load_policy(Path(policy_path))
    if managed is not None:
        return load_policy(managed_paths(Path(managed))["config"])
    env = os.environ.get("GBFC_MANAGED")
    if env:
        return load_policy(managed_paths(Path(env))["config"])
    live = Path.home() / ".claude" / "grokbestfriend-claude" / "config" / "context-guard.json"
    return load_policy(live if live.is_file() else None)


def stream_at_cap(stream_dir: Path, stream_limit: int) -> bool:
    return dir_size(stream_dir) >= int(stream_limit)


def offload_raw(
    stream_dir: Path,
    *,
    tool: str,
    payload: bytes,
    klass: str,
    secret: bool = False,
    policy: dict[str, Any] | None = None,
    policy_path: Path | None = None,
    managed: Path | None = None,
) -> dict[str, str]:
    """Persist raw non-secret evidence. Secret-risk is never written."""
    if secret:
        return {"status": "RAW_CACHE_SKIPPED_SECRET_RISK", "pointer": ""}
    loaded = resolve_policy(policy=policy, policy_path=policy_path, managed=managed)
    stream_limit = int(loaded["cacheStreamMiB"]) * 1024 * 1024
    stream_dir = ensure_dir(stream_dir)
    if stream_at_cap(stream_dir, stream_limit) or dir_size(stream_dir) + len(payload) > stream_limit:
        return {"status": "CACHE_WRITE_SKIPPED_STREAM_CAP", "pointer": ""}
    digest = hashlib.sha256(payload).hexdigest()
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    raw_name = f"{stamp}-{digest[:12]}.raw"
    raw_path = stream_dir / "offload" / raw_name
    meta_path = stream_dir / "offload" / f"{stamp}-{digest[:12]}.json"
    try:
        write_bytes(raw_path, payload)
        write_text(
            meta_path,
            json.dumps(
                {
                    "tool": tool,
                    "bytes": len(payload),
                    "sha256": digest,
                    "timestamp": stamp,
                    "class": klass,
                },
                indent=2,
            )
            + "\n",
        )
    except OSError:
        return {"status": "CACHE_WRITE_FAILED", "pointer": ""}
    pointer = f"offload={raw_path.name} sha256={digest[:12]}"
    return {"status": "OFFLOADED", "pointer": pointer, "path": str(raw_path)}


def prune(
    cache_root: Path,
    *,
    active_stream: str | None = None,
    global_mib: int | None = None,
    stream_mib: int | None = None,
    retention_days: int | None = None,
    now: float | None = None,
    policy: dict[str, Any] | None = None,
    policy_path: Path | None = None,
    managed: Path | None = None,
) -> dict[str, int]:
    cache_root = Path(cache_root)
    if not cache_root.is_dir():
        return {"removed": 0, "bytes": 0}
    loaded = resolve_policy(policy=policy, policy_path=policy_path, managed=managed)
    global_limit = int((global_mib if global_mib is not None else loaded["cacheGlobalMiB"]) * 1024 * 1024)
    stream_limit = int((stream_mib if stream_mib is not None else loaded["cacheStreamMiB"]) * 1024 * 1024)
    days = int(retention_days if retention_days is not None else loaded["cacheRetentionDays"])
    cutoff = (now if now is not None else time.time()) - days * 86400
    removed = 0
    freed = 0

    streams = [p for p in cache_root.iterdir() if p.is_dir()]
    for stream_dir in streams:
        if stream_dir.name == active_stream:
            continue
        try:
            mtime = stream_dir.stat().st_mtime
        except OSError:
            continue
        if mtime < cutoff:
            size = dir_size(stream_dir)
            shutil.rmtree(stream_dir, ignore_errors=True)
            removed += 1
            freed += size

    for stream_dir in [p for p in cache_root.iterdir() if p.is_dir()]:
        if stream_dir.name == active_stream:
            # Active stream is never deleted. Further raw writes refuse at cap.
            continue
        if dir_size(stream_dir) <= stream_limit:
            continue
        files = sorted(
            [p for p in stream_dir.rglob("*") if p.is_file() and p.name not in {"ledger.json", "image.lock", "guard.log"}],
            key=lambda p: p.stat().st_mtime if p.exists() else 0,
        )
        while files and dir_size(stream_dir) > stream_limit:
            victim = files.pop(0)
            try:
                size = victim.stat().st_size
                victim.unlink()
                freed += size
                removed += 1
            except OSError:
                continue

    others = [p for p in cache_root.iterdir() if p.is_dir() and p.name != active_stream]
    others.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0)
    while others and dir_size(cache_root) > global_limit:
        victim = others.pop(0)
        size = dir_size(victim)
        shutil.rmtree(victim, ignore_errors=True)
        removed += 1
        freed += size
    return {"removed": removed, "bytes": freed}


def cache_status(cache_root: Path) -> dict[str, int | str]:
    cache_root = Path(cache_root)
    streams = [p.name for p in cache_root.iterdir() if p.is_dir()] if cache_root.is_dir() else []
    return {
        "root": str(cache_root),
        "streams": len(streams),
        "bytes": dir_size(cache_root) if cache_root.is_dir() else 0,
    }
