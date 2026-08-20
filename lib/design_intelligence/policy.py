"""Load vendor policy and check catalog item fields with the stdlib."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

def _vendor_dir() -> Path:
    """Resolve policy assets in the source tree or packaged Impeccable skill."""
    here = Path(__file__).resolve()
    source = here.parents[2] / "vendor" / "design-intelligence"
    if source.is_dir():
        return source
    packaged = here.parents[2] / "design-intelligence"
    if packaged.is_dir():
        return packaged
    return source


VENDOR_DIR = _vendor_dir()


class PolicyError(ValueError):
    pass


def vendor_dir() -> Path:
    return VENDOR_DIR


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_policy(root: Path | None = None) -> dict[str, Any]:
    base = root or VENDOR_DIR
    return load_json(base / "policy.json")


def load_taxonomy(root: Path | None = None) -> dict[str, Any]:
    base = root or VENDOR_DIR
    return load_json(base / "taxonomy.json")


def load_known_sources(root: Path | None = None) -> dict[str, Any]:
    base = root or VENDOR_DIR
    return load_json(base / "known-sources.json")


def known_hash_map(known: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for snap in known.get("snapshots") or []:
        for name, digest in (snap.get("archives") or {}).items():
            out[digest] = str(snap.get("id") or name)
            out[name] = digest
    return out


def snapshot_for_hashes(known: dict[str, Any], hashes: dict[str, str]) -> str | None:
    """Return a snapshot id only when the incoming set equals that snapshot exactly."""
    incoming = {str(name): str(digest) for name, digest in hashes.items()}
    for snap in known.get("snapshots") or []:
        archives = {str(name): str(digest) for name, digest in (snap.get("archives") or {}).items()}
        if not archives:
            continue
        if incoming == archives:
            return str(snap.get("id"))
    return None


def compile_secret_patterns(policy: dict[str, Any]) -> list[re.Pattern[str]]:
    from . import text as text_mod

    return text_mod.compile_secret_patterns(policy)


def check_lock(lock: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(lock, dict):
        return ["lock"]
    if lock.get("schema_version") != 1:
        errors.append("schema_version")
    gid = str(lock.get("generation_id") or "")
    if not re.fullmatch(r"[0-9a-f]{16,64}", gid):
        errors.append("generation_id")
    if not re.fullmatch(r"catalog-[0-9a-f]+\.sqlite3", str(lock.get("sqlite_filename") or "")):
        errors.append("sqlite_filename")
    if not re.fullmatch(r"catalog-[0-9a-f]+\.jsonl", str(lock.get("jsonl_filename") or "")):
        errors.append("jsonl_filename")
    for digest_key in ("sqlite_sha256", "jsonl_sha256"):
        if not re.fullmatch(r"[0-9a-f]{64}", str(lock.get(digest_key) or "")):
            errors.append(digest_key)
    if not lock.get("created_at"):
        errors.append("created_at")
    hashes = lock.get("input_hashes")
    if not isinstance(hashes, dict):
        errors.append("input_hashes")
    else:
        from . import text as text_mod

        for name, digest in hashes.items():
            if not isinstance(name, str) or not text_mod.is_archive_name(name):
                errors.append(f"input_hashes.{name}")
            if not re.fullmatch(r"[0-9a-f]{64}", str(digest)):
                errors.append(f"input_hashes.{name}")
    return errors


ITEM_REQUIRED = (
    "schema_version",
    "id",
    "kind",
    "name",
    "description",
    "source",
    "license",
    "trust",
    "evidence_tier",
    "execution_class",
    "style_authority",
    "intent",
    "modes",
    "surfaces",
    "platforms",
    "categories",
    "tags",
    "capabilities_required",
    "provider",
    "search_policy",
    "selection_policy",
    "canonical_id",
    "alias_of",
    "duplicate_of",
    "dedup_reason",
    "untrusted_text",
    "normalization_status",
    "extraction_evidence",
    "warnings",
)
STRING_ARRAYS = (
    "intent",
    "modes",
    "surfaces",
    "platforms",
    "categories",
    "tags",
    "capabilities_required",
    "extraction_evidence",
    "warnings",
)


def check_item(item: dict[str, Any], policy: dict[str, Any]) -> list[str]:
    from . import text as text_mod

    if not isinstance(item, dict):
        return ["item"]
    errors: list[str] = []
    enums = policy.get("enums") or {}

    for key in item:
        if key not in text_mod.ROOT_KEYS:
            errors.append(f"additional:{key}")
    for key in ITEM_REQUIRED:
        if key not in item:
            errors.append(f"missing {key}")

    if item.get("schema_version") != 1 or not isinstance(item.get("schema_version"), int):
        errors.append("schema_version")

    def enum_ok(key: str, value: Any) -> None:
        allowed = enums.get(key)
        if allowed is None:
            return
        if value not in allowed:
            errors.append(f"{key}={value!r}")

    if not isinstance(item.get("id"), str) or not text_mod.is_catalog_id(item.get("id")):
        errors.append("id")
    if not isinstance(item.get("name"), str):
        errors.append("name")
    if not isinstance(item.get("description"), str):
        errors.append("description")
    if not isinstance(item.get("canonical_id"), str) or not text_mod.is_catalog_id(item.get("canonical_id")):
        errors.append("canonical_id")
    if not isinstance(item.get("untrusted_text"), bool):
        errors.append("untrusted_text")
    if "search_text" in item and not isinstance(item.get("search_text"), str):
        errors.append("search_text")
    if "summary" in item and not isinstance(item.get("summary"), dict):
        errors.append("summary")

    provider = item.get("provider")
    if provider is not None and not (isinstance(provider, str) and text_mod.is_provider(provider)):
        errors.append("provider")

    for key in ("alias_of", "duplicate_of"):
        value = item.get(key)
        if value is None:
            continue
        if not isinstance(value, str) or not text_mod.is_catalog_id(value):
            errors.append(key)

    enum_ok("kind", item.get("kind"))
    enum_ok("trust", item.get("trust"))
    enum_ok("evidence_tier", item.get("evidence_tier"))
    enum_ok("execution_class", item.get("execution_class"))
    enum_ok("style_authority", item.get("style_authority"))
    enum_ok("search_policy", item.get("search_policy"))
    enum_ok("selection_policy", item.get("selection_policy"))
    enum_ok("normalization_status", item.get("normalization_status"))
    if item.get("dedup_reason") is not None:
        enum_ok("dedup_reason", item.get("dedup_reason"))

    source = item.get("source")
    if not isinstance(source, dict):
        errors.append("source")
    else:
        for key in text_mod.SOURCE_KEYS:
            if key not in source:
                errors.append(f"source.{key}")
        for key in source:
            if key not in text_mod.SOURCE_KEYS:
                errors.append(f"source.additional:{key}")
        if not isinstance(source.get("archive"), str) or not text_mod.is_archive_name(source.get("archive")):
            errors.append("source.archive")
        if not isinstance(source.get("path"), str) or not text_mod.is_source_path(source.get("path")):
            errors.append("source.path")
        url = source.get("url")
        if url is not None and not (isinstance(url, str) and text_mod.is_http_url(url)):
            errors.append("source.url")
        version = source.get("version")
        if version is not None and not (isinstance(version, str) and text_mod.is_version(version)):
            errors.append("source.version")
        digest = source.get("content_sha256")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            errors.append("content_sha256")

    license_obj = item.get("license")
    if not isinstance(license_obj, dict):
        errors.append("license")
    else:
        for key in text_mod.LICENSE_KEYS:
            if key not in license_obj:
                errors.append(f"license.{key}")
        for key in license_obj:
            if key not in text_mod.LICENSE_KEYS:
                errors.append(f"license.additional:{key}")
        enum_ok("license_status", license_obj.get("status"))
        enum_ok("redistribution", license_obj.get("redistribution"))
        spdx = license_obj.get("spdx")
        if spdx is not None and not (isinstance(spdx, str) and text_mod.is_spdx(spdx)):
            errors.append("license.spdx")

    for key in STRING_ARRAYS:
        value = item.get(key)
        if not isinstance(value, list):
            errors.append(key)
        elif any(not isinstance(entry, str) for entry in value):
            errors.append(f"{key}.items")

    if item.get("runtime_availability") is not None or item.get("available_via") is not None:
        errors.append("host_probe_persisted")
    if "execution_status" in item:
        errors.append("execution_status_persisted")

    pointer = item.get("alias_of") or item.get("duplicate_of")
    if pointer and pointer == item.get("id"):
        errors.append("self_pointer")

    if text_mod.find_secret_hits(item, policy):
        errors.append("secret_leak")

    return errors
