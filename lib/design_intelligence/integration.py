"""Deterministic retrieval gate inside Impeccable new-work.

This module never chooses or activates a specialist. It only decides whether the
already-active Impeccable stage may consult the local reference catalog.
"""

from __future__ import annotations

from typing import Any

MODES = {"Persuade", "Operate", "Read", "Experience"}
INTENTS = {"refine", "redesign", "greenfield"}
SCOPES = {"narrow", "surface", "world"}
AUTHORITIES = {"established", "partial", "none"}
REFERENCES = {"none", "named", "url", "screenshot"}
TASK_KINDS = {"static", "motion", "data", "three-d"}


def plan_retrieval(
    *,
    intent: str,
    scope: str,
    mode: str,
    authority: str,
    reference: str = "none",
    task_kind: str = "static",
) -> dict[str, Any]:
    """Return a bounded catalog lane without becoming a second router."""
    values = {
        "intent": (intent, INTENTS),
        "scope": (scope, SCOPES),
        "mode": (mode, MODES),
        "authority": (authority, AUTHORITIES),
        "reference": (reference, REFERENCES),
        "task_kind": (task_kind, TASK_KINDS),
    }
    for name, (value, allowed) in values.items():
        if value not in allowed:
            raise ValueError(f"invalid {name}: {value}")

    base: dict[str, Any] = {
        "owner": "impeccable",
        "intent": intent,
        "scope": scope,
        "mode": mode,
        "authority": authority,
        "reference": reference,
        "task_kind": task_kind,
        "lane": "none",
        "handoff": None,
        "system_limit": 0,
        "structure_limit": 0,
        "packages_loaded_before_selection": 0,
        "specialists_activated": 0,
    }

    if reference in {"url", "screenshot"}:
        base.update(handoff="found-this-design", reason="explicit-visual-reference")
        return base
    if task_kind != "static":
        base["reason"] = "specialist-owned-stage"
        return base
    if scope == "narrow":
        base["reason"] = "incumbent-evidence-is-enough"
        return base
    if authority == "established" and intent != "redesign":
        base.update(lane="structure", structure_limit=3, reason="fixed-world-structure-challenge")
        return base

    base.update(
        lane="system+structure",
        system_limit=5,
        structure_limit=3,
        reason="new-or-replacement-world",
    )
    return base
