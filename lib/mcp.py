#!/usr/bin/env python3
"""Classify and mutate Antigravity MCP servers. Zero secret exposure. Zero Exa."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

PRODUCT = "antigravity-bestfriend"


def agy_config_dir() -> Path:
    return Path(os.environ.get("AGY_CONFIG_DIR", Path.home() / ".gemini" / "config"))


def mcp_config_path() -> Path:
    return agy_config_dir() / "mcp_config.json"


def managed_dir() -> Path:
    return Path(os.environ.get("GBFC_MANAGED", Path.home() / ".gemini" / "antigravity-bestfriend"))


def ownership_path() -> Path:
    return Path(os.environ.get("GBFC_OWNERSHIP", managed_dir() / "config" / "mcp-ownership.json"))


def load_json(path: Path, default):
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    tmp.chmod(0o600)
    tmp.replace(path)


def owned_map() -> dict:
    data = load_json(ownership_path(), {"servers": {}})
    if not isinstance(data, dict):
        return {"servers": {}}
    data.setdefault("servers", {})
    return data


def record_owned(name: str, spec: dict) -> None:
    data = owned_map()
    data["product"] = PRODUCT
    data["servers"][name] = {
        "name": name,
        "owned": True,
        "spec": spec,
    }
    save_json(ownership_path(), data)


def unrecord(name: str) -> None:
    data = owned_map()
    data.get("servers", {}).pop(name, None)
    save_json(ownership_path(), data)


def load_mcp_config() -> dict:
    data = load_json(mcp_config_path(), {})
    if not isinstance(data, dict):
        return {"mcpServers": {}}
    data.setdefault("mcpServers", {})
    return data


def save_mcp_config(data: dict) -> None:
    save_json(mcp_config_path(), data)


def classify(name: str, wanted: dict) -> dict:
    if name == "exa":
        return {"name": "exa", "state": "FORBIDDEN_OMITTED"}
    cfg = load_mcp_config()
    servers = cfg.get("mcpServers") or {}
    own = owned_map().get("servers") or {}
    if name not in servers:
        return {"name": name, "state": "MISSING"}
    existing = servers[name]
    if name in own:
        return {"name": name, "state": "EXISTING_OWNED", "info": existing}
    if wanted.get("serverUrl") and existing.get("serverUrl") == wanted["serverUrl"]:
        return {"name": name, "state": "EXISTING_EQUIVALENT_FOREIGN", "info": existing}
    if wanted.get("command") and existing.get("command") == wanted["command"]:
        return {"name": name, "state": "EXISTING_EQUIVALENT_FOREIGN", "info": existing}
    return {"name": name, "state": "EXISTING_CONFLICT_FOREIGN", "info": existing}


def ensure_server(name: str, spec: dict, enabled: bool = True) -> int:
    if name == "exa":
        sys.stderr.write("refusing to add Exa MCP\n")
        return 1
    cfg = load_mcp_config()
    cfg.setdefault("mcpServers", {})

    server_entry = {}
    if spec.get("serverUrl") or spec.get("url"):
        server_entry["serverUrl"] = spec.get("serverUrl") or spec.get("url")
    else:
        cmd = spec.get("command")
        if spec.get("commandKind") == "owned-binary" or not cmd:
            cmd = os.environ.get("GBFC_CBM_BIN", str(managed_dir() / "components/codebase-memory/bin/codebase-memory-mcp"))
        server_entry["command"] = cmd
        server_entry["args"] = spec.get("args") or []

    # Use explicit enabled flag from spec if present
    if "enabled" in spec:
        server_entry["disabled"] = not spec["enabled"]
    elif "disabled" in spec:
        server_entry["disabled"] = spec["disabled"]
    else:
        server_entry["disabled"] = not enabled

    cfg["mcpServers"][name] = server_entry
    save_mcp_config(cfg)
    record_owned(name, server_entry)
    print(f"Added/Updated MCP server {name}")
    return 0


def remove_server(name: str) -> int:
    cfg = load_mcp_config()
    if name in cfg.get("mcpServers", {}):
        del cfg["mcpServers"][name]
        save_mcp_config(cfg)
    unrecord(name)
    print(f"Removed MCP server {name}")
    return 0


def snapshot_owned(out: Path) -> None:
    data = owned_map()
    save_json(out, data)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("cmd")
    parser.add_argument("--name")
    parser.add_argument("--policy", default="")
    parser.add_argument("--out", default="")
    parser.add_argument("--spec", default="")
    args = parser.parse_args()
    policy = load_json(Path(args.policy), {"servers": {}}) if args.policy else {"servers": {}}

    if args.cmd == "classify":
        wanted = (policy.get("servers") or {}).get(args.name) or {}
        print(json.dumps(classify(args.name, wanted), indent=2))
        return 0
    if args.cmd == "classify-all":
        out = {}
        for name, wanted in (policy.get("servers") or {}).items():
            if name == "exa":
                continue
            out[name] = classify(name, wanted)
        print(json.dumps(out, indent=2))
        return 0
    if args.cmd == "add":
        wanted = (policy.get("servers") or {}).get(args.name) or {}
        return ensure_server(args.name, wanted)
    if args.cmd == "remove":
        return remove_server(args.name)
    if args.cmd == "snapshot-owned":
        out = Path(args.out)
        snapshot_owned(out)
        return 0 if out.is_file() else 1
    if args.cmd == "list-names":
        cfg = load_mcp_config()
        print("\n".join(cfg.get("mcpServers", {}).keys()))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
