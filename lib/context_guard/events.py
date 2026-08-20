"""Hook event dispatch. Stdout is JSON only. Diagnostics go to the stream log."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, BinaryIO

from .cache import ensure_dir, offload_raw, prune
from .images import ImageDecision, deny_message, derive_image, extract_image_paths
from .ledger import Ledger, stream_id
from .outputs import (
    OutputDecision,
    count_image_payloads,
    reduce_output,
    scan_tool_calls,
    secret_risk_tool,
)
from .policy import load_policy, managed_paths

EMERGENCY_STOP = {
    "continue": False,
    "stopReason": "Context Guard: hook stdin exceeded bound; refusing to parse.",
    "decision": "block",
    "reason": "STDIN_TOO_LARGE",
}

# Post-tool / turn hooks already ran the tool. An internal guard bug must
# not halt the agent (that is what froze a session after a derived JPEG Read).
FAIL_OPEN_EVENTS = frozenset(
    {"PostToolUse", "PostToolBatch", "UserPromptSubmit", "PostCompact", "PreCompact"}
)


def emit(payload: dict[str, Any]) -> int:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()
    return 0


def empty_ok() -> int:
    return emit({})


def resolve_managed() -> Path:
    env = os.environ.get("GBFC_MANAGED")
    if env:
        return Path(env)
    return Path.home() / ".gemini" / "antigravity-bestfriend"


def read_bounded(stream: BinaryIO, limit: int) -> bytes | None:
    """Read at most limit+1 bytes. None means the bound was exceeded."""
    raw = stream.read(int(limit) + 1)
    if raw is None:
        return b""
    if len(raw) > int(limit):
        return None
    return raw


def parse_stdin(raw: bytes, max_bytes: int) -> dict[str, Any] | None:
    if len(raw) > max_bytes:
        return None
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _agent_id(event: dict[str, Any]) -> str | None:
    for key in ("agent_id", "agentId", "subagent_id", "subagentId"):
        val = event.get(key)
        if isinstance(val, str) and val:
            return val
    return None


def _ledger(event: dict[str, Any], cache_root: Path) -> Ledger:
    sid = stream_id(
        str(event.get("session_id") or ""),
        str(event.get("transcript_path") or ""),
        _agent_id(event),
    )
    return Ledger(cache_root, sid)


def _serialize_payload(value: Any) -> bytes:
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    if isinstance(value, str):
        return value.encode("utf-8", errors="replace")
    try:
        return json.dumps(value, ensure_ascii=False, default=str).encode("utf-8", errors="replace")
    except (TypeError, ValueError):
        return str(value).encode("utf-8", errors="replace")


def _pre_tool_use(event: dict[str, Any], policy: dict[str, Any], ledger: Ledger) -> dict[str, Any]:
    tool = str(event.get("tool_name") or "")
    paths = extract_image_paths(tool, event.get("tool_input"))
    if not paths:
        return {}
    if not ledger.reserve_image():
        denied = ImageDecision("deny", "IMAGE_SECOND_IN_BATCH", paths[0])
        ledger.log("DENY second image in batch")
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": deny_message(denied),
            }
        }

    dest = ensure_dir(ledger.dir / "derived")
    decision = derive_image(
        paths[0],
        dest,
        max_long_edge=int(policy["maxLongEdgePx"]),
        max_bytes=int(policy["maxImageBytes"]),
        step_down=list(policy.get("stepDownPx") or []),
        qualities=list(policy.get("jpegQuality") or []),
        max_source_pixels=int(policy.get("maxSourcePixels") or 40_000_000),
    )
    if decision.action == "pass":
        ledger.commit_image()
        return {}

    # Raw oversized / unknown / failed: release so a derived retry can claim.
    ledger.release_image()
    ledger.log(f"IMAGE {decision.reason} derived={decision.derived or '-'}")
    if decision.action == "derive_deny" and decision.derived:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": deny_message(decision),
            }
        }
    if decision.reason != "IMAGE_SECOND_IN_BATCH":
        ledger.trip(decision.reason)
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": deny_message(decision),
        }
    }


def _post_tool_use(
    event: dict[str, Any],
    policy: dict[str, Any],
    ledger: Ledger,
    *,
    managed: Path | None = None,
) -> dict[str, Any]:
    tool = str(event.get("tool_name") or "")
    response = event.get("tool_response")
    pointer = f"stream={ledger.stream} cache={ledger.dir}"
    secretish = secret_risk_tool(tool, event.get("tool_input"))
    result: OutputDecision = reduce_output(
        tool,
        response,
        bash_budget=int(policy["textBudgetBash"]),
        read_budget=int(policy["textBudgetRead"]),
        hard_unknown=int(policy["batchHardTokens"]),
        pointer=pointer,
    )
    if secretish and not result.secret:
        result.secret = True

    # Record what we believe will reach the model (reduced size if we rewrote).
    # PostToolBatch independently estimates actual tool_response and takes the max,
    # so an ignored updatedToolOutput still trips the hard budget.
    ledger.add_tokens(int(result.tokens))

    if result.secret:
        ledger.log("SECRET_RISK skip raw cache")
    elif result.action in {"reduce", "stop"} or int(result.original_tokens or 0) >= 8000:
        dumped = _serialize_payload(response)
        stored = offload_raw(
            ledger.dir,
            tool=tool,
            payload=dumped,
            klass=result.reason,
            secret=False,
            policy=policy,
            managed=managed,
        )
        if stored.get("status") == "CACHE_WRITE_SKIPPED_STREAM_CAP":
            ledger.log("CACHE_WRITE_SKIPPED_STREAM_CAP")
            pointer = "CACHE_WRITE_SKIPPED_STREAM_CAP"
        elif stored.get("pointer"):
            pointer = stored["pointer"]
            ledger.log(f"OFFLOAD {stored['status']} {pointer}")

    if result.action == "stop":
        ledger.trip(result.reason)
        return {
            "continue": False,
            "stopReason": (
                "Context Guard stopped: oversized tool output with an unknown schema. "
                f"{result.reason}. Do not retry the same call."
            ),
            "decision": "block",
            "reason": result.reason,
        }
    if result.action == "reduce" and result.updated is not None:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "updatedToolOutput": result.updated,
                "additionalContext": f"Context Guard reduced {tool} ({result.reason}). {pointer}",
            }
        }
    return {}


def _count_executed_images(calls: list[Any]) -> int:
    count = 0
    for call in calls:
        if not isinstance(call, dict):
            continue
        paths = extract_image_paths(str(call.get("tool_name") or ""), call.get("tool_input"))
        resp = call.get("tool_response")
        n_img = count_image_payloads(resp)
        if paths:
            count += 1
        elif n_img:
            count += n_img
    return count


def _post_tool_batch(
    event: dict[str, Any],
    policy: dict[str, Any],
    ledger: Ledger,
    *,
    managed: Path | None = None,
) -> dict[str, Any]:
    state = ledger.snapshot()
    trip = ledger.consume_trip()
    claims = int(state.get("imageClaimsThisEpoch") or 0)
    ledger_batch = int(state.get("batchTokens") or 0)
    ledger_turn = int(state.get("turnTokens") or 0)
    calls = event.get("tool_calls") if isinstance(event.get("tool_calls"), list) else []

    scanned = scan_tool_calls(calls)
    actual_batch = int(scanned["tokens"])
    image_calls = max(int(scanned["image_calls"]), _count_executed_images(calls))
    effective = max(ledger_batch, actual_batch)
    observed = ledger.add_observed_tokens(effective)
    turn_observed = int(observed.get("turnObservedTokens") or 0)
    effective_turn = max(ledger_turn, turn_observed)

    hard_batch = int(policy["batchHardTokens"])
    hard_turn = int(policy["turnHardTokens"])
    reasons: list[str] = []
    if trip:
        reasons.append(trip)
    if claims > 1 or image_calls > 1:
        reasons.append("MULTI_IMAGE_BATCH")
    if effective >= hard_batch:
        reasons.append("BATCH_HARD_BUDGET")
    if effective_turn >= hard_turn:
        reasons.append("TURN_HARD_BUDGET")

    ledger.advance_epoch()
    prune(
        ledger.dir.parent,
        active_stream=ledger.stream,
        policy=policy,
        managed=managed,
    )

    if reasons:
        reason = ",".join(reasons)
        ledger.log(
            f"CIRCUIT {reason} ledger={ledger_batch} actual={actual_batch} "
            f"effective={effective} observed={turn_observed} turn={ledger_turn} turnEffective={effective_turn}"
        )
        # Fat TURN_HARD still halts. A small batch that only crossed the
        # turn cap (sequential QA drip) warns and relieves the meter.
        soft_batch = int(policy["batchSoftTokens"])
        drip_turn = reasons == ["TURN_HARD_BUDGET"] and effective < soft_batch
        if drip_turn:
            ledger.relieve_turn()
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolBatch",
                    "additionalContext": (
                        "Context Guard circuit breaker: "
                        f"{reason}. New-payload batch≈{effective} "
                        f"(ledger={ledger_batch} actual={actual_batch}) "
                        f"turn≈{effective_turn}. "
                        "This is not a total-context meter. Loop continues. "
                        "Prefer DOM/a11y/console. One image per next batch "
                        "if pixels are still required."
                    ),
                }
            }
        return {
            "continue": False,
            "stopReason": (
                "Context Guard circuit breaker: "
                f"{reason}. New-payload batch≈{effective} (ledger={ledger_batch} actual={actual_batch}) "
                f"turn≈{effective_turn}. "
                "This is not a total-context meter. "
                "Prefer DOM/a11y/console. One image per next batch if pixels are still required."
            ),
            "decision": "block",
            "reason": reason,
        }

    extra = ""
    if effective >= int(policy["batchSoftTokens"]) or effective_turn >= int(policy["turnSoftTokens"]):
        extra = (
            f" Context Guard soft budget: new-payload batch≈{effective} turn≈{effective_turn}."
        )
    if extra:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PostToolBatch",
                "additionalContext": extra.strip(),
            }
        }
    return {}


def _user_prompt(ledger: Ledger) -> dict[str, Any]:
    ledger.reset_turn()
    return {}


def _post_compact(ledger: Ledger) -> dict[str, Any]:
    ledger.reset_pressure()
    return {}


def handle_event(event: dict[str, Any], *, managed: Path | None = None) -> dict[str, Any]:
    managed = Path(managed) if managed else resolve_managed()
    paths = managed_paths(managed)
    policy = load_policy(paths["config"])
    cache_root = ensure_dir(paths["cache"])
    name = str(event.get("hook_event_name") or event.get("hookEventName") or "")
    ledger = _ledger(event, cache_root)
    if name == "PreToolUse":
        return _pre_tool_use(event, policy, ledger)
    if name == "PostToolUse":
        return _post_tool_use(event, policy, ledger, managed=managed)
    if name == "PostToolBatch":
        return _post_tool_batch(event, policy, ledger, managed=managed)
    if name == "UserPromptSubmit":
        return _user_prompt(ledger)
    if name in {"PostCompact", "PreCompact"}:
        return _post_compact(ledger)
    return {}


def payload_for_exception(event: dict[str, Any], exc: BaseException) -> dict[str, Any]:
    """Map an uncaught guard exception to a hook payload.

    PreToolUse stays fail-closed (deny the tool). Post-tool / turn events
    fail open so a RecursionError cannot halt the agent loop.
    """
    name = str(event.get("hook_event_name") or event.get("hookEventName") or "")
    kind = type(exc).__name__
    if name == "PreToolUse":
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    f"Context Guard internal error ({kind}). "
                    "Do not retry the same raw tool input."
                ),
            }
        }
    if name in FAIL_OPEN_EVENTS:
        return {
            "hookSpecificOutput": {
                "hookEventName": name,
                "additionalContext": (
                    f"Context Guard internal error ({kind}); continuing without reduction."
                ),
            }
        }
    return {}


def run_from_stdin(argv: list[str] | None = None) -> int:
    del argv
    managed = resolve_managed()
    policy = load_policy(managed_paths(managed)["config"])
    limit = int(policy["maxStdinBytes"])
    raw = read_bounded(sys.stdin.buffer, limit)
    if raw is None:
        return emit(EMERGENCY_STOP)
    parsed = parse_stdin(raw, limit)
    if parsed is None:
        return emit(EMERGENCY_STOP)
    try:
        payload = handle_event(parsed, managed=managed)
    except Exception as exc:
        payload = payload_for_exception(parsed, exc)
    if not payload:
        return empty_ok()
    return emit(payload)
