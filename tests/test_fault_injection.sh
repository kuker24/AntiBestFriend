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

echo "=== Testing Transactional Fault Injection & Rollback ==="

# Helper to hash only transactional files
hash_state() {
  local paths=(
    "$HOME/.gemini/config/mcp_config.json"
    "$HOME/.gemini/config/hooks.json"
    "$HOME/.gemini/GEMINI.md"
    "$HOME/.local/bin/agy"
    "$HOME/.local/bin/agy-real"
    "$HOME/.gemini/config/plugins/antigravity-bestfriend"
    "$HOME/.gemini/antigravity-cli/plugins/antigravity-bestfriend"
    "$HOME/.gemini/antigravity-bestfriend/config/mcp-ownership.json"
    "$HOME/.gemini/antigravity-bestfriend/config/design-bank.json"
  )
  for p in "${paths[@]}"; do
    [[ -e "$p" ]] && find "$p" -type f -exec sha256sum {} + 2>/dev/null
  done | sort | sha256sum | awk '{print $1}'
}

# Get baseline state
baseline_hash="$(hash_state)"

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
  
  recovered_hash="$(hash_state)"
  
  if [[ "$baseline_hash" != "$recovered_hash" ]]; then
    echo "FAIL: State hash drifted after recovery ($baseline_hash -> $recovered_hash)"
    exit 1
  fi
done

echo "PASS: test_fault_injection"
