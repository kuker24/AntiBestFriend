"""Catalog doctor. Does not write host probes into the catalog."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import archive as archive_mod
from . import policy as policy_mod
from .catalog import generation_id_for, listed_raw, load_items, read_lock, resolve_bank, bank_dirs
from .rank import derive_hit, load_allowlist, probe_item


def doctor(
    bank: Path | None,
    policy: dict[str, Any],
    known: dict[str, Any],
    *,
    allowlist_path: Path | None = None,
    expected_sha: dict[str, str] | None = None,
    claimed_snapshot: str | None = None,
    host_commands: set[str] | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    status = "PASS"

    def add(name: str, level: str, detail: str = "") -> None:
        nonlocal status
        checks.append({"name": name, "level": level, "detail": detail})
        if level == "BLOCKED":
            status = "BLOCKED"
        elif level == "DEGRADED" and status != "BLOCKED":
            status = "DEGRADED"

    if bank is None:
        bank = resolve_bank(None, env=env)
    if not bank.exists():
        add("bank_root", "DEGRADED", "missing")
        return {"status": status, "checks": checks, "bank": str(bank)}

    add("bank_root", "PASS", str(bank))
    lock = read_lock(bank)
    if lock is None:
        add("catalog_lock", "DEGRADED", "missing")
        return {"status": status, "checks": checks, "bank": str(bank)}

    lock_errors = policy_mod.check_lock(lock)
    if lock_errors:
        add("catalog_lock", "BLOCKED", ",".join(lock_errors))
        return {"status": status, "checks": checks, "bank": str(bank)}
    add("catalog_lock", "PASS")

    if lock.get("schema_version") != 1:
        add("schema_version", "BLOCKED", str(lock.get("schema_version")))
    else:
        add("schema_version", "PASS", "1")

    try:
        items = load_items(bank, policy)
        add("index_parse", "PASS", str(len(items)))
        add("lock_artifacts", "PASS")
    except Exception as exc:
        add("index_parse", "BLOCKED", str(exc))
        add("lock_artifacts", "BLOCKED", str(exc))
        return {"status": status, "checks": checks, "bank": str(bank)}

    catalog = bank_dirs(bank)["catalog"]
    jsonl_path = catalog / lock["jsonl_filename"]
    expected_gen = generation_id_for(
        jsonl_path.read_bytes(),
        {str(k): str(v) for k, v in (lock.get("input_hashes") or {}).items()},
    )
    if expected_gen != lock.get("generation_id"):
        add("generation_identity", "BLOCKED", "lock generation_id does not match jsonl+inputs")
    else:
        add("generation_identity", "PASS")

    row_failures: list[str] = []
    for item in items:
        row_errors = policy_mod.check_item(item, policy)
        if row_errors:
            row_failures.append(str(item.get("id") or "?"))
    if row_failures:
        add("catalog_rows", "BLOCKED", ",".join(row_failures[:8]))
    else:
        add("catalog_rows", "PASS")

    ids = [item["id"] for item in items]
    if len(ids) != len(set(ids)):
        add("duplicate_ids", "BLOCKED", "catalog ids are not unique")
    else:
        add("duplicate_ids", "PASS")

    catalog_ids = set(ids)
    dangling = []
    for item in items:
        for key in ("alias_of", "duplicate_of"):
            pointer = item.get(key)
            if pointer and pointer not in catalog_ids:
                dangling.append(f"{item['id']}:{key}:{pointer}")
    if dangling:
        add("lineage_pointers", "BLOCKED", ",".join(dangling[:8]))
    else:
        add("lineage_pointers", "PASS")

    leaked = [item["id"] for item in items if str((item.get("source") or {}).get("path") or "").startswith("/")]
    if leaked:
        add("absolute_path_leak", "BLOCKED", ",".join(leaked[:8]))
    else:
        add("absolute_path_leak", "PASS")

    persisted_probe = [
        item["id"]
        for item in items
        if "runtime_availability" in item or "available_via" in item or "execution_status" in item
    ]
    if persisted_probe:
        add("host_probe_persisted", "BLOCKED", ",".join(persisted_probe[:8]))
    else:
        add("host_probe_persisted", "PASS")

    if any(item.get("execution_class") in {"stub", "quarantined"} or (item.get("license") or {}).get("status") == "unknown" for item in items):
        add("reference_limitations", "DEGRADED", "stubs, quarantine, or unknown license present")

    hashes: dict[str, str] = {}
    dup_names: list[str] = []
    for _family, zip_path, meta in listed_raw(bank):
        name = str(meta.get("logical_name") or zip_path.name)
        digest = archive_mod.sha256_file(zip_path)
        if name in hashes and hashes[name] != digest:
            dup_names.append(name)
        hashes[name] = digest
    if dup_names:
        add("duplicate_logical_name", "BLOCKED", ",".join(dup_names[:8]))
    else:
        add("duplicate_logical_name", "PASS")
    lock_inputs = {str(k): str(v) for k, v in (lock.get("input_hashes") or {}).items()}
    if hashes != lock_inputs:
        add("lock_inputs", "DEGRADED", "raw archive hashes differ from lock input_hashes")
    else:
        add("lock_inputs", "PASS")
    snapshot = policy_mod.snapshot_for_hashes(known, hashes)
    if hashes and snapshot:
        add("archive_hashes", "PASS", snapshot)
    elif hashes:
        add("archive_hashes", "DEGRADED", "unknown or partial snapshot")
    else:
        add("archive_hashes", "PASS", "no-raw-archives")

    if expected_sha:
        for name, digest in expected_sha.items():
            actual = hashes.get(name)
            if actual != digest:
                add("expected_sha", "BLOCKED", f"{name}")
    if claimed_snapshot:
        known_ids = {snap.get("id") for snap in known.get("snapshots") or []}
        if claimed_snapshot not in known_ids:
            add("claimed_snapshot", "BLOCKED", claimed_snapshot)
        elif snapshot != claimed_snapshot:
            add("claimed_snapshot", "BLOCKED", f"have {snapshot}")

    allowlist = load_allowlist(allowlist_path) if allowlist_path else set()
    missing_native = 0
    for item in items:
        if item.get("kind") != "specialist":
            continue
        probe = probe_item(item, allowlist=allowlist, host_commands=host_commands)
        derived = derive_hit(item, probe)
        if derived["execution_status"] in {"provider-missing", "connector-missing"}:
            missing_native += 1
    if missing_native:
        add("provider_connector", "DEGRADED", str(missing_native))
    else:
        add("provider_connector", "PASS")

    failed = bank / "reports" / "rebuild-failed.json"
    if failed.is_file() and lock:
        add("rebuild_failed_report", "DEGRADED", "present")

    return {
        "status": status,
        "checks": checks,
        "bank": str(bank),
        "generation_id": lock.get("generation_id"),
        "counts": {
            "items": len(items),
            "aliases": sum(1 for item in items if item.get("alias_of")),
            "duplicates": sum(1 for item in items if item.get("duplicate_of")),
        },
    }
