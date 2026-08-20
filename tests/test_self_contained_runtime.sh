#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TEMP_STAGE="$(mktemp -d)"
trap 'rm -rf "$TEMP_STAGE"' EXIT

echo "=== Testing Self-Contained Managed Runtime ==="

# Ensure latest installation is committed
"$ROOT/install.sh" >/dev/null

# Move source out of the way to prove independence
TEMP_REPO="$(mktemp -d)/repo"
mv "$ROOT" "$TEMP_REPO"

# Re-register cleanup to restore repo
trap 'mv "$TEMP_REPO" "$ROOT" && rm -rf "$(dirname "$TEMP_REPO")" "$TEMP_STAGE"' EXIT

# Verify CLI tools can execute independently from anywhere without depending on source git clone
agy-bestfriend doctor >/dev/null
agy-bestfriend skills list >/dev/null
agy-bestfriend mcp status >/dev/null
agy-bestfriend design-bank status >/dev/null
agy-bestfriend wrapper status >/dev/null

# Verify uninstall works without source repo
agy-bestfriend uninstall >/dev/null

echo "PASS: test_self_contained_runtime"
