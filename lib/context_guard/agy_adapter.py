"""Antigravity CLI hook adapter for Context Guard.

Translates native Antigravity lifecycle events:
- PreToolUse (toolCall, stepIdx, conversationId) -> image budgeting, ledger reserve, deny oversized/unsupported.
- PostToolUse (error, stepIdx, conversationId) -> cleanup and logging.
- PreInvocation (invocationNum, conversationId) -> turn reset and budget checks.
- Stop (terminationReason, fullyIdle, conversationId) -> safe loop completion.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from .cache import ensure_dir
from .images import ImageDecision, deny_message, derive_image
from .ledger import Ledger, stream_id
from .policy import load_policy, managed_paths


def is_antigravity_event(data: dict[str, Any]) -> bool:
    return any(
        k in data
        for k in (
            "toolCall",
            "conversationId",
            "workspacePaths",
            "invocationNum",
            "terminationReason",
            "initialNumSteps",
            "stepIdx",
        )
    )


def extract_agy_image_paths(tool_name: str, args: dict[str, Any] | None) -> list[str]:
    if not isinstance(args, dict):
        return []
    paths: list[str] = []
    if tool_name in {"view_file", "Read", "read_file"}:
        path = args.get("AbsolutePath") or args.get("file_path") or args.get("path")
        if isinstance(path, str) and path.lower().endswith(
            (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff")
        ):
            paths.append(path)
    elif tool_name in {"generate_image", "image_gen", "image_edit"}:
        img_paths = args.get("ImagePaths") or args.get("image_paths") or []
        if isinstance(img_paths, list):
            for p in img_paths:
                if isinstance(p, str):
                    paths.append(p)
    return paths


def handle_agy_event(
    event: dict[str, Any],
    *,
    managed: Path | None = None,
) -> dict[str, Any]:
    managed_dir = managed or Path(
        os.environ.get("GBFC_MANAGED", Path.home() / ".gemini" / "antigravity-bestfriend")
    )
    paths = managed_paths(managed_dir)
    policy = load_policy(paths["config"])
    cache_root = ensure_dir(paths["cache"])

    conv_id = str(event.get("conversationId") or event.get("session_id") or "global")
    trans_path = str(event.get("transcriptPath") or "")
    ledger = Ledger(cache_root, stream_id(conv_id, trans_path, None))

    # 1. PreToolUse
    if "toolCall" in event:
        tool_call = event.get("toolCall") or {}
        tool_name = str(tool_call.get("name") or "")
        args = tool_call.get("args") or {}

        img_paths = extract_agy_image_paths(tool_name, args)
        if not img_paths:
            return {"decision": "allow"}

        if not ledger.reserve_image():
            denied = ImageDecision("deny", "IMAGE_SECOND_IN_BATCH", img_paths[0])
            ledger.log(f"DENY second image in batch: {img_paths[0]}")
            return {
                "decision": "deny",
                "reason": deny_message(denied),
            }

        dest = ensure_dir(ledger.dir / "derived")
        decision = derive_image(
            img_paths[0],
            dest,
            max_long_edge=int(policy.get("maxLongEdgePx", 1200)),
            max_bytes=int(policy.get("maxImageBytes", 393216)),
            step_down=list(policy.get("stepDownPx") or [1200, 1000, 800]),
            qualities=list(policy.get("jpegQuality") or [85, 75, 65]),
            max_source_pixels=int(policy.get("maxSourcePixels", 40_000_000)),
        )

        if decision.action == "pass":
            ledger.commit_image()
            return {"decision": "allow"}

        ledger.release_image()
        ledger.log(f"IMAGE {decision.reason} derived={decision.derived or '-'}")
        if decision.reason != "IMAGE_SECOND_IN_BATCH":
            ledger.trip(decision.reason)

        return {
            "decision": "deny",
            "reason": deny_message(decision),
        }

    # 2. PreInvocation
    if "invocationNum" in event:
        ledger.reset_turn()
        return {}

    # 3. PostToolUse
    if "stepIdx" in event and "toolCall" not in event:
        return {}

    # 4. Stop
    if "terminationReason" in event:
        return {}

    return {}
