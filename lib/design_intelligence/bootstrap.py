"""Transactional Design Intelligence bank bootstrap.

Data-only. Never execute ZIP members, recipes, specialists, stubs, or
community plugins. Does not scan the filesystem for archives.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import stat
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from . import archive as archive_mod
from . import catalog
from . import doctor as doctor_mod
from . import policy as policy_mod
from . import rank
from . import text as text_mod


ALLOWED_DEGRADED_CHECKS = frozenset({"reference_limitations", "provider_connector"})
NEGATIVE_QUERY = "quantum-banana-xyz"
SEARCH_QUERIES = (
    "developer operations dashboard",
    "editorial technical documentation",
    "expressive AI product landing page",
    "trading analysis dashboard",
)
FAMILY_PATTERNS = {
    "systems": re.compile(r"^design-systems.*\.zip$", re.IGNORECASE),
    "templates": re.compile(r"^design-templates.*\.zip$", re.IGNORECASE),
    "plugins": re.compile(r"^plugins.*\.zip$", re.IGNORECASE),
    "skills": re.compile(r"^skills.*\.zip$", re.IGNORECASE),
}
IMPORT_ORDER = ("systems", "templates", "plugins", "skills")
CATALOG_OVERHEAD_BYTES = 64 * 1024 * 1024
SAFETY_MARGIN = 0.20
GLOB_CHARS = set("*?[]")
TX_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}$")
STAGE_NAME_RE = re.compile(r"^DesignIntelligence\.stage\.([A-Za-z0-9][A-Za-z0-9._-]{0,80})$")
RECOVERY_NAME_RE = re.compile(r"^DesignIntelligence\.recovery\.([A-Za-z0-9][A-Za-z0-9._-]{0,80})$")
TRANSACTION_MARKER = ".grokbestfriend-di-transaction.json"
MARKER_KIND_STAGE = "design-intelligence-stage"
MARKER_KIND_BANK = "design-intelligence-bank"
INSTALLER_ENV = "GROK_DI_INSTALLER"
INSTALLER_PHASES = frozenset({"all", "stage", "promote", "remove-staging", "recover-created"})


class BootstrapError(ValueError):
    def __init__(self, code: str, message: str = "") -> None:
        detail = message or code
        super().__init__(f"{code}: {detail}" if message else code)
        self.code = code
        self.detail = detail


@dataclass
class DiscoveredArchive:
    family: str
    path: Path
    logical_name: str
    sha256: str
    compressed_bytes: int
    uncompressed_bytes: int
    members: int
    blocked: bool
    issues: list[str] = field(default_factory=list)


def new_transaction_id() -> str:
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{now}-{os.getpid()}-{secrets.token_hex(4)}"


def tilde_display(path: Path, home: Path) -> str:
    resolved = path.resolve()
    try:
        rel = resolved.relative_to(home.resolve())
        return f"~/{rel.as_posix()}" if str(rel) != "." else "~"
    except ValueError:
        return resolved.name


def expand_tilde(value: str, home: Path) -> Path:
    if value == "~":
        return home
    if value.startswith("~/"):
        return home / value[2:]
    return Path(value)


def has_control_chars(value: str) -> bool:
    return any(ord(ch) < 32 for ch in value)


def contains_glob(value: str) -> bool:
    return any(ch in GLOB_CHARS for ch in value)


def installer_mutation_allowed(allow_mutation: bool | None = None) -> bool:
    if allow_mutation is True:
        return True
    if allow_mutation is False:
        return False
    return os.environ.get(INSTALLER_ENV) == "1"


def require_installer_phase(phase: str, *, dry_run: bool = False, allow_mutation: bool | None = None) -> None:
    if dry_run or phase not in INSTALLER_PHASES:
        return
    if not installer_mutation_allowed(allow_mutation):
        raise BootstrapError("UNSAFE_PATH", "installer-only bootstrap phase")


def validate_transaction_id(transaction_id: str) -> str:
    if not transaction_id or has_control_chars(transaction_id) or contains_glob(transaction_id):
        raise BootstrapError("UNSAFE_PATH", "transaction id is not trusted")
    if "/" in transaction_id or "\\" in transaction_id or ".." in transaction_id:
        raise BootstrapError("UNSAFE_PATH", "transaction id is not trusted")
    if not TX_ID_RE.fullmatch(transaction_id):
        raise BootstrapError("UNSAFE_PATH", "transaction id is not trusted")
    return transaction_id


def _home_resolved(home: Path) -> Path:
    return home.expanduser().resolve()


def assert_not_protected(path: Path, *, home: Path, grok_home: Path | None = None, target: Path | None = None) -> None:
    resolved = path.expanduser()
    if resolved.exists() or resolved.is_symlink():
        resolved = resolved.resolve()
    home_r = _home_resolved(home)
    if resolved == Path("/") or str(resolved) == "/":
        raise BootstrapError("UNSAFE_PATH", "refusing protected path")
    if resolved == home_r:
        raise BootstrapError("UNSAFE_PATH", "refusing to touch home")
    if grok_home is not None:
        grok_r = grok_home.expanduser().resolve()
        if resolved == grok_r or is_inside(resolved, grok_r):
            raise BootstrapError("UNSAFE_PATH", "refusing to touch ~/.grok")
    if target is not None:
        target_r = target.expanduser()
        if target_r.exists() or target_r.is_symlink():
            target_r = target_r.resolve()
        if resolved == target_r:
            raise BootstrapError("UNSAFE_PATH", "refusing to treat the target bank as staging")


def write_transaction_marker(
    directory: Path,
    *,
    kind: str,
    transaction_id: str,
    home: Path,
    target: Path,
) -> None:
    payload = {
        "kind": kind,
        "transaction_id": validate_transaction_id(transaction_id),
        "target": tilde_display(target, home),
    }
    path = directory / TRANSACTION_MARKER
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)


def read_transaction_marker(directory: Path) -> dict[str, Any]:
    path = directory / TRANSACTION_MARKER
    if path.is_symlink() or not path.is_file():
        raise BootstrapError("UNSAFE_PATH", "missing transaction marker")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BootstrapError("UNSAFE_PATH", "transaction marker is not valid JSON") from exc
    if not isinstance(data, dict):
        raise BootstrapError("UNSAFE_PATH", "transaction marker is not an object")
    tx = str(data.get("transaction_id") or "")
    validate_transaction_id(tx)
    kind = str(data.get("kind") or "")
    if kind not in {MARKER_KIND_STAGE, MARKER_KIND_BANK}:
        raise BootstrapError("UNSAFE_PATH", "transaction marker kind mismatch")
    return data


def assert_staging_namespace(
    staging: Path,
    home: Path,
    *,
    transaction_id: str | None = None,
    require_marker: bool | None = None,
) -> Path:
    if has_control_chars(str(staging)) or contains_glob(str(staging)):
        raise BootstrapError("UNSAFE_PATH", "staging path is not trusted")
    if staging.is_symlink():
        raise BootstrapError("UNSAFE_PATH", "staging is a symlink")
    home_r = _home_resolved(home)
    if staging.parent.resolve() != home_r:
        raise BootstrapError("UNSAFE_PATH", "staging parent must be home")
    match = STAGE_NAME_RE.fullmatch(staging.name)
    if not match:
        raise BootstrapError("UNSAFE_PATH", "staging name is not in the staging namespace")
    tx = validate_transaction_id(match.group(1))
    if transaction_id and validate_transaction_id(transaction_id) != tx:
        raise BootstrapError("UNSAFE_PATH", "staging transaction id mismatch")
    assert_not_protected(staging, home=home)
    expected = home_r / staging.name
    if not staging.exists():
        return staging
    if not staging.is_dir() or staging.is_symlink():
        raise BootstrapError("UNSAFE_PATH", "staging is not a regular directory")
    if staging.resolve() != expected:
        raise BootstrapError("UNSAFE_PATH", "staging escaped namespace")
    if is_inside_git_repo(staging) and not is_inside_git_repo(home_r):
        raise BootstrapError("UNSAFE_PATH", "staging is inside a git repository")
    if require_marker is False:
        return staging
    marker = read_transaction_marker(staging)
    if marker.get("transaction_id") != tx:
        raise BootstrapError("UNSAFE_PATH", "transaction marker mismatch")
    return staging


def assert_recovery_namespace(recovery: Path, home: Path, *, must_not_exist: bool = True) -> Path:
    if has_control_chars(str(recovery)) or contains_glob(str(recovery)):
        raise BootstrapError("UNSAFE_PATH", "recovery path is not trusted")
    if recovery.is_symlink():
        raise BootstrapError("UNSAFE_PATH", "recovery is a symlink")
    home_r = _home_resolved(home)
    if recovery.parent.resolve() != home_r:
        raise BootstrapError("UNSAFE_PATH", "recovery parent must be home")
    match = RECOVERY_NAME_RE.fullmatch(recovery.name)
    if not match:
        raise BootstrapError("UNSAFE_PATH", "recovery name is not in the recovery namespace")
    validate_transaction_id(match.group(1))
    assert_not_protected(recovery, home=home)
    if must_not_exist and (recovery.exists() or recovery.is_symlink()):
        raise BootstrapError("UNSAFE_PATH", "recovery path already exists")
    return recovery


def nearest_existing_dir(path: Path) -> Path:
    current = path.expanduser()
    for _ in range(64):
        if current.exists():
            if current.is_symlink():
                raise BootstrapError("UNSAFE_PATH", "disk parent is a symlink")
            if current.is_dir():
                return current.resolve()
            current = current.parent
            continue
        if current.parent == current:
            raise BootstrapError("UNSAFE_PATH", "no existing disk parent")
        current = current.parent
    raise BootstrapError("UNSAFE_PATH", "no existing disk parent")


def load_journal_di_state(journal: Path, *, home: Path) -> dict[str, Any]:
    if journal.is_symlink() or not journal.is_file():
        return {
            "action": "skip",
            "created": False,
            "staging": "",
            "target_path": "",
            "target_display": "~/DesignIntelligence",
            "recovery": "",
            "snapshot": "",
            "transaction_id": "",
        }
    try:
        data = json.loads(journal.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "action": "skip",
            "created": False,
            "staging": "",
            "target_path": "",
            "target_display": "~/DesignIntelligence",
            "recovery": "",
            "snapshot": "",
            "transaction_id": "",
        }
    if not isinstance(data, dict):
        raise BootstrapError("UNSAFE_PATH", "transaction journal is not an object")
    di = data.get("design_intelligence") if isinstance(data.get("design_intelligence"), dict) else {}
    created_block = data.get("created_this_run") if isinstance(data.get("created_this_run"), dict) else {}
    created = bool(created_block.get("design_intelligence_bank") or di.get("created_this_run"))
    action = str(di.get("action") or "skip")
    if action not in {"skip", "create", "reuse"}:
        action = "skip"
    snapshot = str(di.get("snapshot") or "")
    if snapshot and (has_control_chars(snapshot) or contains_glob(snapshot)):
        snapshot = ""
    tx = str(di.get("transaction_id") or "")
    if tx:
        try:
            tx = validate_transaction_id(tx)
        except BootstrapError:
            tx = ""
    staging = ""
    raw_staging = di.get("staging")
    if raw_staging:
        try:
            staging_path = assert_staging_namespace(Path(str(raw_staging)), home, transaction_id=tx or None)
            staging = str(staging_path)
        except BootstrapError:
            staging = ""
    recovery = ""
    raw_recovery = di.get("recovery")
    if raw_recovery:
        try:
            recovery_path = assert_recovery_namespace(Path(str(raw_recovery)), home, must_not_exist=False)
            recovery = str(recovery_path)
        except BootstrapError:
            recovery = ""
    display = str(di.get("target") or "~/DesignIntelligence")
    if has_control_chars(display) or contains_glob(display) or display.startswith("/"):
        display = "~/DesignIntelligence"
    target_path = ""
    raw_target = di.get("target_path") or ""
    if raw_target:
        candidate = Path(str(raw_target)).expanduser()
        try:
            if has_control_chars(str(raw_target)) or contains_glob(str(raw_target)):
                raise BootstrapError("UNSAFE_PATH", "target path is not trusted")
            assert_not_protected(candidate, home=home)
            if candidate.is_symlink():
                raise BootstrapError("UNSAFE_PATH", "target bank is a symlink")
            target_path = str(candidate)
        except BootstrapError:
            target_path = ""
    if not target_path and display.startswith("~/"):
        target_path = str(expand_tilde(display, home))
    return {
        "action": action,
        "created": created,
        "staging": staging,
        "target_path": target_path,
        "target_display": display,
        "recovery": recovery,
        "snapshot": snapshot,
        "transaction_id": tx,
    }


def is_inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def is_inside_git_repo(path: Path) -> bool:
    current = path.expanduser()
    try:
        current = current.resolve()
    except OSError:
        pass
    for parent in (current, *current.parents):
        if (parent / ".git").exists():
            return True
    return False


def _has_untrusted_symlink(path: Path) -> bool:
    current = path.expanduser()
    for _ in range(64):
        try:
            if current.is_symlink():
                return True
        except OSError:
            return True
        if current.parent == current:
            return False
        current = current.parent
    return True


def _paths_overlap(left: Path, right: Path) -> bool:
    try:
        left_r = left.expanduser().resolve()
        right_r = right.expanduser().resolve()
    except OSError:
        left_r = left.expanduser()
        right_r = right.expanduser()
    if left_r == right_r:
        return True
    try:
        left_r.relative_to(right_r)
        return True
    except ValueError:
        pass
    try:
        right_r.relative_to(left_r)
        return True
    except ValueError:
        return False


def validate_bank_target(
    target: Path,
    *,
    home: Path,
    grok_home: Path,
    archive_dir: Path | str | None = None,
) -> Path:
    raw = str(target)
    if not raw or raw in {".", ".."} or has_control_chars(raw) or contains_glob(raw):
        raise BootstrapError("UNSAFE_PATH", "bank target is not trusted")
    expanded = Path(raw).expanduser()
    if expanded == Path("/") or str(expanded) == "/":
        raise BootstrapError("UNSAFE_PATH", "refusing protected path")
    if _has_untrusted_symlink(expanded):
        raise BootstrapError("UNSAFE_PATH", "target or parent is a symlink")
    try:
        resolved = expanded.resolve()
    except OSError as exc:
        raise BootstrapError("UNSAFE_PATH", f"cannot resolve bank target: {exc}") from exc
    if resolved == Path("/") or str(resolved) == "/":
        raise BootstrapError("UNSAFE_PATH", "refusing protected path")
    home_r = _home_resolved(home)
    if resolved == home_r:
        raise BootstrapError("UNSAFE_PATH", "refusing to use home as the bank")
    grok_candidates = [grok_home.expanduser()]
    implicit = home.expanduser() / ".grok"
    if implicit not in grok_candidates:
        grok_candidates.append(implicit)
    for grok in grok_candidates:
        try:
            grok_r = grok.resolve()
        except OSError:
            grok_r = grok
        if resolved == grok_r or is_inside(resolved, grok_r):
            raise BootstrapError("UNSAFE_PATH", "refusing to place the bank inside ~/.grok")
    if is_inside_git_repo(resolved) or is_inside_git_repo(expanded):
        raise BootstrapError("UNSAFE_PATH", "refusing to place the bank inside a git repository")
    if archive_dir is not None and str(archive_dir).strip():
        archive = Path(str(archive_dir))
        if _paths_overlap(resolved, archive) or _paths_overlap(expanded, archive):
            raise BootstrapError("UNSAFE_PATH", "bank target overlaps the archive directory")
    return resolved


def default_bank_target(home: Path | None = None, env: dict[str, str] | None = None) -> Path:
    environ = env if env is not None else os.environ
    explicit = (environ.get("GROK_DESIGN_INTELLIGENCE_BANK") or "").strip()
    if explicit:
        if has_control_chars(explicit) or contains_glob(explicit):
            raise BootstrapError("UNSAFE_PATH", "bank target contains control or glob characters")
        return Path(explicit).expanduser()
    root = home if home is not None else Path.home()
    return root / "DesignIntelligence"


def resolve_archive_dir(
    cli_path: str | None,
    env: dict[str, str] | None = None,
) -> str | None:
    """CLI path wins. Environment is used only when the flag requested a bank."""
    if cli_path is not None and str(cli_path).strip():
        return str(cli_path).strip()
    environ = env if env is not None else os.environ
    alt = (environ.get("GROK_DESIGN_INTELLIGENCE_ARCHIVE_DIR") or "").strip()
    return alt or None


def validate_archive_dir(
    raw: str,
    *,
    grok_home: Path,
    bank_target: Path,
    home: Path,
) -> Path:
    if not raw or has_control_chars(raw):
        raise BootstrapError("UNSAFE_PATH", "archive directory has control characters")
    if contains_glob(raw):
        raise BootstrapError("UNRESOLVED_GLOB", "archive directory must not contain glob characters")
    path = Path(raw).expanduser()
    if path.is_symlink():
        raise BootstrapError("UNSAFE_PATH", "archive directory is a symlink")
    if not path.exists():
        raise BootstrapError("ARCHIVE_DIR_MISSING", "archive directory does not exist")
    if not path.is_dir():
        raise BootstrapError("UNSAFE_PATH", "archive path is not a directory")
    if not os.access(path, os.R_OK):
        raise BootstrapError("UNSAFE_PATH", "archive directory is not readable")
    resolved = path.resolve()
    if is_inside(resolved, grok_home):
        raise BootstrapError("UNSAFE_PATH", "archive directory is inside ~/.grok")
    if is_inside(resolved, bank_target):
        raise BootstrapError("UNSAFE_PATH", "archive directory is inside the bank target")
    if is_inside(resolved, home / "DesignIntelligence"):
        raise BootstrapError("UNSAFE_PATH", "archive directory is inside ~/DesignIntelligence")
    return resolved


def discover_archives(directory: Path) -> dict[str, Path]:
    if directory.is_symlink() or not directory.is_dir():
        raise BootstrapError("UNSAFE_PATH", "archive directory is not a regular directory")
    buckets: dict[str, list[Path]] = {family: [] for family in FAMILY_PATTERNS}
    try:
        entries = list(directory.iterdir())
    except OSError as exc:
        raise BootstrapError("UNSAFE_PATH", f"cannot read archive directory: {exc}") from exc
    for entry in entries:
        name = entry.name
        if has_control_chars(name):
            raise BootstrapError("UNSAFE_PATH", "archive filename has control characters")
        matched = [family for family, pattern in FAMILY_PATTERNS.items() if pattern.fullmatch(name)]
        if not matched:
            continue
        if len(matched) != 1:
            raise BootstrapError("UNSUPPORTED_ARCHIVE_FAMILY", name)
        if entry.is_symlink():
            raise BootstrapError("UNSAFE_PATH", f"archive is a symlink: {name}")
        if not entry.is_file():
            raise BootstrapError("UNSAFE_PATH", f"archive is not a regular file: {name}")
        buckets[matched[0]].append(entry)

    found: dict[str, Path] = {}
    missing: list[str] = []
    duplicates: list[str] = []
    for family, items in buckets.items():
        if not items:
            missing.append(family)
        elif len(items) > 1:
            duplicates.append(family)
        else:
            found[family] = items[0]
    if missing:
        raise BootstrapError("ARCHIVE_MISSING", ",".join(missing))
    if duplicates:
        raise BootstrapError("DUPLICATE_ARCHIVE_FAMILY", ",".join(duplicates))

    logicals: dict[str, str] = {}
    for family, path in found.items():
        name = archive_mod.logical_name(path)
        if name in logicals:
            raise BootstrapError("DUPLICATE_LOGICAL_NAME", name)
        logicals[name] = family
    return found


def _zip_sizes(path: Path) -> tuple[int, int]:
    compressed = 0
    uncompressed = 0
    try:
        with zipfile.ZipFile(path) as handle:
            for info in handle.infolist():
                if info.is_dir():
                    continue
                compressed += int(info.compress_size)
                uncompressed += int(info.file_size)
    except zipfile.BadZipFile as exc:
        raise BootstrapError("CORRUPT_ZIP", path.name) from exc
    return compressed, uncompressed


def inspect_discovered(
    found: dict[str, Path],
    policy: dict[str, Any],
    taxonomy: dict[str, Any],
) -> list[DiscoveredArchive]:
    rows: list[DiscoveredArchive] = []
    for family in IMPORT_ORDER:
        path = found[family]
        try:
            inspection = archive_mod.inspect_archive(path, policy, taxonomy)
        except archive_mod.ArchiveError as exc:
            raise BootstrapError("CORRUPT_ZIP", str(exc)) from exc
        compressed, uncompressed = _zip_sizes(path)
        issues = [f"{item.code}:{item.path}" if item.path else item.code for item in inspection.issues]
        if any(item.code == "absolute" for item in inspection.issues):
            raise BootstrapError("ABSOLUTE_MEMBER_PATH", path.name)
        if any(item.code == "traversal" for item in inspection.issues):
            raise BootstrapError("PARENT_TRAVERSAL", path.name)
        if any(item.code == "symlink" for item in inspection.issues):
            raise BootstrapError("SYMLINK_MEMBER", path.name)
        if any(item.code == "encrypted" for item in inspection.issues):
            raise BootstrapError("ENCRYPTED_MEMBER", path.name)
        if inspection.family is None:
            raise BootstrapError("UNSUPPORTED_ARCHIVE_FAMILY", path.name)
        if inspection.family != family:
            raise BootstrapError("UNSUPPORTED_ARCHIVE_FAMILY", f"{path.name}:{inspection.family}")
        if inspection.blocked:
            raise BootstrapError("UNSAFE_PATH", ",".join(issues) or path.name)
        rows.append(
            DiscoveredArchive(
                family=family,
                path=path,
                logical_name=inspection.logical_name,
                sha256=inspection.sha256,
                compressed_bytes=compressed,
                uncompressed_bytes=uncompressed,
                members=inspection.members,
                blocked=False,
                issues=issues,
            )
        )
    names = [row.logical_name for row in rows]
    if len(names) != len(set(names)):
        raise BootstrapError("DUPLICATE_LOGICAL_NAME", ",".join(names))
    return rows


def snapshot_record(known: dict[str, Any], hashes: dict[str, str]) -> dict[str, Any] | None:
    incoming = {str(name): str(digest) for name, digest in hashes.items()}
    for snap in known.get("snapshots") or []:
        archives = {str(name): str(digest) for name, digest in (snap.get("archives") or {}).items()}
        if archives and incoming == archives:
            return snap if isinstance(snap, dict) else None
    return None


def require_known_snapshot(rows: list[DiscoveredArchive], known: dict[str, Any]) -> dict[str, Any]:
    hashes = {row.logical_name: row.sha256 for row in rows}
    record = snapshot_record(known, hashes)
    if record is None:
        raise BootstrapError("UNKNOWN_ARCHIVE_SNAPSHOT", "exact known snapshot required")
    return record


def disk_preflight(
    rows: list[DiscoveredArchive],
    *,
    staging_parent: Path,
    target_parent: Path,
) -> dict[str, int]:
    compressed = sum(row.compressed_bytes for row in rows)
    uncompressed = sum(row.uncompressed_bytes for row in rows)
    staging_probe = nearest_existing_dir(staging_parent)
    target_probe = nearest_existing_dir(target_parent)
    if os.stat(staging_probe).st_dev != os.stat(target_probe).st_dev:
        raise BootstrapError("INSUFFICIENT_DISK_SPACE", "staging and target are on different filesystems")
    usage = os.statvfs(str(target_probe))
    available = usage.f_bavail * usage.f_frsize
    base = uncompressed + CATALOG_OVERHEAD_BYTES
    required = int(base + base * SAFETY_MARGIN)
    payload = {
        "compressed_bytes": compressed,
        "estimated_uncompressed_bytes": uncompressed,
        "catalog_overhead_estimate": CATALOG_OVERHEAD_BYTES,
        "available_bytes": available,
        "required_bytes": required,
    }
    if available < required:
        raise BootstrapError("INSUFFICIENT_DISK_SPACE", f"need {required} have {available}")
    return payload


def _doctor_payload(
    bank: Path,
    policy: dict[str, Any],
    known: dict[str, Any],
    *,
    claimed_snapshot: str | None = None,
    expected_sha: dict[str, str] | None = None,
    allowlist_path: Path | None = None,
) -> dict[str, Any]:
    return doctor_mod.doctor(
        bank,
        policy,
        known,
        allowlist_path=allowlist_path,
        expected_sha=expected_sha,
        claimed_snapshot=claimed_snapshot,
    )


def classify_doctor(
    report: dict[str, Any],
    *,
    expected_snapshot: str | None = None,
) -> str:
    if not report:
        return "BANK_MISSING"
    if report.get("status") == "BLOCKED":
        return "BANK_BLOCKED"
    checks = {row.get("name"): row for row in report.get("checks") or []}
    if checks.get("bank_root", {}).get("detail") == "missing" or report.get("status") is None:
        return "BANK_MISSING"
    if report.get("status") == "PASS":
        return "BANK_READY_WITH_LIMITATIONS"
    degraded = [row for row in report.get("checks") or [] if row.get("level") == "DEGRADED"]
    unexpected = [row["name"] for row in degraded if row.get("name") not in ALLOWED_DEGRADED_CHECKS]
    snapshot_ok = True
    if expected_snapshot:
        archive = checks.get("archive_hashes") or {}
        snapshot_ok = archive.get("level") == "PASS" and archive.get("detail") == expected_snapshot
    if unexpected or not snapshot_ok:
        return "BANK_DEGRADED"
    return "BANK_READY_WITH_LIMITATIONS"


def evaluate_existing_bank(
    target: Path,
    *,
    policy: dict[str, Any],
    known: dict[str, Any],
    incoming_snapshot: str | None,
    incoming_hashes: dict[str, str] | None,
    allowlist_path: Path | None = None,
) -> dict[str, Any]:
    if target.is_symlink():
        raise BootstrapError("EXISTING_BANK_CONFLICT", "target bank is a symlink")
    if not target.exists():
        return {"action": "create", "reason": None, "doctor": None, "code": "BANK_MISSING"}
    if not target.is_dir():
        raise BootstrapError("EXISTING_BANK_CONFLICT", "target exists and is not a directory")
    report = _doctor_payload(
        target,
        policy,
        known,
        claimed_snapshot=incoming_snapshot,
        expected_sha=incoming_hashes,
        allowlist_path=allowlist_path,
    )
    code = classify_doctor(report, expected_snapshot=incoming_snapshot)
    if code == "BANK_BLOCKED" or code == "BANK_DEGRADED":
        raise BootstrapError("EXISTING_BANK_CONFLICT", code)
    if incoming_snapshot:
        lock = catalog.read_lock(target) or {}
        lock_hashes = {str(k): str(v) for k, v in (lock.get("input_hashes") or {}).items()}
        if incoming_hashes and lock_hashes != incoming_hashes:
            raise BootstrapError("EXISTING_BANK_CONFLICT", "snapshot differs")
        if report.get("status") == "BLOCKED":
            raise BootstrapError("EXISTING_BANK_CONFLICT", "existing bank blocked")
    return {
        "action": "reuse",
        "reason": None,
        "doctor": report,
        "code": code,
        "generation_id": report.get("generation_id"),
        "counts": report.get("counts") or {},
    }


def prepare_staging(home: Path, transaction_id: str, target: Path) -> Path:
    tx = validate_transaction_id(transaction_id)
    staging = home / f"DesignIntelligence.stage.{tx}"
    assert_staging_namespace(staging, home, transaction_id=tx, require_marker=False)
    if staging.exists() or staging.is_symlink():
        raise BootstrapError("UNSAFE_PATH", "staging path already exists")
    if is_inside_git_repo(home):
        raise BootstrapError("UNSAFE_PATH", "refusing to stage a bank inside a git repository")
    if target.exists() and is_inside(staging, target):
        raise BootstrapError("UNSAFE_PATH", "staging would sit inside the target bank")
    staging.mkdir(mode=0o700)
    if staging.is_symlink() or not staging.is_dir():
        raise BootstrapError("UNSAFE_PATH", "staging is not a regular directory")
    os.chmod(staging, 0o700)
    write_transaction_marker(
        staging,
        kind=MARKER_KIND_STAGE,
        transaction_id=tx,
        home=home,
        target=target,
    )
    return staging


def _security_scan(bank: Path, policy: dict[str, Any], home: Path) -> None:
    items = catalog.load_items(bank, policy)
    secret_ids = [item.get("id") for item in items if text_mod.find_secret_hits(item, policy)]
    if secret_ids:
        raise BootstrapError("SECRET_LEAK", ",".join(str(item) for item in secret_ids[:8]))
    leaked = []
    home_s = str(home.resolve())
    for item in items:
        src = str((item.get("source") or {}).get("path") or "")
        if src.startswith("/"):
            leaked.append(str(item.get("id")))
        blob = json.dumps(item, ensure_ascii=False)
        if home_s in blob or "/home/" in src:
            leaked.append(str(item.get("id")))
    if leaked:
        raise BootstrapError("ABSOLUTE_HOME_PATH_LEAK", ",".join(leaked[:8]))
    dirs = catalog.bank_dirs(bank)
    for path in dirs["normalized"].rglob("*"):
        if not path.is_file():
            continue
        mode = path.stat().st_mode
        if mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH) and path.suffix != ".zip":
            raise BootstrapError("UNEXPECTED_EXECUTABLE", path.name)
        if path.name == "SKILL.md":
            raise BootstrapError("UNEXPECTED_EXECUTABLE", "extracted SKILL.md")


def _assert_expected_counts(items: list[dict[str, Any]], expected: dict[str, Any]) -> dict[str, int]:
    counts = catalog._counts(items)
    wanted = {
        key: int(expected[key])
        for key in (
            "items",
            "systems",
            "structures",
            "recipes",
            "specialists",
            "aliases",
            "stubs",
            "quarantined",
        )
        if key in expected
    }
    for key, value in wanted.items():
        if int(counts.get(key) or 0) != value:
            raise BootstrapError("COUNT_MISMATCH", f"{key}:{counts.get(key)}!={value}")
    return counts


def _assert_content_classes(items: list[dict[str, Any]]) -> None:
    for item in items:
        execution = item.get("execution_class")
        if execution in {"native-candidate", "adapted-candidate"}:
            raise BootstrapError("COMMUNITY_EXECUTION_POSSIBLE", str(item.get("id")))
        if item.get("kind") == "recipe" and execution not in {"quarantined", "reference-only", "stub"}:
            raise BootstrapError("COMMUNITY_EXECUTION_POSSIBLE", str(item.get("id")))


def import_into_staging(
    staging: Path,
    rows: list[DiscoveredArchive],
    policy: dict[str, Any],
    taxonomy: dict[str, Any],
    known: dict[str, Any],
    snapshot: dict[str, Any],
    *,
    allowlist_path: Path | None = None,
    home: Path,
) -> dict[str, Any]:
    catalog.ensure_bank(staging)
    for row in rows:
        payload = catalog.import_archive(staging, row.path, policy, taxonomy)
        if payload.get("blocked"):
            raise BootstrapError("UNSAFE_PATH", ",".join(payload.get("issues") or [row.logical_name]))
    rebuilt = catalog.rebuild(staging, policy, taxonomy)
    items = catalog.load_items(staging, policy)
    lock = catalog.read_lock(staging)
    if not lock:
        raise BootstrapError("CATALOG_LOCK_INVALID", "missing lock")
    lock_errors = policy_mod.check_lock(lock)
    if lock_errors:
        raise BootstrapError("CATALOG_LOCK_INVALID", ",".join(lock_errors))
    for item in items:
        row_errors = policy_mod.check_item(item, policy)
        if row_errors:
            raise BootstrapError("SCHEMA_INVALID", f"{item.get('id')}:{','.join(row_errors)}")
    expected = snapshot.get("expected_counts") or {}
    counts = _assert_expected_counts(items, expected) if expected else catalog._counts(items)
    _assert_content_classes(items)
    _security_scan(staging, policy, home)
    incoming = {row.logical_name: row.sha256 for row in rows}
    report = _doctor_payload(
        staging,
        policy,
        known,
        claimed_snapshot=str(snapshot.get("id") or ""),
        expected_sha=incoming,
        allowlist_path=allowlist_path,
    )
    if report.get("status") == "BLOCKED":
        raise BootstrapError("BANK_BLOCKED", "doctor blocked staged bank")
    code = classify_doctor(report, expected_snapshot=str(snapshot.get("id") or ""))
    if code not in {"BANK_READY_WITH_LIMITATIONS", "BANK_DEGRADED"} and report.get("status") != "DEGRADED":
        raise BootstrapError("BANK_BLOCKED", code)
    if code == "BANK_DEGRADED":
        unexpected = [
            row.get("name")
            for row in report.get("checks") or []
            if row.get("level") == "DEGRADED" and row.get("name") not in ALLOWED_DEGRADED_CHECKS
        ]
        if unexpected:
            raise BootstrapError("BANK_BLOCKED", ",".join(str(item) for item in unexpected))
    for path, dirs, files in os.walk(staging):
        del dirs
        for name in files:
            full = Path(path) / name
            os.chmod(full, 0o600)
    for path, dirs, files in os.walk(staging, topdown=False):
        del files
        os.chmod(path, 0o700)
    os.chmod(staging, 0o700)
    return {
        "generation_id": rebuilt.get("generation_id") or lock.get("generation_id"),
        "counts": counts,
        "doctor": report,
        "lock": {
            "generation_id": lock.get("generation_id"),
            "jsonl_sha256": lock.get("jsonl_sha256"),
            "sqlite_sha256": lock.get("sqlite_sha256"),
        },
    }


def promote_staging(
    staging: Path,
    target: Path,
    *,
    home: Path,
    grok_home: Path,
    archive_dir: Path | str | None = None,
    transaction_id: str | None = None,
) -> Path:
    validate_bank_target(target, home=home, grok_home=grok_home, archive_dir=archive_dir)
    if target.exists() or target.is_symlink():
        raise BootstrapError("EXISTING_BANK_CONFLICT", "refusing to overwrite target")
    stage = assert_staging_namespace(staging, home, transaction_id=transaction_id)
    if stage.is_symlink() or not stage.is_dir():
        raise BootstrapError("UNSAFE_PATH", "staging is not a regular directory")
    target_parent = target.parent
    if not target_parent.exists():
        target_parent.mkdir(parents=True, exist_ok=True)
    if target_parent.is_symlink() or not target_parent.is_dir():
        raise BootstrapError("UNSAFE_PATH", "target parent is not a regular directory")
    if os.stat(stage).st_dev != os.stat(target_parent).st_dev:
        raise BootstrapError("ATOMIC_PROMOTION_FAILURE", "cannot rename across filesystems")
    try:
        os.rename(stage, target)
    except OSError as exc:
        raise BootstrapError("ATOMIC_PROMOTION_FAILURE", str(exc)) from exc
    if target.is_symlink():
        raise BootstrapError("ATOMIC_PROMOTION_FAILURE", "promoted target is a symlink")
    os.chmod(target, 0o700)
    marker = read_transaction_marker(target)
    write_transaction_marker(
        target,
        kind=MARKER_KIND_BANK,
        transaction_id=str(marker.get("transaction_id") or transaction_id or ""),
        home=home,
        target=target,
    )
    return target


def recover_created_bank(
    target: Path,
    recovery: Path,
    *,
    home: Path,
    transaction_id: str | None = None,
    grok_home: Path | None = None,
) -> dict[str, str]:
    if target.is_symlink():
        raise BootstrapError("UNSAFE_PATH", "refusing to touch a symlink bank")
    assert_not_protected(target, home=home, grok_home=grok_home)
    dest = assert_recovery_namespace(recovery, home, must_not_exist=True)
    if not target.exists():
        return {"action": "none"}
    if not target.is_dir():
        raise BootstrapError("UNSAFE_PATH", "target exists and is not a directory")
    marker = read_transaction_marker(target)
    if transaction_id and str(marker.get("transaction_id") or "") != validate_transaction_id(transaction_id):
        raise BootstrapError("UNSAFE_PATH", "recovery transaction marker mismatch")
    if dest.parent.resolve() != _home_resolved(home):
        raise BootstrapError("UNSAFE_PATH", "recovery parent must be home")
    if os.stat(target).st_dev != os.stat(dest.parent).st_dev:
        raise BootstrapError("ATOMIC_PROMOTION_FAILURE", "cannot rename across filesystems")
    os.rename(target, dest)
    return {"action": "moved"}


def remove_staging(staging: Path, *, home: Path, transaction_id: str | None = None) -> None:
    stage = assert_staging_namespace(staging, home, transaction_id=transaction_id)
    if not stage.exists():
        return
    if stage.is_symlink() or not stage.is_dir():
        raise BootstrapError("UNSAFE_PATH", "staging is not a regular directory")
    if stage.resolve().parent != _home_resolved(home):
        raise BootstrapError("UNSAFE_PATH", "staging escaped home")
    if stage.resolve() in {_home_resolved(home), Path("/")}:
        raise BootstrapError("UNSAFE_PATH", "refusing protected path")
    shutil.rmtree(stage)


def verify_search(
    bank: Path,
    policy: dict[str, Any],
    *,
    allowlist_path: Path | None = None,
) -> dict[str, Any]:
    allowlist = rank.load_allowlist(allowlist_path) if allowlist_path else set()
    queries: list[dict[str, Any]] = []
    for query in SEARCH_QUERIES:
        systems = rank.search_bank(bank, kind="system", query=query, policy=policy, allowlist=allowlist)
        structures = rank.search_bank(bank, kind="structure", query=query, policy=policy, allowlist=allowlist)
        if int(systems.get("packages_loaded_during_search") or 0) != 0:
            raise BootstrapError("SEARCH_PACKAGE_LOAD", query)
        if int(structures.get("packages_loaded_during_search") or 0) != 0:
            raise BootstrapError("SEARCH_PACKAGE_LOAD", query)
        system_hits = systems.get("results") or []
        structure_hits = structures.get("results") or []
        if len(system_hits) > 5 or len(structure_hits) > 3:
            raise BootstrapError("SEARCH_BOUNDS", query)
        if any(float(row.get("score") or 0) <= 0 for row in system_hits + structure_hits):
            raise BootstrapError("ZERO_SCORE_HITS", query)
        queries.append(
            {
                "query": query,
                "systems": len(system_hits),
                "structures": len(structure_hits),
                "packages_loaded_during_search": 0,
            }
        )
    negative = rank.search_bank(bank, kind="system", query=NEGATIVE_QUERY, policy=policy, allowlist=allowlist)
    if negative.get("results"):
        raise BootstrapError("NEGATIVE_QUERY", NEGATIVE_QUERY)
    return {
        "queries": queries,
        "negative": {"query": NEGATIVE_QUERY, "results": []},
        "packages_loaded_during_search": 0,
        "specialists_activated": 0,
        "community_execution": 0,
        "stub_execution": 0,
        "zero_score_hits": 0,
    }


def safe_manifest_fragment(
    *,
    action: str,
    target: Path,
    home: Path,
    snapshot_id: str | None,
    generation_id: str | None,
    counts: dict[str, Any] | None,
    content_status: str,
    archives: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    bank_state = {
        "create": "installed",
        "reuse": "installed",
        "skip": "skipped",
    }.get(action, "missing")
    payload: dict[str, Any] = {
        "engine": "installed",
        "bank": bank_state,
        "path": tilde_display(target, home) if action != "skip" else "~/DesignIntelligence",
        "snapshot": snapshot_id,
        "generationId": generation_id,
        "contentStatus": content_status,
    }
    if counts:
        for key in ("items", "systems", "structures", "recipes", "specialists"):
            if key in counts:
                payload[key] = int(counts[key])
    if archives:
        payload["archives"] = [
            {"logical_name": row["logical_name"], "sha256": row["sha256"]} for row in archives
        ]
    return payload


def preflight(
    *,
    archive_dir: Path,
    target: Path,
    home: Path,
    grok_home: Path,
    policy: dict[str, Any],
    taxonomy: dict[str, Any],
    known: dict[str, Any],
    allowlist_path: Path | None = None,
) -> dict[str, Any]:
    validate_bank_target(target, home=home, grok_home=grok_home, archive_dir=archive_dir)
    directory = validate_archive_dir(str(archive_dir), grok_home=grok_home, bank_target=target, home=home)
    validate_bank_target(target, home=home, grok_home=grok_home, archive_dir=directory)
    found = discover_archives(directory)
    rows = inspect_discovered(found, policy, taxonomy)
    snapshot = require_known_snapshot(rows, known)
    disk = disk_preflight(rows, staging_parent=home, target_parent=target.parent)
    existing = evaluate_existing_bank(
        target,
        policy=policy,
        known=known,
        incoming_snapshot=str(snapshot.get("id") or ""),
        incoming_hashes={row.logical_name: row.sha256 for row in rows},
        allowlist_path=allowlist_path,
    )
    return {
        "action": existing["action"],
        "snapshot": snapshot.get("id"),
        "expected_counts": snapshot.get("expected_counts") or {},
        "archives": [
            {
                "family": row.family,
                "logical_name": row.logical_name,
                "sha256": row.sha256,
                "members": row.members,
                "compressed_bytes": row.compressed_bytes,
                "uncompressed_bytes": row.uncompressed_bytes,
            }
            for row in rows
        ],
        "disk": disk,
        "existing": {key: existing[key] for key in existing if key != "doctor"},
        "rows": rows,
        "snapshot_record": snapshot,
    }


def bootstrap(
    *,
    archive_dir: str | Path,
    target: Path | None = None,
    home: Path | None = None,
    grok_home: Path | None = None,
    transaction_id: str | None = None,
    dry_run: bool = False,
    phase: str = "all",
    staging: Path | None = None,
    policy: dict[str, Any] | None = None,
    taxonomy: dict[str, Any] | None = None,
    known: dict[str, Any] | None = None,
    allowlist_path: Path | None = None,
    emit: Callable[[str], None] | None = None,
    allow_mutation: bool | None = None,
) -> dict[str, Any]:
    talk = emit or (lambda _line: None)
    require_installer_phase(phase, dry_run=dry_run, allow_mutation=allow_mutation)
    home_path = (home or Path.home()).expanduser()
    grok_path = (grok_home or (home_path / ".grok")).expanduser()
    target_path = (target or default_bank_target(home_path)).expanduser()
    policy = policy or policy_mod.load_policy()
    taxonomy = taxonomy or policy_mod.load_taxonomy()
    known = known or policy_mod.load_known_sources()
    allow = allowlist_path or (policy_mod.vendor_dir() / "skill-allowlist.txt")
    tx_id = validate_transaction_id(transaction_id) if transaction_id else new_transaction_id()

    if phase == "doctor-status":
        if not target_path.exists():
            return {"code": "BANK_MISSING", "status": "DEGRADED", "bank": tilde_display(target_path, home_path)}
        report = _doctor_payload(target_path, policy, known, allowlist_path=allow)
        code = classify_doctor(report)
        return {
            "code": code,
            "status": report.get("status"),
            "generation_id": report.get("generation_id"),
            "counts": report.get("counts") or {},
            "bank": tilde_display(target_path, home_path),
            "checks": report.get("checks") or [],
        }

    if phase == "recover-created":
        if staging is None:
            raise BootstrapError("UNSAFE_PATH", "recovery path required")
        moved = recover_created_bank(
            target_path,
            staging,
            home=home_path,
            transaction_id=transaction_id,
            grok_home=grok_path,
        )
        return {"status": "ok", "recovery": tilde_display(staging, home_path), **moved}

    if phase == "remove-staging":
        if staging is None:
            raise BootstrapError("UNSAFE_PATH", "staging path required")
        remove_staging(staging, home=home_path, transaction_id=transaction_id)
        return {"status": "ok"}

    prepared = preflight(
        archive_dir=Path(archive_dir),
        target=target_path,
        home=home_path,
        grok_home=grok_path,
        policy=policy,
        taxonomy=taxonomy,
        known=known,
        allowlist_path=allow,
    )
    action = prepared["action"]
    snapshot_id = str(prepared["snapshot"])
    archives_meta = prepared["archives"]

    if dry_run:
        if action == "reuse":
            talk("WOULD_REUSE_EXISTING_DI_BANK")
        else:
            talk("WOULD_VERIFY_ARCHIVES")
            talk("WOULD_CREATE_DI_STAGING")
            talk("WOULD_IMPORT_4_ARCHIVES")
            talk("WOULD_REBUILD_CATALOG")
            talk("WOULD_RUN_DI_DOCTOR")
            talk("WOULD_PROMOTE_DI_BANK")
        return {
            "status": "dry-run",
            "action": action,
            "snapshot": snapshot_id,
            "archives": archives_meta,
            "disk": prepared["disk"],
            "would": [
                "WOULD_VERIFY_ARCHIVES",
                "WOULD_CREATE_DI_STAGING",
                "WOULD_IMPORT_4_ARCHIVES",
                "WOULD_REBUILD_CATALOG",
                "WOULD_RUN_DI_DOCTOR",
                "WOULD_PROMOTE_DI_BANK",
            ]
            if action == "create"
            else ["WOULD_REUSE_EXISTING_DI_BANK"],
        }

    if phase == "preflight":
        return {
            "status": "ok",
            "action": action,
            "snapshot": snapshot_id,
            "expected_counts": prepared["expected_counts"],
            "archives": archives_meta,
            "disk": prepared["disk"],
            "target": tilde_display(target_path, home_path),
        }

    if action == "reuse" or phase == "verify-search":
        if action != "reuse" and phase == "verify-search":
            raise BootstrapError("EXISTING_BANK_CONFLICT", "verify-search requires a reusable bank")
        existing = prepared["existing"]
        search = verify_search(target_path, policy, allowlist_path=allow)
        return {
            "status": "ok",
            "action": "reuse",
            "install_result": "SUCCESS_WITH_EXPECTED_LIMITATIONS",
            "bank_integrity": "PASS",
            "bank_content_readiness": "DEGRADED",
            "snapshot": snapshot_id,
            "generation_id": existing.get("generation_id"),
            "counts": existing.get("counts") or {},
            "search": search,
            "manifest": safe_manifest_fragment(
                action="reuse",
                target=target_path,
                home=home_path,
                snapshot_id=snapshot_id,
                generation_id=existing.get("generation_id"),
                counts=existing.get("counts") or {},
                content_status="degraded-with-expected-limitations",
                archives=archives_meta,
            ),
        }

    if phase == "existing":
        return {"status": "ok", "action": action, "snapshot": snapshot_id}

    if phase == "promote":
        if staging is None:
            raise BootstrapError("UNSAFE_PATH", "staging path required")
        stage_path = assert_staging_namespace(staging, home_path, transaction_id=transaction_id)
    else:
        stage_path = staging or prepare_staging(home_path, tx_id, target_path)
        if staging is not None:
            stage_path = assert_staging_namespace(staging, home_path, transaction_id=transaction_id)
    imported: dict[str, Any] = {}
    search: dict[str, Any] = {}
    if phase in {"all", "stage"}:
        try:
            imported = import_into_staging(
                stage_path,
                prepared["rows"],
                policy,
                taxonomy,
                known,
                prepared["snapshot_record"],
                allowlist_path=allow,
                home=home_path,
            )
            search = verify_search(stage_path, policy, allowlist_path=allow)
        except Exception:
            if staging is None:
                remove_staging(stage_path, home=home_path, transaction_id=tx_id)
            raise
        if phase == "stage":
            return {
                "status": "ok",
                "action": "create",
                "staging": tilde_display(stage_path, home_path),
                "staging_path": str(stage_path),
                "snapshot": snapshot_id,
                "generation_id": imported.get("generation_id"),
                "counts": imported.get("counts") or {},
                "search": search,
                "transaction_id": tx_id,
                "manifest": safe_manifest_fragment(
                    action="create",
                    target=target_path,
                    home=home_path,
                    snapshot_id=snapshot_id,
                    generation_id=imported.get("generation_id"),
                    counts=imported.get("counts") or {},
                    content_status="degraded-with-expected-limitations",
                    archives=archives_meta,
                ),
            }

    if phase in {"all", "promote"}:
        search = verify_search(stage_path, policy, allowlist_path=allow)
        promote_staging(
            stage_path,
            target_path,
            home=home_path,
            grok_home=grok_path,
            archive_dir=Path(archive_dir) if archive_dir else None,
            transaction_id=transaction_id or tx_id,
        )

    counts = imported.get("counts") if imported else (catalog._counts(catalog.load_items(target_path, policy)))
    generation_id = imported.get("generation_id") if imported else (catalog.read_lock(target_path) or {}).get("generation_id")
    return {
        "status": "ok",
        "action": "create",
        "install_result": "SUCCESS_WITH_EXPECTED_LIMITATIONS",
        "bank_integrity": "PASS",
        "bank_content_readiness": "DEGRADED",
        "snapshot": snapshot_id,
        "generation_id": generation_id,
        "counts": counts,
        "search": search,
        "staging": None,
        "transaction_id": tx_id,
        "target": tilde_display(target_path, home_path),
        "manifest": safe_manifest_fragment(
            action="create",
            target=target_path,
            home=home_path,
            snapshot_id=snapshot_id,
            generation_id=generation_id,
            counts=counts,
            content_status="degraded-with-expected-limitations",
            archives=archives_meta,
        ),
    }
