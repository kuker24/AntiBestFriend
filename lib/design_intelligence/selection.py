"""Lazy shortlist, safe system inspection, and user-locked selection pins."""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from . import archive as archive_mod
from . import catalog
from . import normalize
from . import rank
from . import text as text_mod


class SelectionError(ValueError):
    pass


MODES = {"Persuade", "Operate", "Read", "Experience"}
INTENTS = {"refine", "redesign", "greenfield"}
TOKEN_NAME = re.compile(r"^--[a-zA-Z0-9_-]{1,80}$")
TOKEN_VALUE = re.compile(r"^[a-zA-Z0-9#(),.%+\-\s/]{1,120}$")


def _catalog_state(bank: Path, policy: dict[str, Any]) -> tuple[str, str | None, list[dict[str, Any]], list[str]]:
    if not bank.is_dir():
        return "DEGRADED", None, [], ["BANK_MISSING"]
    try:
        lock = catalog.read_lock(bank)
        if lock is None:
            return "DEGRADED", None, [], ["CATALOG_LOCK_MISSING"]
        items = catalog.load_items(bank, policy)
    except (OSError, UnicodeError, json.JSONDecodeError, catalog.CatalogError) as exc:
        return "BLOCKED", None, [], [f"CATALOG_INVALID:{type(exc).__name__}"]
    limitations = []
    if any(
        item.get("execution_class") in {"stub", "quarantined"}
        or (item.get("license") or {}).get("status") == "unknown"
        for item in items
    ):
        limitations.append("REFERENCE_LIMITATIONS")
    return ("DEGRADED" if limitations else "PASS"), str(lock["generation_id"]), items, limitations


def _with_catalog_card(hit: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    out = dict(hit)
    out["style_authority"] = item.get("style_authority")
    out["selection_policy"] = item.get("selection_policy")
    out["normalization_status"] = item.get("normalization_status")
    out["summary"] = item.get("summary") or {}
    return out


def shortlist(
    bank: Path,
    *,
    query: str,
    intent: str,
    mode: str,
    policy: dict[str, Any],
    allowlist: set[str] | None = None,
    structure_only: bool = False,
) -> dict[str, Any]:
    if intent not in INTENTS:
        raise SelectionError(f"invalid intent: {intent}")
    if mode not in MODES:
        raise SelectionError(f"invalid mode: {mode}")
    cleaned_query = text_mod.sanitize_field(query, policy, max_len=600)
    if not cleaned_query:
        raise SelectionError("query is empty after sanitization")
    status, generation, items, limitations = _catalog_state(bank, policy)
    payload: dict[str, Any] = {
        "status": status,
        "catalog_generation": generation,
        "intent": intent,
        "mode": mode,
        "query": cleaned_query,
        "systems": [],
        "structures": [],
        "limits": {"systems": 0 if structure_only else 5, "structures": 3},
        "packages_loaded_during_search": 0,
        "specialists_activated": 0,
        "limitations": limitations,
        "untrusted_text": True,
    }
    if not items:
        return payload
    by_id = {str(item["id"]): item for item in items}
    allowed = allowlist or set()
    if not structure_only:
        system_hits = rank.search(
            items,
            kind="system",
            query=cleaned_query,
            policy=policy,
            allowlist=allowed,
        )["results"]
        payload["systems"] = [
            _with_catalog_card(hit, by_id[hit["id"]])
            for hit in system_hits
            if by_id[hit["id"]].get("selection_policy") == "full-on-selection"
            and by_id[hit["id"]].get("normalization_status") == "complete"
        ][:5]
    structure_hits = rank.search(
        items,
        kind="structure",
        query=cleaned_query,
        policy=policy,
        allowlist=allowed,
    )["results"]
    payload["structures"] = [
        _with_catalog_card(hit, by_id[hit["id"]])
        for hit in structure_hits
        if by_id[hit["id"]].get("selection_policy") == "normalized-card-only"
        and by_id[hit["id"]].get("style_authority") == "structure-only"
        and by_id[hit["id"]].get("normalization_status") != "manual-required"
    ][:3]
    return payload


def _selected_item(items: list[dict[str, Any]], item_id: str, kind: str) -> dict[str, Any]:
    matches = [item for item in items if item.get("id") == item_id]
    if len(matches) != 1:
        raise SelectionError(f"unknown {kind}: {item_id}")
    item = matches[0]
    eligible, reason = rank.eligible(
        item,
        kind=kind,
        include_unavailable=False,
        probe=rank.probe_item(item, allowlist=set()),
    )
    if not eligible:
        raise SelectionError(f"ineligible {item_id}: {reason}")
    return item


def _raw_archive(bank: Path, item: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    source = item.get("source") or {}
    archive_name = str(source.get("archive") or "")
    lock = catalog.read_lock(bank)
    if not isinstance(lock, dict):
        raise SelectionError("catalog lock missing")
    expected = str((lock.get("input_hashes") or {}).get(archive_name) or "")
    if not expected:
        raise SelectionError(f"archive is not pinned by lock: {archive_name}")
    matches = [
        (zip_path, meta)
        for _family, zip_path, meta in catalog.listed_raw(bank)
        if str(meta.get("logical_name") or "") == archive_name
    ]
    if len(matches) != 1:
        raise SelectionError(f"archive resolution failed: {archive_name}")
    zip_path, meta = matches[0]
    actual = archive_mod.sha256_file(zip_path)
    if actual != expected or str(meta.get("sha256") or "") != expected:
        raise SelectionError(f"archive hash mismatch: {archive_name}")
    return zip_path, lock


def _css_tokens(raw: str, policy: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for match in re.finditer(r"(--[A-Za-z0-9_-]+)\s*:\s*([^;{}]+);", raw):
        key = match.group(1)
        value = text_mod.redact_secrets(match.group(2).strip(), policy)
        if not TOKEN_NAME.fullmatch(key) or not TOKEN_VALUE.fullmatch(value):
            continue
        if any(marker in value.lower() for marker in ("url(", "expression", "javascript", "@import")):
            continue
        out[key] = value
        if len(out) >= 128:
            break
    return out


def inspect_system(bank: Path, item_id: str, policy: dict[str, Any]) -> dict[str, Any]:
    status, generation, items, limitations = _catalog_state(bank, policy)
    if status == "BLOCKED" or not generation:
        raise SelectionError("catalog is not selectable")
    item = _selected_item(items, item_id, "system")
    if item.get("selection_policy") != "full-on-selection":
        raise SelectionError(f"system cannot be opened: {item_id}")
    zip_path, _lock = _raw_archive(bank, item)
    source_path = str((item.get("source") or {}).get("path") or "")
    if not source_path.endswith("/manifest.json"):
        raise SelectionError(f"invalid system source path: {item_id}")
    folder = source_path.rsplit("/", 1)[0]
    members = [f"{folder}/manifest.json", f"{folder}/DESIGN.md", f"{folder}/tokens.css"]
    parts: list[tuple[str, bytes]] = []
    loaded: dict[str, bytes] = {}
    with archive_mod.open_zip(zip_path) as handle:
        for member in members:
            data = archive_mod.read_member(handle, member, policy)
            loaded[member] = data
            parts.append((member.rsplit("/", 1)[-1], data))
    actual_content = normalize.framed_hash(parts)
    expected_content = str((item.get("source") or {}).get("content_sha256") or "")
    if actual_content != expected_content:
        raise SelectionError(f"system content hash mismatch: {item_id}")
    try:
        manifest = json.loads(loaded[members[0]].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SelectionError(f"invalid selected manifest: {item_id}") from exc
    if not isinstance(manifest, dict):
        raise SelectionError(f"invalid selected manifest: {item_id}")
    design = loaded[members[1]].decode("utf-8", "replace")
    tokens = loaded[members[2]].decode("utf-8", "replace")
    return {
        "status": status,
        "catalog_generation": generation,
        "id": item["id"],
        "name": item["name"],
        "style_authority": item.get("style_authority"),
        "evidence_tier": item.get("evidence_tier"),
        "license": item.get("license"),
        "summary": item.get("summary") or {},
        "design_evidence": text_mod.sanitize_field(design, policy, max_len=4000),
        "tokens": _css_tokens(tokens, policy),
        "source_content_sha256": expected_content,
        "package_files_loaded": 3,
        "loaded_files": ["manifest.json", "DESIGN.md", "tokens.css"],
        "verified_content_hash": True,
        "limitations": limitations,
        "quote_as_evidence": True,
        "untrusted_text": True,
    }


def check_selection(value: Any, policy: dict[str, Any]) -> list[str]:
    if not isinstance(value, dict):
        return ["selection"]
    errors: list[str] = []
    allowed = {
        "schema_version", "catalog_generation", "target", "intent", "mode", "query",
        "systems", "structure", "authority", "constraints", "not_design_md", "untrusted_text",
    }
    if set(value) - allowed:
        errors.append("additional_properties")
    if value.get("schema_version") != 1:
        errors.append("schema_version")
    if not re.fullmatch(r"[0-9a-f]{16,64}", str(value.get("catalog_generation") or "")):
        errors.append("catalog_generation")
    if value.get("intent") not in INTENTS:
        errors.append("intent")
    if value.get("mode") not in MODES:
        errors.append("mode")
    systems = value.get("systems")
    if not isinstance(systems, list) or len(systems) > 2:
        errors.append("systems")
    else:
        system_keys = {
            "role", "id", "name", "source_content_sha256", "style_authority",
            "evidence_tier", "license", "package_files_loaded",
        }
        roles: list[str] = []
        for row in systems:
            if not isinstance(row, dict) or set(row) != system_keys:
                errors.append("systems.items")
                continue
            roles.append(str(row.get("role")))
            if row.get("role") not in {"primary", "secondary"}:
                errors.append("systems.role")
            if not text_mod.is_catalog_id(str(row.get("id") or "")):
                errors.append("systems.id")
            if not re.fullmatch(r"[0-9a-f]{64}", str(row.get("source_content_sha256") or "")):
                errors.append("systems.source_content_sha256")
            if row.get("style_authority") not in {"authoritative", "inspiration-only"}:
                errors.append("systems.style_authority")
            if row.get("package_files_loaded") != 3:
                errors.append("systems.package_files_loaded")
        if len(roles) != len(set(roles)) or ("secondary" in roles and "primary" not in roles):
            errors.append("systems.roles")
    structure = value.get("structure")
    if structure is not None and not isinstance(structure, dict):
        errors.append("structure")
    elif isinstance(structure, dict):
        structure_keys = {
            "id", "name", "source_content_sha256", "style_authority", "package_files_loaded",
        }
        if set(structure) != structure_keys:
            errors.append("structure.items")
        if structure.get("style_authority") != "structure-only" or structure.get("package_files_loaded") != 0:
            errors.append("structure.boundary")
        if not text_mod.is_catalog_id(str(structure.get("id") or "")):
            errors.append("structure.id")
        if not re.fullmatch(r"[0-9a-f]{64}", str(structure.get("source_content_sha256") or "")):
            errors.append("structure.source_content_sha256")
    authority = value.get("authority")
    if authority != {
        "source": "user-locked-direction",
        "bank_role": "challenger-evidence",
        "product_truth_wins": True,
    }:
        errors.append("authority")
    constraints = value.get("constraints")
    if constraints != {
        "max_primary_systems": 1,
        "max_secondary_influences": 1,
        "structure_cannot_override_style": True,
        "no_literal_brand_copy": True,
        "no_specialist_activation": True,
    }:
        errors.append("constraints")
    if not isinstance(value.get("target"), str) or not value.get("target", "").strip():
        errors.append("target")
    if not isinstance(value.get("query"), str) or not value.get("query", "").strip():
        errors.append("query")
    if not isinstance(value.get("target"), str) or not isinstance(value.get("query"), str):
        errors.append("text_fields")
    if value.get("not_design_md") is not True or value.get("untrusted_text") is not True:
        errors.append("authority_flags")
    if text_mod.find_secret_hits(value, policy):
        errors.append("secret_leak")
    return errors


def validate_selection(bank: Path, path: Path, policy: dict[str, Any]) -> dict[str, Any]:
    """Validate a persisted pin against the current committed catalog."""
    try:
        if path.stat().st_size > 256 * 1024:
            return {"status": "BLOCKED", "errors": ["selection_read:too_large"]}
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return {"status": "BLOCKED", "errors": [f"selection_read:{type(exc).__name__}"]}
    errors = check_selection(value, policy)
    if not isinstance(value, dict):
        return {"status": "BLOCKED", "valid": False, "errors": errors}
    status, generation, items, limitations = _catalog_state(bank, policy)
    if status == "BLOCKED" or not generation:
        errors.append("catalog_not_selectable")
    elif value.get("catalog_generation") != generation:
        errors.append("catalog_generation_stale")
    by_id = {str(item.get("id")): item for item in items}
    system_rows = value.get("systems") if isinstance(value.get("systems"), list) else []
    for row in system_rows:
        if not isinstance(row, dict):
            continue
        item = by_id.get(str(row.get("id")))
        if not item or item.get("kind") != "system":
            errors.append(f"system_missing:{row.get('id')}")
            continue
        if row.get("source_content_sha256") != (item.get("source") or {}).get("content_sha256"):
            errors.append(f"system_hash:{row.get('id')}")
    structure = value.get("structure")
    if isinstance(structure, dict):
        item = by_id.get(str(structure.get("id")))
        if not item or item.get("kind") != "structure":
            errors.append(f"structure_missing:{structure.get('id')}")
        elif structure.get("source_content_sha256") != (item.get("source") or {}).get("content_sha256"):
            errors.append(f"structure_hash:{structure.get('id')}")
    return {
        "status": "BLOCKED" if errors else status,
        "valid": not errors,
        "errors": errors,
        "catalog_generation": generation,
        "limitations": limitations,
        "selection": value if not errors else None,
    }


def pin_selection(
    project: Path,
    bank: Path,
    *,
    target: str,
    query: str,
    intent: str,
    mode: str,
    policy: dict[str, Any],
    primary_system: str | None = None,
    secondary_system: str | None = None,
    structure: str | None = None,
    user_locked: bool = False,
) -> dict[str, Any]:
    if not user_locked:
        raise SelectionError("selection requires an explicit user lock")
    if intent not in INTENTS or mode not in MODES:
        raise SelectionError("invalid intent or mode")
    if secondary_system and not primary_system:
        raise SelectionError("secondary system requires a primary system")
    if primary_system and secondary_system and primary_system == secondary_system:
        raise SelectionError("primary and secondary systems must differ")
    if not any((primary_system, structure)):
        raise SelectionError("selection is empty")
    status, generation, items, _limitations = _catalog_state(bank, policy)
    if status == "BLOCKED" or not generation:
        raise SelectionError("catalog is not selectable")

    systems: list[dict[str, Any]] = []
    selected_evidence: list[dict[str, Any]] = []
    for role, item_id in (("primary", primary_system), ("secondary", secondary_system)):
        if not item_id:
            continue
        evidence = inspect_system(bank, item_id, policy)
        selected_evidence.append({"role": role, **evidence})
        systems.append(
            {
                "role": role,
                "id": evidence["id"],
                "name": evidence["name"],
                "source_content_sha256": evidence["source_content_sha256"],
                "style_authority": evidence["style_authority"],
                "evidence_tier": evidence["evidence_tier"],
                "license": evidence["license"],
                "package_files_loaded": evidence["package_files_loaded"],
            }
        )

    structure_row = None
    selected_structure_card = None
    if structure:
        item = _selected_item(items, structure, "structure")
        if item.get("selection_policy") != "normalized-card-only":
            raise SelectionError(f"structure cannot be selected: {structure}")
        if item.get("style_authority") != "structure-only":
            raise SelectionError(f"style-coupled structure blocked: {structure}")
        if item.get("normalization_status") == "manual-required":
            raise SelectionError(f"structure lacks a normalized card: {structure}")
        structure_row = {
            "id": item["id"],
            "name": item["name"],
            "source_content_sha256": (item.get("source") or {}).get("content_sha256"),
            "style_authority": "structure-only",
            "package_files_loaded": 0,
        }
        selected_structure_card = item.get("summary") or {}

    cleaned_target = text_mod.sanitize_field(target, policy, max_len=240)
    cleaned_query = text_mod.sanitize_field(query, policy, max_len=600)
    if not cleaned_target or not cleaned_query:
        raise SelectionError("target and query must survive sanitization")
    payload = {
        "schema_version": 1,
        "catalog_generation": generation,
        "target": cleaned_target,
        "intent": intent,
        "mode": mode,
        "query": cleaned_query,
        "systems": systems,
        "structure": structure_row,
        "authority": {
            "source": "user-locked-direction",
            "bank_role": "challenger-evidence",
            "product_truth_wins": True,
        },
        "constraints": {
            "max_primary_systems": 1,
            "max_secondary_influences": 1,
            "structure_cannot_override_style": True,
            "no_literal_brand_copy": True,
            "no_specialist_activation": True,
        },
        "not_design_md": True,
        "untrusted_text": True,
    }
    errors = check_selection(payload, policy)
    if errors:
        raise SelectionError("invalid selection artifact: " + ",".join(errors))
    project_root = project.resolve()
    if not project_root.is_dir() or project_root == Path(project_root.anchor):
        raise SelectionError("project must be an existing non-root directory")
    state_dir = project_root / ".impeccable"
    if state_dir.is_symlink():
        raise SelectionError("project .impeccable directory cannot be a symlink")
    destination = state_dir / "design-intelligence-selection.json"
    if destination.is_symlink():
        raise SelectionError("selection artifact cannot be a symlink")
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, raw_tmp = tempfile.mkstemp(prefix=".design-intelligence-", suffix=".json", dir=destination.parent)
    tmp = Path(raw_tmp)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
        os.replace(tmp, destination)
    finally:
        tmp.unlink(missing_ok=True)
    return {
        "status": "ok",
        "path": str(destination),
        "selection": payload,
        "selected_evidence": selected_evidence,
        "selected_structure_card": selected_structure_card,
    }
