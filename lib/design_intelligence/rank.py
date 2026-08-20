"""Eligibility, lexical search, and authority resolution."""

from __future__ import annotations

import math
import re
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from . import classify
from .catalog import load_items, read_lock

TOKEN = re.compile(r"[a-z0-9]+")

AUTHORITY_RANK = {
    "explicit_scope": 100,
    "explicit_brief": 100,
    "product_truth": 90,
    "incumbent_design": 80,
    "pinned_compatible_reference": 70,
    "pinned_new_direction": 75,
    "selected_direction": 75,
    "reference_evidence": 60,
    "trusted_evidence": 60,
    "system_bank": 40,
    "structure_bank": 35,
    "bank": 30,
    "heuristics": 10,
}


def tokenize(text: str) -> list[str]:
    return TOKEN.findall(text.lower())


def load_allowlist(path: Path) -> set[str]:
    names: set[str] = set()
    if not path.is_file():
        return names
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            names.add(stripped)
    return names


def probe_item(
    item: dict[str, Any],
    *,
    allowlist: set[str],
    host_commands: set[str] | None = None,
) -> dict[str, str | None]:
    commands = host_commands if host_commands is not None else set()
    available_via: str | None = None
    name = (item.get("name") or "").strip()
    slug = (item.get("id") or "").split(":", 1)[-1]
    execution = item.get("execution_class")

    if slug in allowlist or name in allowlist:
        available_via = f"gbf-skill:{slug if slug in allowlist else name}"
    if slug == "shadcn-ui" or name == "shadcn-ui":
        available_via = available_via or "gbf-mcp:shadcn"

    needed = list(item.get("capabilities_required") or [])
    if execution == "connector-required":
        if needed and all(cmd in commands for cmd in needed):
            return {"runtime_availability": "available", "available_via": needed[0]}
        return {"runtime_availability": "unavailable", "available_via": available_via}
    if execution == "provider-required":
        return {"runtime_availability": "unavailable", "available_via": available_via}
    if execution in {"native-candidate", "adapted-candidate"}:
        status = "available" if available_via else "unavailable"
        return {"runtime_availability": status, "available_via": available_via}
    if available_via and execution == "reference-only":
        return {"runtime_availability": "unavailable", "available_via": available_via}
    return {"runtime_availability": "unknown", "available_via": available_via}


def derive_hit(item: dict[str, Any], probe: dict[str, str | None]) -> dict[str, Any]:
    availability = str(probe.get("runtime_availability") or "unknown")
    status = classify.derive_execution_status(str(item.get("execution_class")), availability)
    return {
        "execution_status": status,
        "runtime_availability": availability,
        "available_via": probe.get("available_via"),
    }


def eligible(
    item: dict[str, Any],
    *,
    kind: str,
    include_unavailable: bool,
    probe: dict[str, str | None],
) -> tuple[bool, str]:
    if item.get("alias_of") or item.get("duplicate_of"):
        return False, "alias_or_duplicate"
    if item.get("kind") != kind:
        return False, "kind"
    if item.get("search_policy") == "never":
        return False, "search_policy"
    license_obj = item.get("license") or {}
    if license_obj.get("redistribution") == "blocked" or license_obj.get("status") == "conflicting":
        return False, "blocked_license"
    execution = item.get("execution_class")
    if execution == "quarantined":
        return False, "quarantined"
    derived = derive_hit(item, probe)
    if kind == "specialist":
        executable = derived["execution_status"] in {"native", "adapted"} and derived["runtime_availability"] == "available"
        if executable:
            return True, "executable"
        if include_unavailable and execution in {"stub", "provider-required", "connector-required", "reference-only"}:
            return True, "include_unavailable"
        return False, "specialist_not_executable"
    if kind == "recipe" and execution == "quarantined":
        return False, "quarantined"
    return True, "ok"


def score_item(item: dict[str, Any], query: str, policy: dict[str, Any]) -> tuple[float, list[str]]:
    weights = (policy.get("search") or {}).get("weights") or {}
    q_tokens = set(tokenize(query))
    if not q_tokens:
        return 0.0, []
    matched: list[str] = []
    score = 0.0
    fields = {
        "name": item.get("name") or "",
        "id": item.get("id") or "",
        "description": item.get("description") or "",
        "category": " ".join(item.get("categories") or []),
        "tags": " ".join(item.get("tags") or []),
        "summary": item.get("search_text") or "",
    }
    for field, blob in fields.items():
        tokens = set(tokenize(blob))
        overlap = q_tokens & tokens
        if not overlap:
            continue
        weight = float(weights.get(field) or 1.0)
        score += weight * len(overlap) / math.sqrt(len(q_tokens))
        matched.append(field)
    return score, matched


def diversity_penalty(selected: list[dict[str, Any]], candidate: dict[str, Any], penalty: float) -> float:
    cats = set(candidate.get("categories") or [])
    if not cats:
        return 0.0
    hits = 0
    for item in selected:
        if cats & set(item.get("categories") or []):
            hits += 1
    return hits * penalty


def search(
    items: Iterable[dict[str, Any]],
    *,
    kind: str,
    query: str,
    policy: dict[str, Any],
    allowlist: set[str],
    include_unavailable: bool = False,
    host_commands: set[str] | None = None,
) -> dict[str, Any]:
    limits = {
        "system": int((policy.get("search") or {}).get("system_limit") or 5),
        "structure": int((policy.get("search") or {}).get("structure_limit") or 3),
        "recipe": int((policy.get("search") or {}).get("recipe_limit") or 3),
        "specialist": int((policy.get("search") or {}).get("specialist_limit") or 3),
    }
    limit = limits.get(kind, 3)
    penalty = float((policy.get("search") or {}).get("diversity_penalty") or 4.0)
    scored: list[tuple[float, dict[str, Any], list[str], dict[str, str | None], str]] = []
    for item in items:
        probe = probe_item(item, allowlist=allowlist, host_commands=host_commands)
        ok, reason = eligible(
            item, kind=kind, include_unavailable=include_unavailable, probe=probe
        )
        if not ok:
            continue
        points, matched = score_item(item, query, policy)
        min_score = float((policy.get("search") or {}).get("min_score") or 0)
        if points <= 0 or points < min_score:
            continue
        scored.append((points, item, matched, probe, reason))
    scored.sort(key=lambda row: (-row[0], row[1]["id"]))
    picked: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    pending = list(scored)
    while pending and len(results) < limit:
        best_index = 0
        best_adj = None
        for index, (points, item, matched, probe, reason) in enumerate(pending):
            adj = points - diversity_penalty(picked, item, penalty)
            if best_adj is None or adj > best_adj or (adj == best_adj and item["id"] < pending[best_index][1]["id"]):
                best_adj = adj
                best_index = index
        if best_adj is None or best_adj <= 0:
            break
        points, item, matched, probe, reason = pending.pop(best_index)
        picked.append(item)
        derived = derive_hit(item, probe)
        results.append(
            {
                "id": item["id"],
                "kind": item["kind"],
                "name": item["name"],
                "description": item["description"],
                "score": points - diversity_penalty(picked[:-1], item, penalty),
                "matched_fields": matched,
                "eligibility": reason,
                "evidence_tier": item.get("evidence_tier"),
                "license": item.get("license"),
                "execution_class": item.get("execution_class"),
                "execution_status": derived["execution_status"],
                "runtime_availability": derived["runtime_availability"],
                "available_via": derived["available_via"],
                "warnings": item.get("warnings") or [],
                "untrusted_text": True,
            }
        )
    return {
        "query": query,
        "kind": kind,
        "results": results,
        "packages_loaded_during_search": 0,
    }


def search_bank(
    bank: Path,
    *,
    kind: str,
    query: str,
    policy: dict[str, Any],
    allowlist: set[str],
    include_unavailable: bool = False,
    host_commands: set[str] | None = None,
) -> dict[str, Any]:
    items = load_items(bank)
    lock = read_lock(bank)
    del lock
    return search(
        items,
        kind=kind,
        query=query,
        policy=policy,
        allowlist=allowlist,
        include_unavailable=include_unavailable,
        host_commands=host_commands,
    )


def fts_available(sqlite_path: Path) -> bool:
    if not sqlite_path.is_file():
        return False
    conn = sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True)
    try:
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='items_fts'")
        return cur.fetchone() is not None
    finally:
        conn.close()


def resolve_authority(intent: str, claims: dict[str, Any], taxonomy: dict[str, Any]) -> dict[str, Any]:
    ladder = ((taxonomy.get("authority") or {}).get(intent) or [])
    if not ladder:
        raise ValueError(f"unknown intent: {intent}")
    winner = None
    winner_rank = -1
    winner_source = None
    forbidden = {
        "brand_pixel_copy",
        "invented_claims",
        "a11y_violation",
        "skip_platform",
    }
    blocked = [key for key in forbidden if claims.get(key)]
    for source in ladder:
        if source not in claims:
            continue
        rank = AUTHORITY_RANK.get(source, 0)
        if rank > winner_rank:
            winner = claims[source]
            winner_rank = rank
            winner_source = source
    return {
        "intent": intent,
        "source": winner_source,
        "value": winner,
        "rank": winner_rank,
        "blocked": blocked,
        "preserves_product_truth": bool(claims.get("product_truth")),
        "preserves_incumbent": intent == "refine" and winner_source in {
            "incumbent_design",
            "product_truth",
            "explicit_scope",
        },
    }
