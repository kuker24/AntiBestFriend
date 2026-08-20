#!/usr/bin/env python3
"""Design Intelligence catalog CLI. Not a router and not a skill runner."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SOURCE_ROOT = SCRIPT_DIR.parent
LIB_ROOT = SOURCE_ROOT / "lib"
if not (LIB_ROOT / "design_intelligence").is_dir():
    # Installed layout: impeccable/scripts/design-intelligence.py and
    # impeccable/scripts/design_intelligence/*.py.
    LIB_ROOT = SCRIPT_DIR
sys.path.insert(0, str(LIB_ROOT))

from design_intelligence import archive as archive_mod  # noqa: E402
from design_intelligence import bootstrap as bootstrap_mod  # noqa: E402
from design_intelligence import catalog  # noqa: E402
from design_intelligence import doctor as doctor_mod  # noqa: E402
from design_intelligence import integration  # noqa: E402
from design_intelligence import policy as policy_mod  # noqa: E402
from design_intelligence import rank  # noqa: E402
from design_intelligence import report  # noqa: E402
from design_intelligence import selection  # noqa: E402


def allowlist_path() -> Path:
    source = SOURCE_ROOT / "vendor" / "skill-allowlist.txt"
    if source.is_file():
        return source
    return policy_mod.vendor_dir() / "skill-allowlist.txt"


def emit(payload: object) -> int:
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    policy = policy_mod.load_policy()
    taxonomy = policy_mod.load_taxonomy()
    known = policy_mod.load_known_sources()
    inspection = archive_mod.inspect_archive(Path(args.archive), policy, taxonomy)
    snapshot = policy_mod.snapshot_for_hashes(known, {inspection.logical_name: inspection.sha256})
    payload = report.inspect_payload(inspection, snapshot)
    emit(payload)
    return 2 if inspection.blocked else 0


def cmd_import(args: argparse.Namespace) -> int:
    policy = policy_mod.load_policy()
    taxonomy = policy_mod.load_taxonomy()
    bank = catalog.resolve_bank(args.bank)
    archives = []
    blocked = False
    for raw in args.archive:
        payload = catalog.import_archive(bank, Path(raw), policy, taxonomy)
        archives.append(payload)
        blocked = blocked or bool(payload.get("blocked"))
    rebuilt = catalog.rebuild(bank, policy, taxonomy)
    status = "blocked" if blocked else "ok"
    emit(
        report.import_payload(
            status=status,
            generation_id=rebuilt.get("generation_id"),
            archives=archives,
            counts=rebuilt.get("counts") or {},
            warnings=rebuilt.get("warnings") or [],
        )
    )
    return 2 if blocked else 0


def cmd_rebuild(args: argparse.Namespace) -> int:
    policy = policy_mod.load_policy()
    taxonomy = policy_mod.load_taxonomy()
    bank = catalog.resolve_bank(args.bank)
    rebuilt = catalog.rebuild(bank, policy, taxonomy)
    emit(
        {
            "status": rebuilt.get("status"),
            "generation_id": rebuilt.get("generation_id"),
            "reused": rebuilt.get("reused"),
            "counts": rebuilt.get("counts"),
            "warnings": rebuilt.get("warnings"),
        }
    )
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    policy = policy_mod.load_policy()
    bank = catalog.resolve_bank(args.bank)
    allowlist = rank.load_allowlist(Path(args.allowlist) if args.allowlist else allowlist_path())
    payload = rank.search_bank(
        bank,
        kind=args.kind,
        query=args.query,
        policy=policy,
        allowlist=allowlist,
        include_unavailable=args.include_unavailable,
    )
    emit(payload)
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    policy = policy_mod.load_policy()
    known = policy_mod.load_known_sources()
    bank = catalog.resolve_bank(args.bank)
    expected = None
    if args.expected_sha:
        expected = {}
        for item in args.expected_sha:
            if "=" not in item:
                raise SystemExit("--expected-sha needs name=hex")
            name, digest = item.split("=", 1)
            expected[name] = digest
    payload = doctor_mod.doctor(
        bank,
        policy,
        known,
        allowlist_path=allowlist_path(),
        expected_sha=expected,
        claimed_snapshot=args.claimed_snapshot,
    )
    emit(payload)
    if payload.get("status") == "BLOCKED":
        return 2
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    return emit(
        integration.plan_retrieval(
            intent=args.intent,
            scope=args.scope,
            mode=args.mode,
            authority=args.authority,
            reference=args.reference,
            task_kind=args.task_kind,
        )
    )


def cmd_shortlist(args: argparse.Namespace) -> int:
    policy = policy_mod.load_policy()
    bank = catalog.resolve_bank(args.bank)
    payload = selection.shortlist(
        bank,
        query=args.query,
        intent=args.intent,
        mode=args.mode,
        policy=policy,
        allowlist=rank.load_allowlist(allowlist_path()),
        structure_only=args.structure_only,
    )
    emit(payload)
    return 2 if payload.get("status") == "BLOCKED" else 0


def cmd_inspect_system(args: argparse.Namespace) -> int:
    policy = policy_mod.load_policy()
    bank = catalog.resolve_bank(args.bank)
    return emit(selection.inspect_system(bank, args.id, policy))


def cmd_pin_selection(args: argparse.Namespace) -> int:
    policy = policy_mod.load_policy()
    bank = catalog.resolve_bank(args.bank)
    return emit(
        selection.pin_selection(
            Path(args.project),
            bank,
            target=args.target,
            query=args.query,
            intent=args.intent,
            mode=args.mode,
            policy=policy,
            primary_system=args.primary_system,
            secondary_system=args.secondary_system,
            structure=args.structure,
            user_locked=args.user_locked,
        )
    )


def cmd_bootstrap(args: argparse.Namespace) -> int:
    payload = bootstrap_mod.bootstrap(
        archive_dir=args.archive_dir or "",
        target=Path(args.target).expanduser() if args.target else None,
        home=Path(args.home).expanduser() if args.home else None,
        grok_home=Path(args.grok_home).expanduser() if args.grok_home else None,
        transaction_id=args.transaction_id,
        dry_run=args.dry_run,
        phase=args.phase,
        staging=Path(args.staging).expanduser() if args.staging else None,
    )
    return emit(payload)


def cmd_validate_selection(args: argparse.Namespace) -> int:
    policy = policy_mod.load_policy()
    bank = catalog.resolve_bank(args.bank)
    payload = selection.validate_selection(bank, Path(args.path), policy)
    emit(payload)
    return 2 if payload.get("status") == "BLOCKED" else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="design-intelligence")
    sub = parser.add_subparsers(dest="cmd", required=True)

    inspect_p = sub.add_parser("inspect-archive")
    inspect_p.add_argument("archive")
    inspect_p.set_defaults(func=cmd_inspect)

    import_p = sub.add_parser("import")
    import_p.add_argument("--bank")
    import_p.add_argument("--archive", action="append", required=True)
    import_p.set_defaults(func=cmd_import)

    rebuild_p = sub.add_parser("rebuild")
    rebuild_p.add_argument("--bank")
    rebuild_p.set_defaults(func=cmd_rebuild)

    search_p = sub.add_parser("search")
    search_p.add_argument("--bank")
    search_p.add_argument("--kind", required=True, choices=["system", "structure", "recipe", "specialist"])
    search_p.add_argument("--query", required=True)
    search_p.add_argument("--allowlist")
    search_p.add_argument("--include-unavailable", action="store_true")
    search_p.set_defaults(func=cmd_search)

    plan_p = sub.add_parser("plan", help="plan the internal Impeccable retrieval lane")
    plan_p.add_argument("--intent", required=True, choices=sorted(integration.INTENTS))
    plan_p.add_argument("--scope", required=True, choices=sorted(integration.SCOPES))
    plan_p.add_argument("--mode", required=True, choices=sorted(integration.MODES))
    plan_p.add_argument("--authority", required=True, choices=sorted(integration.AUTHORITIES))
    plan_p.add_argument("--reference", default="none", choices=sorted(integration.REFERENCES))
    plan_p.add_argument("--task-kind", default="static", choices=sorted(integration.TASK_KINDS))
    plan_p.set_defaults(func=cmd_plan)

    shortlist_p = sub.add_parser("shortlist", help="retrieve bounded system/structure cards")
    shortlist_p.add_argument("--bank")
    shortlist_p.add_argument("--query", required=True)
    shortlist_p.add_argument("--intent", required=True, choices=sorted(integration.INTENTS))
    shortlist_p.add_argument("--mode", required=True, choices=sorted(integration.MODES))
    shortlist_p.add_argument("--structure-only", action="store_true")
    shortlist_p.set_defaults(func=cmd_shortlist)

    selected_p = sub.add_parser("inspect-system", help="open one selected system package safely")
    selected_p.add_argument("--bank")
    selected_p.add_argument("--id", required=True)
    selected_p.set_defaults(func=cmd_inspect_system)

    pin_p = sub.add_parser("pin-selection", help="persist an explicitly user-locked catalog choice")
    pin_p.add_argument("--bank")
    pin_p.add_argument("--project", default=".")
    pin_p.add_argument("--target", required=True)
    pin_p.add_argument("--query", required=True)
    pin_p.add_argument("--intent", required=True, choices=sorted(integration.INTENTS))
    pin_p.add_argument("--mode", required=True, choices=sorted(integration.MODES))
    pin_p.add_argument("--primary-system")
    pin_p.add_argument("--secondary-system")
    pin_p.add_argument("--structure")
    pin_p.add_argument("--user-locked", action="store_true", required=True)
    pin_p.set_defaults(func=cmd_pin_selection)

    validate_p = sub.add_parser("validate-selection", help="check a persisted pin against the catalog")
    validate_p.add_argument("--bank")
    validate_p.add_argument("--path", default=".impeccable/design-intelligence-selection.json")
    validate_p.set_defaults(func=cmd_validate_selection)

    doctor_p = sub.add_parser("doctor")
    doctor_p.add_argument("--bank")
    doctor_p.add_argument("--expected-sha", action="append", default=[])
    doctor_p.add_argument("--claimed-snapshot")
    doctor_p.set_defaults(func=cmd_doctor)

    boot_p = sub.add_parser(
        "bootstrap",
        help="installer-only transactional local-pack bank import",
    )
    boot_p.add_argument(
        "--phase",
        required=True,
        choices=[
            "all",
            "preflight",
            "stage",
            "promote",
            "verify-search",
            "existing",
            "doctor-status",
            "remove-staging",
            "recover-created",
        ],
    )
    boot_p.add_argument("--archive-dir")
    boot_p.add_argument("--target")
    boot_p.add_argument("--staging")
    boot_p.add_argument("--home")
    boot_p.add_argument("--grok-home")
    boot_p.add_argument("--transaction-id")
    boot_p.add_argument("--dry-run", action="store_true")
    boot_p.set_defaults(func=cmd_bootstrap)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return int(args.func(args))
    except bootstrap_mod.BootstrapError as exc:
        print(json.dumps({"status": "BLOCKED", "error": exc.code, "detail": exc.detail}, indent=2), file=sys.stderr)
        return 2
    except (selection.SelectionError, catalog.CatalogError, ValueError) as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
