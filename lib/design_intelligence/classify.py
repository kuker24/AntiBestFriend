"""Static classification. Host probes live in rank/doctor only."""

from __future__ import annotations

import re
from typing import Any

from . import text as text_mod


def _normalize_declared_spdx(declared: str | None) -> str | None:
    text = (declared or "").strip()
    if not text:
        return None
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.+-]{0,63}", text):
        return text
    return None


def canonical_spdx(value: str | None, policy: dict[str, Any]) -> str | None:
    if not value:
        return None
    aliases = policy.get("license_aliases") or {}
    if value in aliases:
        return str(aliases[value])
    lowered = value.lower()
    for key, canon in aliases.items():
        if str(key).lower() == lowered:
            return str(canon)
    return value


def _signature_hits(license_text: str, spec: Any) -> bool:
    if isinstance(spec, list):
        required = spec
        any_of: list[str] = []
        forbidden: list[str] = []
    elif isinstance(spec, dict):
        required = list(spec.get("required") or [])
        any_of = list(spec.get("any_of") or [])
        forbidden = list(spec.get("forbidden") or [])
    else:
        return False
    if not required or not all(needle in license_text for needle in required):
        return False
    if any_of and not any(needle in license_text for needle in any_of):
        return False
    low = license_text.lower()
    if any(marker.lower() in low for marker in forbidden):
        return False
    return True


def detect_license(
    license_text: str | None,
    declared: str | None,
    policy: dict[str, Any],
    *,
    item_owned: bool,
) -> dict[str, Any]:
    if not item_owned:
        license_text = None
    signatures = policy.get("license_signatures") or {}
    matches: list[str] = []
    if license_text:
        for spdx, spec in signatures.items():
            if _signature_hits(license_text, spec):
                matches.append(str(spdx))
    declared_norm = canonical_spdx(_normalize_declared_spdx(declared), policy)
    if len(matches) > 1:
        return {"spdx": matches[0], "status": "conflicting", "redistribution": "blocked"}
    found = canonical_spdx(matches[0] if matches else None, policy)
    if found and declared_norm and declared_norm != found:
        return {"spdx": found, "status": "conflicting", "redistribution": "blocked"}
    if found:
        return {"spdx": found, "status": "known", "redistribution": "allowed"}
    if declared_norm:
        return {"spdx": declared_norm, "status": "declared-only", "redistribution": "local-only"}
    return {"spdx": None, "status": "unknown", "redistribution": "local-only"}


def is_community_path(path: str, taxonomy: dict[str, Any]) -> bool:
    prefix = ((taxonomy.get("lineage") or {}).get("community_prefix") or "plugins/community/")
    return path.startswith(prefix)


def is_official_system_path(path: str, taxonomy: dict[str, Any]) -> bool:
    prefix = (taxonomy.get("lineage") or {}).get("official_design_systems_prefix") or ""
    return bool(prefix) and path.startswith(prefix)


def is_official_example_path(path: str, taxonomy: dict[str, Any]) -> bool:
    prefix = (taxonomy.get("lineage") or {}).get("official_examples_prefix") or ""
    return bool(prefix) and path.startswith(prefix)


def lineage_slug(path: str, prefix: str) -> str | None:
    if not path.startswith(prefix):
        return None
    rest = path[len(prefix) :].strip("/")
    if not rest:
        return None
    return rest.split("/", 1)[0]


def special_class(name: str, policy: dict[str, Any]) -> dict[str, Any] | None:
    specials = policy.get("specials") or {}
    if name in specials:
        return dict(specials[name])
    prefix = policy.get("figma_prefix") or "figma-"
    if name.startswith(prefix):
        return {"execution_class": "stub"}
    return None


def classify_system(manifest: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    origin = ""
    source = manifest.get("source") if isinstance(manifest.get("source"), dict) else {}
    origin = str(source.get("origin") or "")
    url = origin if origin.startswith("http") else None
    return {
        "trust": "curated",
        "evidence_tier": "E1",
        "style_authority": "inspiration-only",
        "execution_class": "reference-only",
        "search_policy": "metadata-only",
        "selection_policy": "full-on-selection",
        "source_url": url,
        "warnings": [],
    }


def classify_structure(
    *,
    style_coupled: bool,
    community: bool,
    policy: dict[str, Any],
) -> dict[str, Any]:
    del policy
    if community:
        return {
            "trust": "community",
            "evidence_tier": "E0",
            "style_authority": "none",
            "execution_class": "quarantined",
            "search_policy": "never",
            "selection_policy": "never",
            "warnings": [],
        }
    warnings = ["TEMPLATE_STYLE_COUPLED"] if style_coupled else []
    return {
        "trust": "curated",
        "evidence_tier": "E1",
        "style_authority": "none" if style_coupled else "structure-only",
        "execution_class": "reference-only" if style_coupled else "reference-only",
        "search_policy": "metadata-only",
        "selection_policy": "normalized-card-only",
        "warnings": warnings,
    }


def classify_specialist(
    *,
    name: str,
    body: str,
    front: dict[str, Any],
    community: bool,
    policy: dict[str, Any],
) -> dict[str, Any]:
    warnings: list[str] = []
    if community:
        return {
            "trust": "community",
            "evidence_tier": "E0",
            "style_authority": "none",
            "execution_class": "quarantined",
            "search_policy": "never",
            "selection_policy": "never",
            "capabilities_required": [],
            "provider": None,
            "warnings": warnings,
        }

    special = special_class(name, policy) or {}
    execution = special.get("execution_class")
    warnings.extend(special.get("warnings") or [])
    caps = list(special.get("capabilities_required") or [])
    if front.get("disable-model-invocation") is True and "DISABLE_MODEL_INVOCATION" not in warnings:
        warnings.append("DISABLE_MODEL_INVOCATION")

    blob = f"{name}\n{body}\n{front}"
    if not execution:
        if text_mod.contains_any(blob, list(policy.get("stub_markers") or [])):
            execution = "stub"
        else:
            connectors = [c for c in (policy.get("connector_names") or []) if c in blob]
            # require od/agent-browser as tokens, not substring of random words
            connector_hits = []
            for conn in policy.get("connector_names") or []:
                if re_word(blob, conn):
                    connector_hits.append(conn)
            provider_hits = [p for p in (policy.get("provider_names") or []) if re_word(blob, p)]
            if connector_hits:
                execution = "connector-required"
                caps.extend(connector_hits)
            elif provider_hits:
                execution = "provider-required"
            else:
                execution = "reference-only"

    if execution == "stub":
        search_policy = "metadata-only"
        selection = "never"
        trust = "upstream"
        tier = "E1"
    elif execution == "connector-required":
        search_policy = "metadata-only"
        selection = "never"
        trust = "upstream"
        tier = "E1"
    elif execution == "provider-required":
        search_policy = "metadata-only"
        selection = "never"
        trust = "upstream"
        tier = "E1"
    else:
        search_policy = "metadata-only"
        selection = "never"
        trust = "upstream"
        tier = "E1"

    provider = front.get("od.upstream") if isinstance(front.get("od.upstream"), str) else None
    extra_caps = front.get("capabilities_required")
    if isinstance(extra_caps, list):
        caps.extend(str(item) for item in extra_caps if item)

    return {
        "trust": trust,
        "evidence_tier": tier,
        "style_authority": "none",
        "execution_class": execution,
        "search_policy": search_policy,
        "selection_policy": selection,
        "capabilities_required": list(dict.fromkeys(caps)),
        "provider": provider,
        "warnings": warnings,
    }


def re_word(text: str, token: str) -> bool:
    return re.search(r"(?<![A-Za-z0-9_-])" + re.escape(token) + r"(?![A-Za-z0-9_-])", text) is not None


def classify_recipe(
    *,
    path: str,
    community: bool,
    official: bool,
    policy: dict[str, Any],
) -> dict[str, Any]:
    del policy, path
    if community:
        return {
            "trust": "community",
            "evidence_tier": "E0",
            "style_authority": "none",
            "execution_class": "quarantined",
            "search_policy": "never",
            "selection_policy": "never",
            "warnings": [],
        }
    return {
        "trust": "upstream" if official else "unknown",
        "evidence_tier": "E1",
        "style_authority": "none",
        "execution_class": "reference-only",
        "search_policy": "metadata-only",
        "selection_policy": "metadata-only",
        "warnings": [],
    }


def derive_execution_status(execution_class: str, availability: str) -> str:
    if execution_class == "quarantined":
        return "quarantined"
    if execution_class == "stub":
        return "stub"
    if execution_class == "connector-required":
        return "native" if availability == "available" else "connector-missing"
    if execution_class == "provider-required":
        return "native" if availability == "available" else "provider-missing"
    if execution_class == "native-candidate":
        return "native" if availability == "available" else "reference-only"
    if execution_class == "adapted-candidate":
        return "adapted" if availability == "available" else "reference-only"
    return "reference-only"
