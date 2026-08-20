#!/usr/bin/env python3
"""Automated MCP policy & foreign ownership test."""

import json, os, sys, tempfile
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root / "lib"))

import mcp

policy = json.loads((root / "vendor/mcp-policy.json").read_text(encoding="utf-8"))
servers = policy.get("servers", {})

# 1. Verify exact 4 MCP targets & Zero Exa
assert "codebase-memory-mcp" in servers, "codebase-memory-mcp missing from policy"
assert "context7" in servers, "context7 missing from policy"
assert "shadcn" in servers, "shadcn missing from policy"
assert "serena" in servers, "serena missing from policy"
assert "exa" not in servers or servers["exa"].get("enabled") is False, "Exa must be strictly omitted"

# 2. Test classification in isolated temp environment
with tempfile.TemporaryDirectory() as tmp:
    tmp_path = Path(tmp)
    mcp_cfg_file = tmp_path / "mcp_config.json"
    ownership_file = tmp_path / "mcp-ownership.json"

    # Mock environment
    os.environ["AGY_CONFIG_DIR"] = str(tmp_path)
    os.environ["GBFC_OWNERSHIP"] = str(ownership_file)

    # Initial state: foreign server exists
    initial_cfg = {
        "mcpServers": {
            "my-custom-foreign-server": {
                "command": "custom-cmd",
                "args": ["--port", "8080"]
            }
        }
    }
    mcp_cfg_file.write_text(json.dumps(initial_cfg, indent=2) + "\n")

    # Add owned server
    mcp.ensure_server("context7", servers["context7"])

    # Verify foreign server is preserved and context7 is added
    data, err = mcp.load_raw_json(mcp_cfg_file)
    assert not err, f"Load error: {err}"
    assert "my-custom-foreign-server" in data["mcpServers"], "Foreign server was wiped!"
    assert "context7" in data["mcpServers"], "Owned server was not added!"

    # Remove owned server
    mcp.remove_server("context7")

    # Verify foreign server is still intact and context7 removed
    data, err = mcp.load_raw_json(mcp_cfg_file)
    assert "my-custom-foreign-server" in data["mcpServers"], "Foreign server was wiped on removal!"
    assert "context7" not in data["mcpServers"], "Owned server was not removed!"

    # Attempt to remove foreign server (must be safely ignored)
    mcp.remove_server("my-custom-foreign-server")
    data, err = mcp.load_raw_json(mcp_cfg_file)
    assert "my-custom-foreign-server" in data["mcpServers"], "Foreign server was deleted by unowned remove!"

print("PASS: test_mcp_policy")
