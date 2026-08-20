"""Bank import, item extraction, and generational catalog commit."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from . import archive as archive_mod
from . import classify
from . import normalize
from . import policy as policy_mod
from . import text as text_mod

FAMILIES = ("systems", "templates", "plugins", "skills")
SKIP_PLUGIN_ROOTS = {
    "AGENTS.md",
    "README.md",
    "README.zh-CN.md",
    "registry",
    "spec",
    "open-design",
}


class CatalogError(ValueError):
    pass


def resolve_bank(explicit: str | None, env: dict[str, str] | None = None, home: Path | None = None) -> Path:
    environ = env if env is not None else os.environ
    if explicit:
        return Path(explicit).expanduser()
    for var in ("ANTIGRAVITY_DESIGN_BANK", "GROK_DESIGN_BANK", "CLAUDE_DESIGN_BANK", "GROK_DESIGN_INTELLIGENCE_BANK"):
        if environ.get(var):
            return Path(environ[var]).expanduser()
    root = home if home is not None else Path.home()
    return root / "Design"


def bank_dirs(bank: Path) -> dict[str, Path]:
    return {
        "root": bank,
        "raw": bank / "raw",
        "normalized": bank / "normalized",
        "catalog": bank / "catalog",
        "quarantine": bank / "quarantine",
        "reports": bank / "reports",
        "cache": bank / "cache",
    }


def ensure_bank(bank: Path) -> dict[str, Path]:
    dirs = bank_dirs(bank)
    for name in FAMILIES:
        (dirs["raw"] / name).mkdir(parents=True, exist_ok=True)
        (dirs["normalized"] / {"systems": "systems", "templates": "structures", "plugins": "recipes", "skills": "specialists"}[name]).mkdir(
            parents=True, exist_ok=True
        )
    for key in ("catalog", "quarantine", "reports", "cache"):
        dirs[key].mkdir(parents=True, exist_ok=True)
    return dirs


def empty_item() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "id": "",
        "kind": "visual",
        "name": "",
        "description": "",
        "source": {
            "archive": "",
            "path": "",
            "url": None,
            "version": None,
            "content_sha256": "0" * 64,
        },
        "license": {"spdx": None, "status": "unknown", "redistribution": "local-only"},
        "trust": "unknown",
        "evidence_tier": "E0",
        "execution_class": "reference-only",
        "style_authority": "none",
        "intent": [],
        "modes": [],
        "surfaces": [],
        "platforms": [],
        "categories": [],
        "tags": [],
        "capabilities_required": [],
        "provider": None,
        "search_policy": "metadata-only",
        "selection_policy": "never",
        "canonical_id": "",
        "alias_of": None,
        "duplicate_of": None,
        "dedup_reason": None,
        "untrusted_text": True,
        "normalization_status": "partial",
        "extraction_evidence": [],
        "warnings": [],
        "summary": {},
        "search_text": "",
    }


def dump_line(item: dict[str, Any]) -> str:
    return json.dumps(item, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_lock(bank: Path) -> dict[str, Any] | None:
    path = bank_dirs(bank)["catalog"] / "catalog.lock.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def generation_id_for(jsonl_bytes: bytes, input_hashes: dict[str, str]) -> str:
    parts: list[tuple[str, bytes]] = [("catalog.jsonl", jsonl_bytes)]
    for name in sorted(input_hashes):
        parts.append((f"archive:{name}", str(input_hashes[name]).encode("ascii")))
    return normalize.framed_hash(parts)[:16]


def persist_sanitize(item: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    cleaned = text_mod.sanitize_tree(item, policy)
    cleaned["search_text"] = _search_text(cleaned, policy)
    return cleaned


def load_items(bank: Path, policy: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    lock = read_lock(bank)
    if not lock:
        return []
    errors = policy_mod.check_lock(lock)
    if errors:
        raise CatalogError("lock:" + ",".join(errors))
    catalog = bank_dirs(bank)["catalog"]
    jsonl = catalog / lock["jsonl_filename"]
    sqlite_path = catalog / lock["sqlite_filename"]
    if not jsonl.is_file() or not sqlite_path.is_file():
        raise CatalogError("lock artifacts missing")
    jsonl_bytes = jsonl.read_bytes()
    if sha256_bytes(jsonl_bytes) != lock.get("jsonl_sha256"):
        raise CatalogError("jsonl hash mismatch")
    if sha256_bytes(sqlite_path.read_bytes()) != lock.get("sqlite_sha256"):
        raise CatalogError("sqlite hash mismatch")
    expected = generation_id_for(jsonl_bytes, {str(k): str(v) for k, v in (lock.get("input_hashes") or {}).items()})
    if expected != lock.get("generation_id"):
        raise CatalogError("generation_id mismatch")
    items: list[dict[str, Any]] = []
    for line in jsonl_bytes.decode("utf-8").splitlines():
        if line.strip():
            items.append(json.loads(line))
    checker = policy if policy is not None else policy_mod.load_policy()
    for item in items:
        row_errors = policy_mod.check_item(item, checker)
        if row_errors:
            raise CatalogError(f"catalog_row:{item.get('id')}:{','.join(row_errors)}")
    return items


def import_archive(
    bank: Path,
    archive_path: Path,
    policy: dict[str, Any],
    taxonomy: dict[str, Any],
) -> dict[str, Any]:
    ensure_bank(bank)
    inspection = archive_mod.inspect_archive(archive_path, policy, taxonomy)
    payload = {
        "logical_name": inspection.logical_name,
        "sha256": inspection.sha256,
        "family": inspection.family,
        "blocked": inspection.blocked,
        "members": inspection.members,
        "issues": [issue.code for issue in inspection.issues],
    }
    dest_family = inspection.family if inspection.family in FAMILIES else None
    if dest_family is None and "UNSUPPORTED_ARCHIVE_FAMILY" not in payload["issues"]:
        payload["issues"] = list(payload["issues"]) + ["UNSUPPORTED_ARCHIVE_FAMILY"]
    owners = _logical_name_hashes(bank)
    if (
        dest_family is not None
        and inspection.logical_name in owners
        and owners[inspection.logical_name] != inspection.sha256
    ):
        payload["blocked"] = True
        payload["issues"] = list(payload["issues"]) + ["DUPLICATE_LOGICAL_NAME"]
    if inspection.blocked or dest_family is None or "DUPLICATE_LOGICAL_NAME" in payload["issues"]:
        payload["blocked"] = True
        dest = bank_dirs(bank)["quarantine"] / f"{inspection.sha256}.zip"
        shutil.copy2(archive_path, dest)
        (dest.with_suffix(".issues.json")).write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )
        return payload
    dest_dir = bank_dirs(bank)["raw"] / dest_family
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{inspection.sha256}.zip"
    shutil.copy2(archive_path, dest)
    meta = {"logical_name": inspection.logical_name, "family": dest_family, "sha256": inspection.sha256}
    dest.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return payload


def listed_raw(bank: Path) -> list[tuple[str, Path, dict[str, Any]]]:
    found: list[tuple[str, Path, dict[str, Any]]] = []
    raw = bank_dirs(bank)["raw"]
    for family in FAMILIES:
        folder = raw / family
        if not folder.is_dir():
            continue
        for zip_path in sorted(folder.glob("*.zip")):
            meta_path = zip_path.with_suffix(".meta.json")
            meta = {"logical_name": zip_path.name, "family": family, "sha256": zip_path.stem}
            if meta_path.is_file():
                meta.update(json.loads(meta_path.read_text(encoding="utf-8")))
            found.append((family, zip_path, meta))
    return found


def _logical_name_hashes(bank: Path) -> dict[str, str]:
    owners: dict[str, str] = {}
    for _family, zip_path, meta in listed_raw(bank):
        name = str(meta.get("logical_name") or archive_mod.logical_name(zip_path))
        digest = str(meta.get("sha256") or "")
        if name:
            owners[name] = digest
    return owners


def _duplicate_logical_names(archives_meta: list[dict[str, Any]]) -> list[str]:
    seen: dict[str, str] = {}
    dupes: list[str] = []
    for row in archives_meta:
        name = str(row.get("logical_name") or "")
        digest = str(row.get("sha256") or "")
        if not name:
            continue
        if name in seen and seen[name] != digest and name not in dupes:
            dupes.append(name)
        seen[name] = digest
    return dupes


def rebuild(
    bank: Path,
    policy: dict[str, Any],
    taxonomy: dict[str, Any],
    *,
    now: Callable[[], datetime] | None = None,
) -> dict[str, Any]:
    dirs = ensure_bank(bank)
    archives_meta: list[dict[str, Any]] = []
    items: list[dict[str, Any]] = []
    warnings: list[str] = []
    clock = now or (lambda: datetime.now(timezone.utc))

    for family, zip_path, meta in listed_raw(bank):
        inspection = archive_mod.inspect_archive(zip_path, policy, taxonomy)
        archives_meta.append(
            {
                "logical_name": meta.get("logical_name") or inspection.logical_name,
                "sha256": inspection.sha256,
                "family": family,
                "blocked": inspection.blocked,
                "members": inspection.members,
                "issues": [issue.code for issue in inspection.issues],
            }
        )
        use_family = inspection.family if inspection.family in FAMILIES else None
        if inspection.blocked or use_family is None:
            warnings.append(f"blocked:{inspection.logical_name}")
            continue
        with archive_mod.open_zip(zip_path) as handle:
            items.extend(
                extract_archive(
                    handle,
                    family=use_family,
                    logical_name=str(meta.get("logical_name") or inspection.logical_name),
                    policy=policy,
                    taxonomy=taxonomy,
                )
            )

    dupes = _duplicate_logical_names(archives_meta)
    if dupes:
        failed = {"error": "duplicate_logical_name", "names": dupes}
        (dirs["reports"] / "rebuild-failed.json").write_text(
            json.dumps(failed, indent=2) + "\n", encoding="utf-8"
        )
        raise CatalogError("duplicate_logical_name:" + ",".join(dupes))

    items = apply_lineage(items, taxonomy)
    items = apply_content_duplicates(items)
    finalized: list[dict[str, Any]] = []
    schema_errors: list[str] = []
    for item in items:
        item["canonical_id"] = item.get("alias_of") or item.get("duplicate_of") or item["id"]
        item = persist_sanitize(item, policy)
        errors = policy_mod.check_item(item, policy)
        if errors:
            schema_errors.append(f"{item.get('id')}:{','.join(errors)}")
            continue
        finalized.append(item)
    if schema_errors:
        failed = {
            "error": "schema_invalid",
            "items": schema_errors[:32],
        }
        (dirs["reports"] / "rebuild-failed.json").write_text(
            json.dumps(failed, indent=2) + "\n", encoding="utf-8"
        )
        raise CatalogError("schema_invalid:" + ";".join(schema_errors[:16]))
    items = finalized

    items.sort(key=lambda row: row["id"])
    jsonl = "".join(dump_line(item) + "\n" for item in items)
    jsonl_bytes = jsonl.encode("utf-8")
    input_hashes = {row["logical_name"]: row["sha256"] for row in archives_meta}
    input_hashes = {name: input_hashes[name] for name in sorted(input_hashes)}
    generation_id = generation_id_for(jsonl_bytes, input_hashes)

    lock = read_lock(bank)
    if lock and lock.get("generation_id") == generation_id and lock.get("input_hashes") == input_hashes:
        try:
            load_items(bank, policy)
        except CatalogError:
            pass
        else:
            return {
                "status": "ok",
                "generation_id": generation_id,
                "reused": True,
                "counts": _counts(items),
                "archives": archives_meta,
                "warnings": warnings,
                "items": items,
            }

    sqlite_name = f"catalog-{generation_id}.sqlite3"
    jsonl_name = f"catalog-{generation_id}.jsonl"
    incoming = Path(tempfile.mkdtemp(prefix="di-incoming-", dir=str(dirs["catalog"])))
    try:
        incoming_jsonl = incoming / jsonl_name
        incoming_sqlite = incoming / sqlite_name
        incoming_jsonl.write_bytes(jsonl_bytes)
        _write_sqlite(incoming_sqlite, items)
        jsonl_sha = sha256_bytes(incoming_jsonl.read_bytes())
        sqlite_sha = sha256_bytes(incoming_sqlite.read_bytes())
        final_jsonl = dirs["catalog"] / jsonl_name
        final_sqlite = dirs["catalog"] / sqlite_name
        os.replace(incoming_jsonl, final_jsonl)
        os.replace(incoming_sqlite, final_sqlite)
        lock_doc = {
            "generation_id": generation_id,
            "schema_version": 1,
            "input_hashes": input_hashes,
            "sqlite_filename": sqlite_name,
            "sqlite_sha256": sqlite_sha,
            "jsonl_filename": jsonl_name,
            "jsonl_sha256": jsonl_sha,
            "created_at": clock().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        _atomic_write_json(dirs["catalog"] / "catalog.lock.json", lock_doc)
    except Exception:
        failed = {
            "error": "rebuild_failed",
            "generation_id": generation_id,
        }
        (dirs["reports"] / "rebuild-failed.json").write_text(
            json.dumps(failed, indent=2) + "\n", encoding="utf-8"
        )
        raise
    finally:
        shutil.rmtree(incoming, ignore_errors=True)

    _gc_generations(dirs["catalog"], generation_id, int((policy.get("keep_generations") or 2)))
    return {
        "status": "ok",
        "generation_id": generation_id,
        "reused": False,
        "counts": _counts(items),
        "archives": archives_meta,
        "warnings": warnings,
        "items": items,
    }


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _write_sqlite(path: Path, items: list[dict[str, Any]]) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.execute("CREATE TABLE items (id TEXT PRIMARY KEY, kind TEXT, json TEXT NOT NULL)")
        conn.executemany(
            "INSERT INTO items(id, kind, json) VALUES (?, ?, ?)",
            [(item["id"], item["kind"], dump_line(item)) for item in items],
        )
        try:
            conn.execute(
                "CREATE VIRTUAL TABLE items_fts USING fts5(id, name, description, search_text, kind)"
            )
            conn.executemany(
                "INSERT INTO items_fts(id, name, description, search_text, kind) VALUES (?, ?, ?, ?, ?)",
                [
                    (
                        item["id"],
                        item.get("name") or "",
                        item.get("description") or "",
                        item.get("search_text") or "",
                        item.get("kind") or "",
                    )
                    for item in items
                ],
            )
        except sqlite3.OperationalError:
            pass
        conn.commit()
    finally:
        conn.close()


def _gc_generations(catalog: Path, current: str, keep: int) -> None:
    lock = catalog / "catalog.lock.json"
    live = {f"catalog-{current}.sqlite3", f"catalog-{current}.jsonl", "catalog.lock.json"}
    if lock.is_file():
        try:
            doc = json.loads(lock.read_text(encoding="utf-8"))
            live.add(str(doc.get("sqlite_filename") or ""))
            live.add(str(doc.get("jsonl_filename") or ""))
        except json.JSONDecodeError:
            pass
    generations = sorted(
        {path.name.split(".")[0].removeprefix("catalog-") for path in catalog.glob("catalog-*.jsonl")}
    )
    stale = [gen for gen in generations if gen != current]
    drop = stale[:- max(keep - 1, 0)] if keep > 1 else stale
    for gen in drop:
        for path in catalog.glob(f"catalog-{gen}.*"):
            if path.name not in live:
                path.unlink(missing_ok=True)


def _counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "items": len(items),
        "systems": 0,
        "structures": 0,
        "recipes": 0,
        "specialists": 0,
        "aliases": 0,
        "duplicates": 0,
        "stubs": 0,
        "quarantined": 0,
    }
    for item in items:
        kind = item.get("kind")
        if kind == "system":
            counts["systems"] += 1
        elif kind == "structure":
            counts["structures"] += 1
        elif kind == "recipe":
            counts["recipes"] += 1
        elif kind == "specialist":
            counts["specialists"] += 1
        if item.get("alias_of"):
            counts["aliases"] += 1
        if item.get("duplicate_of"):
            counts["duplicates"] += 1
        if item.get("execution_class") == "stub":
            counts["stubs"] += 1
        if item.get("execution_class") == "quarantined":
            counts["quarantined"] += 1
    return counts


def extract_archive(
    handle,
    *,
    family: str,
    logical_name: str,
    policy: dict[str, Any],
    taxonomy: dict[str, Any],
) -> list[dict[str, Any]]:
    names = archive_mod.member_names(handle)
    if family == "systems":
        return extract_systems(handle, names, logical_name, policy)
    if family == "templates":
        return extract_templates(handle, names, logical_name, policy)
    if family == "skills":
        return extract_skills(handle, names, logical_name, policy, taxonomy)
    if family == "plugins":
        return extract_plugins(handle, names, logical_name, policy, taxonomy)
    return []


def _read_text(handle, path: str, policy: dict[str, Any]) -> tuple[str | None, str | None]:
    try:
        return normalize.decode_text(archive_mod.read_member(handle, path, policy)), None
    except archive_mod.ArchiveError as exc:
        return None, str(exc)


def _owned_license(handle, folder: str, names: list[str], policy: dict[str, Any]) -> tuple[str | None, bool]:
    for filename in policy.get("license_files") or ["LICENSE"]:
        path = f"{folder.rstrip('/')}/{filename}"
        if archive_mod.has_file(names, path):
            text, err = _read_text(handle, path, policy)
            if err:
                return None, False
            return text, True
    return None, False


def extract_systems(handle, names: list[str], logical_name: str, policy: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    root = "design-systems"
    for slug in archive_mod.children(names, root):
        if slug.startswith("_") or slug.endswith(".md"):
            continue
        folder = f"{root}/{slug}"
        required = [f"{folder}/manifest.json", f"{folder}/DESIGN.md", f"{folder}/tokens.css"]
        missing = [path for path in required if not archive_mod.has_file(names, path)]
        manifest, err = normalize.load_json_member(handle, f"{folder}/manifest.json", policy)
        if err or manifest is None:
            continue
        design, derr = _read_text(handle, f"{folder}/DESIGN.md", policy)
        tokens, terr = _read_text(handle, f"{folder}/tokens.css", policy)
        parts: list[tuple[str, bytes]] = []
        warnings = []
        if missing:
            warnings.append("MISSING_MIN_SET")
        status = "complete" if not missing and not derr and not terr else "partial"
        for rel in ("manifest.json", "DESIGN.md", "tokens.css"):
            member = f"{folder}/{rel}"
            if archive_mod.has_file(names, member):
                try:
                    parts.append((rel, archive_mod.read_member(handle, member, policy)))
                except archive_mod.ArchiveError as exc:
                    warnings.append(str(exc))
        if not parts:
            continue
        license_text, owned = _owned_license(handle, folder, names, policy)
        declared = None
        if isinstance(manifest.get("license"), str):
            declared = manifest["license"]
        license_obj = classify.detect_license(license_text, declared, policy, item_owned=owned)
        cls = classify.classify_system(manifest, policy)
        summary, evidence = normalize.system_summary(manifest, design or "")
        name = text_mod.sanitize_name(str(manifest.get("name") or slug), policy)
        desc_src = str(manifest.get("description") or "")
        text_warnings = text_mod.warnings_for(desc_src + "\n" + (design or ""), policy)
        desc = text_mod.sanitize_description(desc_src, policy)
        item_id = normalize.make_id("system", str(manifest.get("id") or slug))
        item = empty_item()
        item.update(
            {
                "id": item_id,
                "kind": "system",
                "name": name,
                "description": desc,
                "source": {
                    "archive": logical_name,
                    "path": f"{folder}/manifest.json",
                    "url": cls.get("source_url"),
                    "version": None,
                    "content_sha256": normalize.framed_hash(parts),
                },
                "license": license_obj,
                "trust": cls["trust"],
                "evidence_tier": cls["evidence_tier"],
                "execution_class": cls["execution_class"],
                "style_authority": cls["style_authority"],
                "search_policy": cls["search_policy"],
                "selection_policy": cls["selection_policy"],
                "categories": text_mod.unique_keep(
                    [text_mod.sanitize_tag(str(manifest.get("category") or ""), policy)],
                    int((policy.get("text") or {}).get("tag_count_max") or 24),
                ),
                "canonical_id": item_id,
                "normalization_status": status,
                "extraction_evidence": evidence,
                "warnings": warnings + text_warnings + list(cls.get("warnings") or []),
                "summary": summary,
            }
        )
        item["search_text"] = _search_text(item, policy)
        items.append(item)
    return items


def extract_templates(handle, names: list[str], logical_name: str, policy: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    root = "design-templates"
    for slug in archive_mod.children(names, root):
        if slug.endswith(".md"):
            continue
        folder = f"{root}/{slug}"
        skill_path = f"{folder}/SKILL.md"
        if not archive_mod.has_file(names, skill_path):
            continue
        raw, err = _read_text(handle, skill_path, policy)
        if err or raw is None:
            continue
        front, fm_warn, body = normalize.parse_frontmatter(raw)
        name_key = str(front.get("name") or slug)
        card, evidence, status = normalize.structure_from_skill(front, body)
        coupled = normalize.looks_style_coupled(body)
        cls = classify.classify_structure(style_coupled=coupled, community=False, policy=policy)
        license_text, owned = _owned_license(handle, folder, names, policy)
        license_obj = classify.detect_license(license_text, None, policy, item_owned=owned)
        parts = [("SKILL.md", raw.encode("utf-8"))]
        item_id = normalize.make_id("structure", slug)
        desc_src = str(front.get("description") or "")
        text_warnings = text_mod.warnings_for(raw, policy)
        item = empty_item()
        item.update(
            {
                "id": item_id,
                "kind": "structure",
                "name": text_mod.sanitize_name(name_key, policy),
                "description": text_mod.sanitize_description(desc_src, policy),
                "source": {
                    "archive": logical_name,
                    "path": skill_path,
                    "url": None,
                    "version": None,
                    "content_sha256": normalize.framed_hash(parts),
                },
                "license": license_obj,
                "trust": cls["trust"],
                "evidence_tier": cls["evidence_tier"],
                "execution_class": cls["execution_class"],
                "style_authority": cls["style_authority"],
                "modes": [str(front["od.mode"])] if front.get("od.mode") else [],
                "surfaces": [str(front["od.surface"])] if front.get("od.surface") else [],
                "platforms": [str(front["od.platform"])] if front.get("od.platform") else [],
                "search_policy": cls["search_policy"],
                "selection_policy": cls["selection_policy"],
                "canonical_id": item_id,
                "normalization_status": status,
                "extraction_evidence": evidence,
                "warnings": fm_warn + text_warnings + list(cls.get("warnings") or []),
                "summary": card,
            }
        )
        item["search_text"] = _search_text(item, policy)
        items.append(item)
    return items


def extract_skills(
    handle,
    names: list[str],
    logical_name: str,
    policy: dict[str, Any],
    taxonomy: dict[str, Any],
) -> list[dict[str, Any]]:
    del taxonomy
    items: list[dict[str, Any]] = []
    root = "skills"
    for slug in archive_mod.children(names, root):
        if slug.endswith(".md"):
            continue
        folder = f"{root}/{slug}"
        skill_path = f"{folder}/SKILL.md"
        if not archive_mod.has_file(names, skill_path):
            continue
        raw, err = _read_text(handle, skill_path, policy)
        if err or raw is None:
            continue
        front, fm_warn, body = normalize.parse_frontmatter(raw)
        name_key = str(front.get("name") or slug)
        cls = classify.classify_specialist(
            name=name_key, body=body, front=front, community=False, policy=policy
        )
        license_text, owned = _owned_license(handle, folder, names, policy)
        license_obj = classify.detect_license(license_text, None, policy, item_owned=owned)
        item_id = normalize.make_id("specialist", name_key)
        text_warnings = text_mod.warnings_for(raw, policy)
        item = empty_item()
        item.update(
            {
                "id": item_id,
                "kind": "specialist",
                "name": text_mod.sanitize_name(name_key, policy),
                "description": text_mod.sanitize_description(str(front.get("description") or ""), policy),
                "source": {
                    "archive": logical_name,
                    "path": skill_path,
                    "url": str(front["od.upstream"]) if isinstance(front.get("od.upstream"), str) else None,
                    "version": None,
                    "content_sha256": normalize.framed_hash([("SKILL.md", raw.encode("utf-8"))]),
                },
                "license": license_obj,
                "trust": cls["trust"],
                "evidence_tier": cls["evidence_tier"],
                "execution_class": cls["execution_class"],
                "style_authority": cls["style_authority"],
                "capabilities_required": cls.get("capabilities_required") or [],
                "provider": cls.get("provider"),
                "search_policy": cls["search_policy"],
                "selection_policy": cls["selection_policy"],
                "canonical_id": item_id,
                "normalization_status": "partial" if fm_warn else "complete",
                "extraction_evidence": ["SKILL.md"] + (["frontmatter:name"] if front.get("name") else []),
                "warnings": fm_warn + text_warnings + list(cls.get("warnings") or []),
            }
        )
        item["search_text"] = _search_text(item, policy)
        items.append(item)
    return items


def extract_plugins(
    handle,
    names: list[str],
    logical_name: str,
    policy: dict[str, Any],
    taxonomy: dict[str, Any],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    root = "plugins"
    for slug in archive_mod.children(names, f"{root}/community"):
        items.append(
            _plugin_item(
                handle,
                names,
                folder=f"{root}/community/{slug}",
                logical_name=logical_name,
                policy=policy,
                taxonomy=taxonomy,
                community=True,
                official=False,
            )
        )
    official_kinds = (
        "atoms",
        "scenarios",
        "examples",
        "design-systems",
        "image-templates",
        "video-templates",
    )
    for kind in official_kinds:
        for slug in archive_mod.children(names, f"{root}/_official/{kind}"):
            items.append(
                _plugin_item(
                    handle,
                    names,
                    folder=f"{root}/_official/{kind}/{slug}",
                    logical_name=logical_name,
                    policy=policy,
                    taxonomy=taxonomy,
                    community=False,
                    official=True,
                )
            )
    for slug in archive_mod.children(names, f"{root}/spec/examples"):
        items.append(
            _plugin_item(
                handle,
                names,
                folder=f"{root}/spec/examples/{slug}",
                logical_name=logical_name,
                policy=policy,
                taxonomy=taxonomy,
                community=False,
                official=False,
            )
        )
    return [item for item in items if item]


def _plugin_item(
    handle,
    names: list[str],
    *,
    folder: str,
    logical_name: str,
    policy: dict[str, Any],
    taxonomy: dict[str, Any],
    community: bool,
    official: bool,
) -> dict[str, Any] | None:
    del taxonomy
    od_path = f"{folder}/open-design.json"
    skill_path = f"{folder}/SKILL.md"
    if not archive_mod.has_file(names, od_path) and not archive_mod.has_file(names, skill_path):
        return None
    od: dict[str, Any] = {}
    od_err = None
    if archive_mod.has_file(names, od_path):
        od, od_err = normalize.load_json_member(handle, od_path, policy)
        if od is None:
            od = {}
    skill_text = ""
    if archive_mod.has_file(names, skill_path):
        skill_text, _ = _read_text(handle, skill_path, policy)
        skill_text = skill_text or ""
    front, fm_warn, body = normalize.parse_frontmatter(skill_text) if skill_text else ({}, [], "")
    name_key = str(od.get("name") or front.get("name") or folder.rsplit("/", 1)[-1])
    cls = classify.classify_recipe(path=folder, community=community, official=official, policy=policy)
    license_text, owned = _owned_license(handle, folder, names, policy)
    declared = od.get("license") if isinstance(od.get("license"), str) else None
    license_obj = classify.detect_license(license_text, declared, policy, item_owned=owned)
    primary_path = od_path if archive_mod.has_file(names, od_path) else skill_path
    try:
        primary_bytes = archive_mod.read_member(handle, primary_path, policy)
    except archive_mod.ArchiveError:
        return None
    digest = normalize.framed_hash([(Path(primary_path).name, primary_bytes)])
    desc_src = str(od.get("description") or front.get("description") or "")
    text_warnings = text_mod.warnings_for(desc_src + "\n" + skill_text, policy)
    summary: dict[str, Any] = {}
    evidence = [primary_path]
    if isinstance(od.get("od"), dict):
        inner = od["od"]
        for key in ("kind", "mode", "scenario", "capabilities"):
            if key in inner:
                summary[key] = inner[key]
                evidence.append(f"open-design.json:od.{key}")
    item_id = normalize.make_id("recipe", name_key)
    item = empty_item()
    item.update(
        {
            "id": item_id,
            "kind": "recipe",
            "name": text_mod.sanitize_name(str(od.get("title") or name_key), policy),
            "description": text_mod.sanitize_description(desc_src, policy),
            "source": {
                "archive": logical_name,
                "path": primary_path,
                "url": od.get("homepage") if isinstance(od.get("homepage"), str) else None,
                "version": str(od["version"]) if od.get("version") else None,
                "content_sha256": digest,
            },
            "license": license_obj,
            "trust": cls["trust"],
            "evidence_tier": cls["evidence_tier"],
            "execution_class": cls["execution_class"],
            "style_authority": cls["style_authority"],
            "search_policy": cls["search_policy"],
            "selection_policy": cls["selection_policy"],
            "canonical_id": item_id,
            "normalization_status": "partial" if (od_err or fm_warn) else "complete",
            "extraction_evidence": evidence,
            "warnings": ([od_err] if od_err else []) + fm_warn + text_warnings,
            "summary": summary,
        }
    )
    if body:
        item["modes"] = [str(front["od.mode"])] if front.get("od.mode") else item["modes"]
    item["search_text"] = _search_text(item, policy)
    item["_folder"] = folder
    item["_skill_hash"] = (
        normalize.framed_hash([("SKILL.md", skill_text.encode("utf-8"))]) if skill_text else None
    )
    item["_skill_name"] = str(front.get("name") or "")
    return item


def apply_lineage(items: list[dict[str, Any]], taxonomy: dict[str, Any]) -> list[dict[str, Any]]:
    by_id = {item["id"]: item for item in items}
    lineage = taxonomy.get("lineage") or {}
    sys_prefix = lineage.get("official_design_systems_prefix") or "plugins/_official/design-systems/"
    ex_prefix = lineage.get("official_examples_prefix") or "plugins/_official/examples/"
    for item in items:
        folder = str(item.pop("_folder", "") or "")
        skill_hash = item.pop("_skill_hash", None)
        skill_name = item.pop("_skill_name", "")
        path = str((item.get("source") or {}).get("path") or folder)
        if path.startswith(sys_prefix) or folder.startswith(sys_prefix):
            slug = classify.lineage_slug(folder or path, sys_prefix)
            target = normalize.make_id("system", slug or "")
            if slug and target in by_id:
                item["alias_of"] = target
                item["dedup_reason"] = "path-lineage"
                item["canonical_id"] = target
            continue
        if path.startswith(ex_prefix) or folder.startswith(ex_prefix):
            slug = classify.lineage_slug(folder or path, ex_prefix)
            target = normalize.make_id("structure", slug or "")
            if not slug or target not in by_id:
                continue
            structure = by_id[target]
            same_name = bool(skill_name) and normalize.normalize_slug(skill_name) == normalize.normalize_slug(
                structure.get("name") or slug
            )
            same_hash = skill_hash and skill_hash == (structure.get("source") or {}).get("content_sha256")
            if same_name or same_hash:
                item["alias_of"] = target
                item["dedup_reason"] = "path-lineage"
                item["canonical_id"] = target
    return items


def apply_content_duplicates(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[tuple[str, str], str] = {}
    id_owner: dict[str, str] = {}
    for item in items:
        if item.get("alias_of"):
            continue
        kind = item["kind"]
        digest = str((item.get("source") or {}).get("content_sha256") or "")
        key = (kind, digest)
        if digest and key in seen:
            item["duplicate_of"] = seen[key]
            item["dedup_reason"] = "content-hash"
            item["canonical_id"] = seen[key]
            continue
        if digest:
            seen[key] = item["id"]
        item_id = item["id"]
        if item_id in id_owner and id_owner[item_id] != digest:
            suffix = digest[:8] if digest else "dup"
            item["id"] = f"{item_id}-{suffix}"
            item["warnings"] = list(item.get("warnings") or []) + ["DUPLICATE_NORMALIZED_ID"]
            item["dedup_reason"] = "normalized-id"
        else:
            id_owner[item_id] = digest
    return items


def _search_text(item: dict[str, Any], policy: dict[str, Any]) -> str:
    bits = [
        item.get("name") or "",
        item.get("description") or "",
        " ".join(item.get("categories") or []),
        " ".join(item.get("tags") or []),
        " ".join(str(v) for v in (item.get("summary") or {}).values() if isinstance(v, str)),
    ]
    return text_mod.sanitize_field(
        " ".join(bits),
        policy,
        max_len=int((policy.get("text") or {}).get("search_text_max") or 1200),
    )
