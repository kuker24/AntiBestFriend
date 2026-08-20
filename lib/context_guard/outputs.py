"""Deterministic tool-output reducers. Proven schemas only. Unknown oversized → STOP."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

PROVEN = "PROVEN"
UNVERIFIED = "UNVERIFIED"

KNOWN_BASH_REQUIRED = {"stdout", "stderr", "interrupted"}
KNOWN_BASH_OPTIONAL = {"isImage"}
KNOWN_READ_KEYS = {"type", "file", "content", "numLines", "startLine", "totalLines"}
SECRET_HINTS = (
    r"ANTHROPIC_AUTH_TOKEN",
    r"AWS_SECRET_ACCESS_KEY",
    r"BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY",
    r"ghp_[A-Za-z0-9]{20,}",
    r"github_pat_[A-Za-z0-9_]{20,}",
    r"xox[baprs]-[A-Za-z0-9-]{10,}",
    r"AKIA[0-9A-Z]{16}",
)
SECRET_TOOL_HINTS = (
    r"(^|/)(\.env|credentials|\.netrc|id_rsa|id_ed25519|auth\.json)$",
    r"printenv",
    r"gh\s+auth\s+token",
)


class OutputDecision:
    def __init__(
        self,
        action: str,
        reason: str,
        *,
        updated: Any = None,
        tokens: int = 0,
        secret: bool = False,
        provenance: str = UNVERIFIED,
        original_tokens: int = 0,
    ) -> None:
        self.action = action  # pass | reduce | stop
        self.reason = reason
        self.updated = updated
        self.tokens = tokens
        self.secret = secret
        self.provenance = provenance
        self.original_tokens = original_tokens or tokens


def _tool_basename(tool_name: str) -> str:
    return (tool_name or "").split("__")[-1]


def estimate_tokens_of(value: Any) -> int:
    """Conservative encoded-size estimate. Never decode base64 image bytes.

    Image pixel payloads count as metadata only. Caps + one-image-per-batch
    already gate pixels; putting base64/4 on the text meter trips TURN_HARD
    after a few sequential screenshots.
    """
    if value is None:
        return 0
    if isinstance(value, (bytes, bytearray)):
        return (len(value) + 3) // 4
    if isinstance(value, str):
        return (len(value.encode("utf-8", errors="replace")) + 3) // 4
    if isinstance(value, dict):
        kind = str(value.get("type") or "")
        if kind == "image" or "media_type" in value or "source" in value:
            return _image_block_tokens(value)
        return sum(estimate_tokens_of(v) for v in value.values())
    if isinstance(value, list):
        return sum(estimate_tokens_of(v) for v in value)
    try:
        encoded = json.dumps(value, ensure_ascii=False, default=str).encode("utf-8", errors="replace")
    except (TypeError, ValueError):
        encoded = str(value).encode("utf-8", errors="replace")
    return (len(encoded) + 3) // 4


def _encoded_field_len(value: Any) -> int:
    if isinstance(value, (bytes, bytearray)):
        return len(value)
    if isinstance(value, str):
        return len(value.encode("utf-8", errors="replace"))
    return 0


def _image_encoded_len(block: dict[str, Any]) -> int:
    """Encoded pixel length. Anthropic: source.data. Claude Code Read: file.base64."""
    source = block.get("source") if isinstance(block.get("source"), dict) else None
    file_rec = block.get("file") if isinstance(block.get("file"), dict) else None
    candidates = []
    if source is not None:
        candidates.append(source.get("data"))
        candidates.append(source.get("base64"))
    if file_rec is not None:
        candidates.append(file_rec.get("base64"))
        candidates.append(file_rec.get("data"))
    candidates.append(block.get("data"))
    candidates.append(block.get("base64"))
    for item in candidates:
        encoded = _encoded_field_len(item)
        if encoded:
            return encoded
    return 0


_PIXEL_KEYS = frozenset({"data", "base64"})


def _redact_image_pixels(value: Any) -> Any:
    """Replace pixel fields with a length placeholder. Never copies the bytes."""
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if key in _PIXEL_KEYS and isinstance(item, (str, bytes, bytearray)):
                out[key] = f"<{_encoded_field_len(item)} bytes>"
            else:
                out[key] = _redact_image_pixels(item)
        return out
    if isinstance(value, list):
        return [_redact_image_pixels(item) for item in value]
    return value


def _image_block_tokens(block: dict[str, Any]) -> int:
    """Text-meter size of an image block: metadata only, never base64/4."""
    try:
        dumped = json.dumps(
            _redact_image_pixels(block),
            ensure_ascii=False,
            default=str,
        ).encode("utf-8", errors="replace")
    except (TypeError, ValueError):
        dumped = str(block).encode("utf-8", errors="replace")
    return (len(dumped) + 3) // 4


def image_encoded_tokens(response: Any) -> int:
    """Encoded pixel token estimate for offload decisions. Not the text meter."""
    total = 0
    if isinstance(response, dict):
        encoded = _image_encoded_len(response)
        if encoded:
            total += (encoded + 3) // 4
        content = response.get("content")
        if isinstance(content, list):
            response = content
        else:
            return total
    if isinstance(response, list):
        for block in response:
            if isinstance(block, dict):
                encoded = _image_encoded_len(block)
                if encoded:
                    total += (encoded + 3) // 4
    return total


def secret_risk(text: str) -> bool:
    if not text:
        return False
    sample = text[:200_000]
    for pat in SECRET_HINTS:
        if re.search(pat, sample):
            return True
    return False


def secret_risk_tool(tool_name: str, tool_input: Any) -> bool:
    blob = f"{tool_name}\n"
    if isinstance(tool_input, dict):
        for key in ("command", "file_path", "path"):
            val = tool_input.get(key)
            if isinstance(val, str):
                blob += val + "\n"
    elif isinstance(tool_input, str):
        blob += tool_input
    for pat in SECRET_TOOL_HINTS:
        if re.search(pat, blob, re.IGNORECASE):
            return True
    return False


def _clip(text: str, budget_tokens: int, pointer: str) -> str:
    if estimate_tokens_of(text) <= budget_tokens:
        return text
    budget_chars = max(256, budget_tokens * 4)
    head = budget_chars * 2 // 3
    tail = budget_chars - head
    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) <= budget_chars:
        return text
    body = encoded[:head].decode("utf-8", errors="replace")
    end = encoded[-tail:].decode("utf-8", errors="replace") if tail else ""
    digest = hashlib.sha256(encoded).hexdigest()[:12]
    return (
        f"{body}\n\n[Context Guard truncated {len(encoded)} bytes → "
        f"~{budget_tokens} tokens; sha256={digest}; {pointer}]\n\n{end}"
    )


def _content_blocks(response: Any) -> list[Any]:
    if isinstance(response, list):
        return response
    if isinstance(response, dict):
        content = response.get("content")
        if isinstance(content, list):
            return content
    return []


def is_image_content_block(block: Any) -> bool:
    if not isinstance(block, dict):
        return False
    kind = str(block.get("type") or "")
    if kind == "image":
        return True
    if kind.startswith("image/"):
        return True
    source = block.get("source")
    if isinstance(source, dict) and (
        source.get("type") in {"base64", "image"} or str(source.get("media_type") or "").startswith("image/")
    ):
        return True
    if str(block.get("media_type") or "").startswith("image/"):
        return True
    return False


def count_image_payloads(response: Any) -> int:
    n = sum(1 for block in _content_blocks(response) if is_image_content_block(block))
    if n:
        return n
    if _is_image_response(response):
        return 1
    return 0


def is_image_heavy(response: Any) -> bool:
    return count_image_payloads(response) > 0


def _is_image_response(response: Any) -> bool:
    if isinstance(response, dict):
        if response.get("isImage") is True:
            return True
        if response.get("type") == "image":
            return True
        file_rec = response.get("file")
        if isinstance(file_rec, dict) and str(file_rec.get("type") or "").startswith("image"):
            return True
        if is_image_content_block(response):
            return True
    if isinstance(response, list) and any(is_image_content_block(b) for b in response):
        return True
    return False


def proven_bash_shape(tool_name: str, response: Any) -> bool:
    if _tool_basename(tool_name) != "Bash":
        return False
    if not isinstance(response, dict):
        return False
    if not KNOWN_BASH_REQUIRED.issubset(response.keys()):
        return False
    extra = set(response.keys()) - KNOWN_BASH_REQUIRED - KNOWN_BASH_OPTIONAL
    # Extra keys are allowed only if they are small metadata; unknown blobs make it unverified.
    for key in extra:
        val = response.get(key)
        if isinstance(val, (dict, list)) and estimate_tokens_of(val) > 64:
            return False
        if isinstance(val, str) and len(val) > 256:
            return False
    return isinstance(response.get("stdout"), str) and isinstance(response.get("stderr"), str)


def proven_read_shape(tool_name: str, response: Any) -> bool:
    if _tool_basename(tool_name) not in {"Read", "read"}:
        return False
    if isinstance(response, str):
        return True
    if not isinstance(response, dict):
        return False
    if isinstance(response.get("content"), str):
        return True
    if response.get("type") in {"text", "file"} and "file" in response:
        return True
    return False


def classify_output(tool_name: str, response: Any) -> str:
    if _is_image_response(response) or count_image_payloads(response):
        return PROVEN
    if proven_bash_shape(tool_name, response) or proven_read_shape(tool_name, response):
        return PROVEN
    return UNVERIFIED


def reduce_output(
    tool_name: str,
    response: Any,
    *,
    bash_budget: int = 20000,
    read_budget: int = 30000,
    hard_unknown: int = 40000,
    pointer: str = "offloaded",
) -> OutputDecision:
    tokens = estimate_tokens_of(response)
    name = _tool_basename(tool_name)

    if _is_image_response(response) or count_image_payloads(response):
        encoded = image_encoded_tokens(response)
        return OutputDecision(
            "pass",
            "IMAGE_PAYLOAD",
            tokens=tokens,
            provenance=PROVEN,
            original_tokens=max(tokens, encoded),
        )

    text_blob = ""
    if isinstance(response, str):
        text_blob = response
    elif isinstance(response, dict):
        for key in ("stdout", "stderr", "content"):
            val = response.get(key)
            if isinstance(val, str):
                text_blob += val
    bash = proven_bash_shape(tool_name, response)
    read = proven_read_shape(tool_name, response)
    provenance = PROVEN if bash or read else UNVERIFIED

    if secret_risk(text_blob):
        if bash or read:
            return OutputDecision(
                "reduce",
                "RAW_CACHE_SKIPPED_SECRET_RISK",
                updated=_redact_known(name, response, pointer),
                tokens=min(tokens, 200),
                secret=True,
                provenance=PROVEN,
                original_tokens=tokens,
            )
        return OutputDecision(
            "stop",
            "RAW_CACHE_SKIPPED_SECRET_RISK",
            tokens=min(tokens, 200),
            secret=True,
            provenance=UNVERIFIED,
            original_tokens=tokens,
        )

    if tokens < 8000:
        return OutputDecision("pass", "SMALL", tokens=tokens, provenance=provenance, original_tokens=tokens)

    if bash:
        if tokens <= bash_budget:
            return OutputDecision("pass", "BASH_OK", tokens=tokens, provenance=PROVEN, original_tokens=tokens)
        updated = dict(response)
        if isinstance(updated.get("stdout"), str):
            updated["stdout"] = _clip(updated["stdout"], bash_budget, pointer)
        if isinstance(updated.get("stderr"), str) and estimate_tokens_of(updated["stderr"]) > 2000:
            updated["stderr"] = _clip(updated["stderr"], 2000, pointer)
        return OutputDecision(
            "reduce",
            "BASH_REDUCED",
            updated=updated,
            tokens=estimate_tokens_of(updated),
            provenance=PROVEN,
            original_tokens=tokens,
        )

    if read:
        if tokens <= read_budget:
            return OutputDecision("pass", "READ_OK", tokens=tokens, provenance=PROVEN, original_tokens=tokens)
        if isinstance(response, str):
            return OutputDecision(
                "reduce",
                "READ_REDUCED",
                updated=_clip(response, read_budget, pointer),
                tokens=read_budget,
                provenance=PROVEN,
                original_tokens=tokens,
            )
        updated = dict(response)
        if isinstance(updated.get("content"), str):
            updated["content"] = _clip(updated["content"], read_budget, pointer)
        return OutputDecision(
            "reduce",
            "READ_REDUCED",
            updated=updated,
            tokens=estimate_tokens_of(updated),
            provenance=PROVEN,
            original_tokens=tokens,
        )

    if tokens >= hard_unknown:
        return OutputDecision(
            "stop",
            "UNKNOWN_OVERSIZED_SCHEMA",
            tokens=tokens,
            provenance=UNVERIFIED,
            original_tokens=tokens,
        )
    return OutputDecision("pass", "UNKNOWN_SMALL", tokens=tokens, provenance=UNVERIFIED, original_tokens=tokens)


def _redact_known(name: str, response: Any, pointer: str) -> Any:
    notice = f"[Context Guard] RAW_CACHE_SKIPPED_SECRET_RISK. Output not persisted. {pointer}"
    if proven_bash_shape("Bash" if name != "Bash" else name, response) or (
        isinstance(response, dict) and "stdout" in response and "stderr" in response
    ):
        updated = dict(response)
        updated["stdout"] = notice
        if isinstance(updated.get("stderr"), str) and updated["stderr"]:
            updated["stderr"] = "[redacted secret-risk]"
        return updated
    if isinstance(response, str):
        return notice
    if isinstance(response, dict) and "content" in response:
        updated = dict(response)
        updated["content"] = notice
        return updated
    return None


def scan_tool_calls(calls: Any) -> dict[str, int]:
    """Independent estimate of what PostToolBatch actually received."""
    tokens = 0
    image_calls = 0
    if not isinstance(calls, list):
        return {"tokens": 0, "image_calls": 0}
    for call in calls:
        if not isinstance(call, dict):
            continue
        resp = call.get("tool_response")
        tokens += estimate_tokens_of(resp)
        n_img = count_image_payloads(resp)
        if n_img:
            image_calls += n_img
    return {"tokens": tokens, "image_calls": image_calls}
