"""Import and inspect reports."""

from __future__ import annotations

import json
from typing import Any


def inspect_payload(inspection: Any, snapshot: str | None = None) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "logical_name": inspection.logical_name,
        "sha256": inspection.sha256,
        "family": inspection.family,
        "top_level": inspection.top_level,
        "members": inspection.members,
        "files": inspection.files,
        "blocked": inspection.blocked,
        "snapshot": snapshot,
        "issues": [f"{item.code}:{item.path}" if item.path else item.code for item in inspection.issues],
    }


def import_payload(
    *,
    status: str,
    generation_id: str | None,
    archives: list[dict[str, Any]],
    counts: dict[str, int],
    warnings: list[str],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": status,
        "generation_id": generation_id,
        "archives": archives,
        "counts": counts,
        "warnings": warnings,
    }


def dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"
