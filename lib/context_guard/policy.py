"""Context Guard policy. Defaults live here; live file may override non-secret fields."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULTS: dict[str, Any] = {
    "version": 1,
    "maxLongEdgePx": 1200,
    "maxImageBytes": 393216,
    "stepDownPx": [1200, 1024, 900, 768],
    "maxSourcePixels": 40_000_000,
    "batchSoftTokens": 60000,
    "batchHardTokens": 90000,
    "turnSoftTokens": 100000,
    "turnHardTokens": 140000,
    "textBudgetBash": 20000,
    "textBudgetRead": 30000,
    "cacheGlobalMiB": 256,
    "cacheStreamMiB": 64,
    "cacheRetentionDays": 7,
    "maxStdinBytes": 12_000_000,
    "oneImagePerBatch": True,
    "jpegQuality": [85, 75, 65, 55],
}


def default_policy() -> dict[str, Any]:
    return dict(DEFAULTS)


def load_policy(path: Path | None) -> dict[str, Any]:
    policy = default_policy()
    if path is None or not Path(path).is_file():
        return policy
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return policy
    if not isinstance(data, dict):
        return policy
    for key, value in data.items():
        if key in DEFAULTS and value is not None:
            policy[key] = value
    return policy


def estimate_tokens(size_bytes: int) -> int:
    return max(0, (int(size_bytes) + 3) // 4)


def managed_paths(managed: Path) -> dict[str, Path]:
    managed = Path(managed)
    return {
        "managed": managed,
        "bin": managed / "bin" / "gbfc-context-guard",
        "lib": managed / "lib" / "context_guard",
        "config": managed / "config" / "context-guard.json",
        "ownership": managed / "config" / "hook-ownership.json",
        "cache": managed / "context-cache",
        "tx": managed / "tx",
        "dispatch": managed / "bin" / "claude-gbf",
    }
