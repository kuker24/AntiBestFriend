#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=== Testing Installation Idempotency ==="

# First installation
"$ROOT/install.sh" >/dev/null

# Second installation immediately after
"$ROOT/install.sh" >/dev/null

# Verify doctor is 100% clean
"$ROOT/install.sh" --doctor >/dev/null

# Verify wrapper header is intact and not nested
wrapper_file="$HOME/.local/bin/agy"
second_line="$(sed -n '2p' "$wrapper_file")"
if [[ "$second_line" != "# ANTIBESTFRIEND-AGY-WRAPPER" ]]; then
  echo "FAIL: Wrapper corrupted or improperly formatted: $second_line"
  exit 1
fi

echo "PASS: test_idempotency"
