#!/usr/bin/env python3
"""Classify and mutate Antigravity MCP servers. Foreign-safe. Zero secret exposure. Zero Exa."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
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


def load_raw_json(path: Path) -> tuple[dict | None, str | None]:
    if not path.is_file():
        return {"mcpServers": {}}, None
    try:
        content = path.read_text(encoding="utf-8")
        if not content.strip():
            return {"mcpServers": {}}, None
        data = json.loads(content)
        if not isinstance(data, dict):
            return None, "Root JSON must be an object"
        data.setdefault("mcpServers", {})
        return data, None
    except Exception as e:
        return None, str(e)


def save_mcp_config(data: dict) -> None:
    path = mcp_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp." + str(os.getpid()))
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    tmp.chmod(0o600)
    tmp.replace(path)


def owned_map() -> dict:
    path = ownership_path()
    if not path.is_file():
        return {"servers": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data.setdefault("servers", {})
            return data
    except Exception:
        pass
    return {"servers": {}}


def record_owned(name: str, spec: dict) -> None:
    path = ownership_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = owned_map()
    data["product"] = PRODUCT
    data["servers"][name] = {
        "name": name,
        "owned": True,
        "spec": spec,
    }
    tmp = path.with_suffix(".tmp." + str(os.getpid()))
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    tmp.chmod(0o600)
    tmp.replace(path)


def unrecord(name: str) -> None:
    path = ownership_path()
    if not path.is_file():
        return
    data = owned_map()
    data.get("servers", {}).pop(name, None)
    tmp = path.with_suffix(".tmp." + str(os.getpid()))
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    tmp.chmod(0o600)
    tmp.replace(path)


def resolve_spec(spec: dict) -> dict:
    resolved = dict(spec)
    cmd = resolved.get("command", "")
    if cmd == "@CODEBASE_MEMORY_BIN@" or resolved.get("commandKind") == "owned-binary":
        resolved["command"] = os.environ.get(
            "GBFC_CBM_BIN",
            str(managed_dir() / "components/codebase-memory/bin/codebase-memory-mcp")
        )
    return resolved


def classify(name: str, wanted: dict) -> dict:
    if name == "exa":
        return {"name": "exa", "state": "FORBIDDEN_OMITTED"}
    cfg, err = load_raw_json(mcp_config_path())
    if err:
        return {"name": name, "state": "INVALID_CONFIG", "error": err}
    servers = cfg.get("mcpServers") or {}
    own = owned_map().get("servers") or {}
    if name not in servers:
        return {"name": name, "state": "MISSING"}
    existing = servers[name]
    if name in own:
        return {"name": name, "state": "EXISTING_OWNED", "info": existing}

    # Compare with wanted spec
    resolved = resolve_spec(wanted)
    if resolved.get("serverUrl") and existing.get("serverUrl") == resolved["serverUrl"]:
        return {"name": name, "state": "EXISTING_EQUIVALENT_FOREIGN", "info": existing}
    if resolved.get("command") and existing.get("command") == resolved["command"]:
        return {"name": name, "state": "EXISTING_EQUIVALENT_FOREIGN", "info": existing}
    return {"name": name, "state": "EXISTING_CONFLICT_FOREIGN", "info": existing}


def ensure_server(name: str, spec: dict, enabled: bool = True) -> int:
    if name == "exa":
        sys.stderr.write("Refusing to configure Exa MCP (strictly omitted in AntiBestFriend)\n")
        return 1

    cfg, err = load_raw_json(mcp_config_path())
    if err:
        sys.stderr.write(f"FAIL CLOSED: Malformed MCP config: {err}\n")
        return 2

    cls = classify(name, spec)
    if cls["state"] == "EXISTING_CONFLICT_FOREIGN":
        sys.stderr.write(f"CONFLICT: MCP server {name} exists with foreign configuration. Not overwriting.\n")
        return 3
    if cls["state"] == "EXISTING_EQUIVALENT_FOREIGN":
        print(f"Reusing foreign equivalent MCP server {name} (FOREIGN_SHARED)")
        return 0

    resolved = resolve_spec(spec)
    server_entry = {}
    if resolved.get("serverUrl") or resolved.get("url"):
        server_entry["serverUrl"] = resolved.get("serverUrl") or resolved.get("url")
    else:
        server_entry["command"] = resolved.get("command")
        server_entry["args"] = resolved.get("args") or []

    if "enabled" in resolved:
        server_entry["disabled"] = not resolved["enabled"]
    elif "disabled" in resolved:
        server_entry["disabled"] = resolved["disabled"]
    else:
        server_entry["disabled"] = not enabled

    cfg["mcpServers"][name] = server_entry
    save_mcp_config(cfg)
    record_owned(name, server_entry)
    print(f"Added/Updated owned MCP server {name}")
    return 0


def remove_server(name: str) -> int:
    own = owned_map().get("servers") or {}
    if name not in own:
        print(f"Skipping MCP {name}: not owned by AntiBestFriend (FOREIGN_PRESERVED)")
        return 0

    cfg, err = load_raw_json(mcp_config_path())
    if err:
        sys.stderr.write(f"FAIL CLOSED: Malformed MCP config: {err}\n")
        return 2

    if name in cfg.get("mcpServers", {}):
        del cfg["mcpServers"][name]
        save_mcp_config(cfg)
    unrecord(name)
    print(f"Removed owned MCP server {name}")
    return 0


def snapshot_bytes(out_path: Path) -> None:
    p = mcp_config_path()
    if p.is_file():
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(p.read_bytes())


def restore_exact_bytes(src_path: Path) -> bool:
    if not src_path.is_file():
        return False
    data = src_path.read_bytes()
    expected_sha = hashlib.sha256(data).hexdigest()
    target = mcp_config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    got_sha = hashlib.sha256(target.read_bytes()).hexdigest()
    return got_sha == expected_sha


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("cmd")
    parser.add_argument("--name")
    parser.add_argument("--policy", default="")
    parser.add_argument("--out", default="")
    parser.add_argument("--src", default="")
    parser.add_argument("--enable", action="store_true", default=False)
    parser.add_argument("--disable", action="store_true", default=False)
    args = parser.parse_args()

    policy = {}
    if args.policy and Path(args.policy).is_file():
        policy = json.loads(Path(args.policy).read_text(encoding="utf-8"))

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
        if args.enable:
            wanted = dict(wanted)
            wanted["enabled"] = True
            wanted.pop("disabled", None)
        elif args.disable:
            wanted = dict(wanted)
            wanted["enabled"] = False
        return ensure_server(args.name, wanted)
    if args.cmd == "remove":
        return remove_server(args.name)
    if args.cmd == "snapshot":
        snapshot_bytes(Path(args.out))
        return 0
    if args.cmd == "restore":
        ok = restore_exact_bytes(Path(args.src))
        return 0 if ok else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
