"""Sanitize untrusted ZIP prose before it enters the catalog."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_CODE_FENCE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE = re.compile(r"`[^`]*`")
_HTML = re.compile(r"<[^>]+>")
_MD_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_MD_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)

ROOT_KEYS = frozenset(
    {
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
        "summary",
        "search_text",
    }
)
SOURCE_KEYS = frozenset({"archive", "path", "url", "version", "content_sha256"})
LICENSE_KEYS = frozenset({"spdx", "status", "redistribution"})
KNOWN_OBJECT_KEYS = {
    "": ROOT_KEYS,
    "source": SOURCE_KEYS,
    "license": LICENSE_KEYS,
}
# Values at these full paths are identity/format fields, not ZIP prose.
STRUCTURAL_VALUE_PATHS = frozenset(
    {
        "schema_version",
        "id",
        "kind",
        "canonical_id",
        "alias_of",
        "duplicate_of",
        "dedup_reason",
        "trust",
        "evidence_tier",
        "execution_class",
        "style_authority",
        "search_policy",
        "selection_policy",
        "normalization_status",
        "untrusted_text",
        "provider",
        "source.archive",
        "source.path",
        "source.url",
        "source.version",
        "source.content_sha256",
        "license.spdx",
        "license.status",
        "license.redistribution",
    }
)
REJECTED_KEY = "[rejected-key]"
ID_RE = re.compile(r"^[a-z]+:[a-z0-9]+(?:-[a-z0-9]+)*$")
ARCHIVE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,120}\.zip$", re.IGNORECASE)
SOURCE_PATH_RE = re.compile(r"^[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*$")
VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,31}$")
URL_RE = re.compile(r"^https?://[A-Za-z0-9][A-Za-z0-9._~:/\-?#\[\]@!$&'()*+,;=%]{0,511}$")
PROVIDER_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
SPDX_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.+-]{0,63}$")
SAFE_KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")

# Fallback only when policy has no patterns. Split so installer greps miss this file.
_VALUE = r"""\s*[=:]\s*(?:"[^"]*"|'[^']*'|\S+)"""
_FALLBACK_SECRET_RES = (
    re.compile("XAI_API_" "KEY" + _VALUE, re.IGNORECASE),
    re.compile("gho_" r"[A-Za-z0-9]{10,}"),
    re.compile("xai-" r"[A-Za-z0-9]{16,}"),
    re.compile("Bearer " r"[A-Za-z0-9._-]{20,}"),
)


def _collapse_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def strip_controls(text: str) -> str:
    out: list[str] = []
    for ch in text:
        code = ord(ch)
        if ch in "\t\n\r":
            out.append(" ")
        elif code < 32 or 127 <= code < 160:
            continue
        else:
            out.append(ch)
    return "".join(out)


def compile_secret_patterns(policy: dict[str, Any] | None) -> list[re.Pattern[str]]:
    compiled: list[re.Pattern[str]] = []
    if not policy:
        return list(_FALLBACK_SECRET_RES)
    for item in policy.get("secret_pattern_parts") or []:
        if isinstance(item, list) and item:
            compiled.append(re.compile("".join(str(part) for part in item)))
        elif isinstance(item, str) and item:
            compiled.append(re.compile(item))
    for item in policy.get("secret_patterns") or []:
        if isinstance(item, str) and item:
            compiled.append(re.compile(item))
    return compiled or list(_FALLBACK_SECRET_RES)


def redact_secrets(text: str, policy: dict[str, Any] | None = None) -> str:
    out = text
    for compiled in compile_secret_patterns(policy):
        out = compiled.sub("[REDACTED]", out)
    return out


def drop_markup(text: str) -> str:
    out = _MD_HTML_COMMENT.sub(" ", text)
    out = _CODE_FENCE.sub(" ", out)
    out = _INLINE_CODE.sub(" ", out)
    out = _HTML.sub(" ", out)
    out = _MD_IMAGE.sub(" ", out)
    return out


def contains_any(text: str, markers: list[str]) -> bool:
    low = text.lower()
    return any(marker.lower() in low for marker in markers)


def warnings_for(text: str, policy: dict[str, Any]) -> list[str]:
    found: list[str] = []
    if contains_any(text, list(policy.get("install_command_markers") or [])):
        found.append("CATALOGUE_INSTALL_POINTER")
    if contains_any(text, list(policy.get("instruction_tells") or [])):
        found.append("UNTRUSTED_INSTRUCTION_TEXT")
    if contains_any(text, list(policy.get("stub_markers") or [])):
        found.append("CATALOGUE_STUB")
    return found


def _strip_markers(text: str, markers: list[str]) -> str:
    out = text
    for marker in markers:
        out = re.sub(re.escape(marker), " ", out, flags=re.IGNORECASE)
    return out


def sanitize_field(text: str | None, policy: dict[str, Any], *, max_len: int) -> str:
    raw = strip_controls(text or "")
    raw = drop_markup(raw)
    raw = redact_secrets(raw, policy)
    raw = _strip_markers(raw, list(policy.get("install_command_markers") or []))
    raw = _strip_markers(raw, list(policy.get("instruction_tells") or []))
    raw = re.sub(r"https?://\S+", " ", raw)
    raw = _collapse_ws(raw)
    if len(raw) > max_len:
        raw = raw[: max_len - 1].rstrip() + "…"
    return raw


def sanitize_name(text: str | None, policy: dict[str, Any]) -> str:
    caps = policy.get("text") or {}
    return sanitize_field(text, policy, max_len=int(caps.get("name_max") or 160))


def sanitize_description(text: str | None, policy: dict[str, Any]) -> str:
    caps = policy.get("text") or {}
    return sanitize_field(text, policy, max_len=int(caps.get("description_max") or 400))


def sanitize_tag(text: str | None, policy: dict[str, Any]) -> str:
    caps = policy.get("text") or {}
    return sanitize_field(text, policy, max_len=int(caps.get("tag_max") or 48))


def unique_keep(values: list[str], limit: int) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
        if len(out) >= limit:
            break
    return out


def _limit_for(path: str, policy: dict[str, Any]) -> int:
    caps = policy.get("text") or {}
    key = path.rsplit(".", 1)[-1] if path else ""
    if key == "name":
        return int(caps.get("name_max") or 160)
    if key == "description":
        return int(caps.get("description_max") or 400)
    if key == "search_text":
        return int(caps.get("search_text_max") or 1200)
    if key in {"tags", "categories", "intent", "modes", "surfaces", "platforms"}:
        return int(caps.get("tag_max") or 48)
    return int(caps.get("field_max") or 240)


def is_catalog_id(value: str | None) -> bool:
    return bool(value and ID_RE.fullmatch(value))


def is_archive_name(value: str | None) -> bool:
    return bool(value and ARCHIVE_RE.fullmatch(value))


def is_source_path(value: str | None) -> bool:
    if not value or not SOURCE_PATH_RE.fullmatch(value):
        return False
    return not value.startswith("/") and ".." not in Path(value).parts


def is_http_url(value: str | None) -> bool:
    return bool(value and URL_RE.fullmatch(value))


def is_version(value: str | None) -> bool:
    return bool(value and VERSION_RE.fullmatch(value))


def is_provider(value: str | None) -> bool:
    return bool(value and (PROVIDER_TOKEN_RE.fullmatch(value) or is_http_url(value)))


def is_spdx(value: str | None) -> bool:
    return bool(value and SPDX_RE.fullmatch(value))


def sanitize_dict_key(raw: Any, policy: dict[str, Any]) -> str:
    text = strip_controls(str(raw))
    text = redact_secrets(text, policy)
    text = _strip_markers(text, list(policy.get("instruction_tells") or []))
    text = _collapse_ws(text)
    if not text or not SAFE_KEY_RE.fullmatch(text) or find_secret_hits(text, policy):
        return REJECTED_KEY
    return text


def _sanitize_structural_value(path: str, value: Any, policy: dict[str, Any]) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    text = strip_controls(str(value))
    text = redact_secrets(text, policy)
    if path == "source.archive":
        return Path(text).name
    if path == "source.path":
        return text.replace("\\", "/")
    if path == "source.url":
        return text if is_http_url(text) else None
    if path == "source.version":
        return text if is_version(text) else None
    if path == "provider":
        return text if is_provider(text) else None
    if path == "license.spdx":
        return text if is_spdx(text) else None
    return text


def sanitize_tree(value: Any, policy: dict[str, Any], *, path: str = "") -> Any:
    """Recursively sanitize persisted strings and dynamic keys. Skips by full path."""
    if isinstance(value, dict):
        known = KNOWN_OBJECT_KEYS.get(path)
        out: dict[str, Any] = {}
        for child_key, child in value.items():
            key_str = str(child_key)
            next_key = key_str if known is not None and key_str in known else sanitize_dict_key(key_str, policy)
            child_path = f"{path}.{next_key}" if path else next_key
            out[next_key] = sanitize_tree(child, policy, path=child_path)
        return out
    if isinstance(value, list):
        return [sanitize_tree(child, policy, path=path) for child in value]
    if path in STRUCTURAL_VALUE_PATHS:
        return _sanitize_structural_value(path, value, policy)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return sanitize_field(value, policy, max_len=_limit_for(path, policy))
    return sanitize_field(str(value), policy, max_len=_limit_for(path, policy))


def walk_strings(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, str):
        found.append(value)
    elif isinstance(value, dict):
        for child_key, child in value.items():
            found.append(str(child_key))
            found.extend(walk_strings(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(walk_strings(child))
    return found


def find_secret_hits(value: Any, policy: dict[str, Any] | None) -> bool:
    patterns = compile_secret_patterns(policy)
    for blob in walk_strings(value):
        for compiled in patterns:
            if compiled.search(blob):
                return True
    return False
