#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_HOME="$(mktemp -d)"
trap 'rm -rf "$TMP_HOME"' EXIT

echo "=== Testing in Isolated HOME: $TMP_HOME ==="

# Setup mock environment in isolated HOME
mkdir -p "$TMP_HOME/.local/bin" "$TMP_HOME/.gemini/config"

# Create mock upstream agy
cat << 'MOCK_AGY' > "$TMP_HOME/.local/bin/agy"
#!/usr/bin/env bash
if [[ "${1:-}" == "--version" ]]; then
  echo "1.1.17"
  exit 0
fi
if [[ "${1:-}" == "plugin" ]]; then
  exit 0
fi
echo "MOCK AGY RUN: $@"
MOCK_AGY
chmod +x "$TMP_HOME/.local/bin/agy"

# Run install inside isolated HOME
HOME="$TMP_HOME" PATH="$TMP_HOME/.local/bin:$PATH" "$ROOT/install.sh" >/dev/null

# Verify installation in isolated HOME
HOME="$TMP_HOME" PATH="$TMP_HOME/.local/bin:$PATH" "$ROOT/install.sh" --doctor >/dev/null

# Verify uninstall inside isolated HOME
HOME="$TMP_HOME" PATH="$TMP_HOME/.local/bin:$PATH" "$ROOT/uninstall.sh" >/dev/null

# Verify agy binary is restored to original mock
if [[ ! -x "$TMP_HOME/.local/bin/agy" ]]; then
  echo "FAIL: Original agy binary not restored on uninstall"
  exit 1
fi

echo "PASS: test_isolated_home"
