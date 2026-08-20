#!/usr/bin/env python3
import json, sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
policy = json.loads((root / "vendor/mcp-policy.json").read_text())
servers = policy.get("servers", {})

assert "codebase-memory-mcp" in servers, "codebase-memory-mcp missing"
assert "context7" in servers, "context7 missing"
assert "shadcn" in servers, "shadcn missing"
assert "serena" in servers, "serena missing"
assert servers.get("exa", {}).get("enabled") is False, "exa must be disabled"

print("MCP policy test passed. Zero exa confirmed.")
