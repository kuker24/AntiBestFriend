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
if [[ "${1:-}" == "plugin" ]]; then
  exit 0
fi
echo "MOCK AGY RUN: $@"
MOCK_AGY
  chmod +x "$HOME/.local/bin/agy"
  export PATH="$HOME/.local/bin:$PATH"
fi

echo "=== Testing Transactional Fault Injection & Rollback ==="

for fault_state in PREPARING BACKED_UP WRAPPER_CONFIGURED SKILLS_CONFIGURED RULES_CONFIGURED DESIGN_CONFIGURED MCP_CONFIGURED HOOKS_CONFIGURED VERIFIED; do
  echo "Testing fault at state: $fault_state"
  
  if GBFC_FAIL_AT="$fault_state" "$ROOT/install.sh" >/dev/null 2>&1; then
    echo "FAIL: Installer unexpectedly succeeded with GBFC_FAIL_AT=$fault_state"
    exit 1
  fi

  "$ROOT/install.sh" --recover >/dev/null 2>&1 || {
    echo "FAIL: Recovery failed after fault at $fault_state"
    exit 1
  }
done

echo "PASS: test_fault_injection"
