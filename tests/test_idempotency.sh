#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

# Ensure agy is available in CI environments
if ! command -v agy >/dev/null 2>&1 && [[ ! -x "$HOME/.local/bin/agy-real" && ! -x "$HOME/.local/bin/agy" ]]; then
  mkdir -p "$HOME/.local/bin"
  cat << 'MOCK_AGY' > "$HOME/.local/bin/agy"
#!/usr/bin/env bash
if [[ "${1:-}" == "--version" ]]; then
  echo "1.1.17"
  exit 0
fi
if [[ "${1:-}" == "--help" ]]; then
  echo "  --dangerously-skip-permissions  Skip permission checks"
  exit 0
fi
if [[ "${1:-}" == "plugin" ]]; then
  if [[ "${2:-}" == "install" ]]; then
    mkdir -p "$HOME/.gemini/config/plugins/antigravity-bestfriend"
    cp -a -- "$3/"* "$HOME/.gemini/config/plugins/antigravity-bestfriend/"
  elif [[ "${2:-}" == "list" ]]; then
    echo "antigravity-bestfriend"
  elif [[ "${2:-}" == "uninstall" ]]; then
    rm -rf "$HOME/.gemini/config/plugins/antigravity-bestfriend"
  fi
  exit 0
fi
echo "MOCK AGY RUN: $@"
MOCK_AGY
  chmod +x "$HOME/.local/bin/agy"
  export PATH="$HOME/.local/bin:$PATH"
fi

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
