#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TEMP_STAGE="$(mktemp -d)"
trap 'rm -rf "$TEMP_STAGE"' EXIT

echo "=== Testing Self-Contained Managed Runtime ==="

# Ensure latest installation is committed
"$ROOT/install.sh" >/dev/null

# Verify CLI tools can execute independently from anywhere without depending on source git clone
agy-bestfriend doctor >/dev/null
agy-bestfriend skills list >/dev/null
agy-bestfriend mcp status >/dev/null
agy-bestfriend design-bank status >/dev/null
agy-bestfriend wrapper status >/dev/null

echo "PASS: test_self_contained_runtime"
