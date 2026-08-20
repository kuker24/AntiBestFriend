"""Deterministic extractors. No PyYAML. No invented structure."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from . import archive as archive_mod

ALLOWED_FRONTMATTER = {
    "name",
    "description",
    "triggers",
    "disable-model-invocation",
    "od.mode",
    "od.surface",
    "od.platform",
    "od.category",
    "od.upstream",
    "capabilities_required",
}

_SCALAR = re.compile(r"^([A-Za-z0-9_.-]+):\s*(.*?)\s*$")
_LIST_INLINE = re.compile(r"^\[(.*)\]$")


def normalize_slug(value: str) -> str:
    text = value.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "unnamed"


def make_id(kind: str, slug: str) -> str:
    return f"{kind}:{normalize_slug(slug)}"


def framed_hash(parts: list[tuple[str, bytes]]) -> str:
    digest = hashlib.sha256()
    for path, data in sorted(parts, key=lambda item: item[0]):
        digest.update(path.encode("utf-8"))
        digest.update(b"\x00")
        digest.update(str(len(data)).encode("ascii"))
        digest.update(b"\x00")
        digest.update(data)
        digest.update(b"\x00")
    return digest.hexdigest()


def parse_frontmatter(text: str) -> tuple[dict[str, Any], list[str], str]:
    warnings: list[str] = []
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, warnings, text
    end = next((index for index, line in enumerate(lines[1:], 1) if line.strip() == "---"), None)
    if end is None:
        warnings.append("FRONTMATTER_PARTIAL")
        return {}, warnings, text

    data: dict[str, Any] = {}
    in_od = False
    list_key: str | None = None
    block_key: str | None = None
    block_lines: list[str] = []

    def flush_block() -> None:
        nonlocal block_key, block_lines
        if block_key is not None:
            data[block_key] = "\n".join(block_lines).strip()
        block_key = None
        block_lines = []

    for line in lines[1:end]:
        if block_key is not None:
            if line.startswith("  ") or line.startswith("\t") or line.strip() == "":
                block_lines.append(re.sub(r"^  ", "", line))
                continue
            flush_block()

        if (line.startswith("  - ") or (line.startswith("- ") and list_key)) and list_key:
            item = line.strip()[2:].strip().strip('"').strip("'")
            bucket = data.setdefault(list_key, [])
            if isinstance(bucket, list):
                bucket.append(item)
            continue

        if re.match(r"^od:\s*$", line):
            in_od = True
            list_key = None
            continue

        nested = re.match(r"^  ([A-Za-z0-9_-]+):\s*(.*)$", line)
        if in_od and nested:
            key = f"od.{nested.group(1)}"
            raw = nested.group(2)
            list_key = None
            if key not in ALLOWED_FRONTMATTER:
                if raw in {"", "|", ">"} or raw.startswith("{") or raw.startswith("["):
                    warnings.append("FRONTMATTER_PARTIAL")
                continue
            if raw in {"|", ">"}:
                block_key = key
                block_lines = []
            else:
                data[key] = _parse_scalar(raw, warnings)
            continue

        top = re.match(r"^([A-Za-z0-9_.-]+):\s*(.*)$", line)
        if top and not line.startswith(" ") and not line.startswith("\t"):
            in_od = False
            key, raw = top.group(1), top.group(2)
            if key not in ALLOWED_FRONTMATTER:
                list_key = None
                if raw in {"", "|", ">"} or raw.startswith("{") or raw.startswith("["):
                    warnings.append("FRONTMATTER_PARTIAL")
                continue
            if raw in {"|", ">"}:
                block_key = key
                list_key = None
                block_lines = []
            elif raw == "":
                list_key = key if key in {"triggers", "capabilities_required"} else None
                if list_key:
                    data[list_key] = []
                else:
                    warnings.append("FRONTMATTER_PARTIAL")
            else:
                parsed = _parse_scalar(raw, warnings)
                data[key] = parsed
                list_key = key if isinstance(parsed, list) else None
            continue

        if line.strip() == "" or line.strip().startswith("#"):
            continue
        warnings.append("FRONTMATTER_PARTIAL")
    flush_block()
    body = "\n".join(lines[end + 1 :]).lstrip("\n")
    return data, warnings, body


def _parse_scalar(raw: str, warnings: list[str]) -> Any:
    if raw == "":
        return ""
    if raw in {"true", "True"}:
        return True
    if raw in {"false", "False"}:
        return False
    if raw in {"null", "None", "~"}:
        return None
    inline = _LIST_INLINE.match(raw)
    if inline:
        inner = inline.group(1).strip()
        if not inner:
            return []
        return [part.strip().strip('"').strip("'") for part in inner.split(",")]
    if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
        return raw[1:-1]
    if raw.startswith("{") or raw.startswith("[") and not _LIST_INLINE.match(raw):
        warnings.append("FRONTMATTER_PARTIAL")
        return raw
    return raw


def decode_text(data: bytes) -> str:
    return data.decode("utf-8", "replace")


def load_json_member(archive, name: str, policy: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    try:
        raw = archive_mod.read_member(archive, name, policy)
    except archive_mod.ArchiveError as exc:
        return None, str(exc)
    try:
        value = json.loads(decode_text(raw))
    except json.JSONDecodeError as exc:
        return None, f"invalid_json:{name}:{exc.msg}"
    if not isinstance(value, dict):
        return None, f"invalid_json:{name}:not-object"
    return value, None


def extract_heading_fields(markdown: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    current = None
    buf: list[str] = []

    def flush() -> None:
        if current and buf:
            fields[current] = " ".join(line.strip() for line in buf if line.strip())[:240]

    for line in markdown.splitlines():
        if line.startswith("## "):
            flush()
            current = line[3:].strip().lower()
            buf = []
            continue
        if current:
            buf.append(line)
    flush()
    return fields


def system_summary(manifest: dict[str, Any], design: str) -> tuple[dict[str, str], list[str]]:
    headings = extract_heading_fields(design)
    evidence: list[str] = []
    summary: dict[str, str] = {}
    category = str(manifest.get("category") or "").strip()
    if category:
        summary["category"] = category
        evidence.append("manifest.category")
    desc = str(manifest.get("description") or "").strip()
    if desc:
        summary["catalog_description"] = desc
        evidence.append("manifest.description")
    mapping = {
        "visual philosophy": ("visual theme", "visual theme & atmosphere", "1. visual theme & atmosphere"),
        "color character": ("color", "2. color"),
        "typography character": ("typography", "3. typography"),
        "density": ("spacing & grid", "4. spacing & grid"),
        "layout character": ("layout & composition", "5. layout & composition", "layout"),
        "component character": ("components", "6. components"),
        "motion posture": ("motion & interaction", "7. motion & interaction"),
    }
    for dest, keys in mapping.items():
        for key in keys:
            if key in headings and headings[key]:
                summary[dest.replace(" ", "_")] = headings[key][:240]
                evidence.append(f"DESIGN.md:{key}")
                break
    first = next((line[2:].strip() for line in design.splitlines() if line.startswith("> ")), "")
    if first and "visual_philosophy" not in summary:
        summary["visual_philosophy"] = first[:240]
        evidence.append("DESIGN.md:blockquote")
    return summary, evidence


def structure_from_skill(front: dict[str, Any], body: str) -> tuple[dict[str, Any], list[str], str]:
    card: dict[str, Any] = {}
    evidence: list[str] = []
    status = "partial"
    mode = front.get("od.mode")
    if isinstance(mode, str) and mode:
        card["artifact_kind"] = mode
        evidence.append("frontmatter:od.mode")
    if front.get("od.platform"):
        card["platform"] = front.get("od.platform")
        evidence.append("frontmatter:od.platform")
    if front.get("od.surface"):
        card["surface"] = front.get("od.surface")
        evidence.append("frontmatter:od.surface")

    regions: list[str] = []
    capture = False
    for line in body.splitlines():
        stripped = line.strip()
        low = stripped.lower()
        if low.startswith("## ") and ("region" in low or "lay out" in low or "layout" in low):
            capture = True
            evidence.append(stripped)
            continue
        if capture and stripped.startswith("## "):
            capture = False
        if (capture or "required regions" in low) and stripped.startswith("- "):
            regions.append(re.sub(r"^[-*]\s+\*?\*?", "", stripped).strip()[:120])
        bullet_match = re.match(r"^[-*]\s+\*\*(Left sidebar|Top bar|Main|Footer|Hero|Sidebar)", stripped)
        if bullet_match:
            regions.append(stripped[2:120])
            evidence.append("SKILL.md:region-bullet")
    if regions:
        card["required_data_regions"] = regions[:12]
        card["section_order"] = regions[:12]
        status = "complete" if mode else "partial"
    else:
        status = "manual-required" if not mode else "partial"
    return card, evidence, status


def looks_style_coupled(body: str) -> bool:
    low = body.lower()
    hits = 0
    for marker in (
        "must use #",
        "required font",
        "mandatory radius",
        "pixel-perfect brand",
        "always use inter",
        "always use playfair",
    ):
        if marker in low:
            hits += 1
    return hits >= 1


def catalogue_stub(text: str, policy: dict[str, Any]) -> bool:
    return any(marker.lower() in text.lower() for marker in policy.get("stub_markers") or [])
