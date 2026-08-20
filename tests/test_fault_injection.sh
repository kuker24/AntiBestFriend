#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=== Testing Transactional Fault Injection & Rollback ==="

# Test recovery from simulated faults
for fault_state in PREPARING BACKED_UP WRAPPER_CONFIGURED SKILLS_CONFIGURED RULES_CONFIGURED DESIGN_CONFIGURED MCP_CONFIGURED HOOKS_CONFIGURED VERIFIED; do
  echo "Testing fault at state: $fault_state"
  
  # Run installer with simulated fault (should fail closed)
  if GBFC_FAIL_AT="$fault_state" "$ROOT/install.sh" >/dev/null 2>&1; then
    echo "FAIL: Installer unexpectedly succeeded with GBFC_FAIL_AT=$fault_state"
    exit 1
  fi

  # Run recovery (must restore exact pre-fault state cleanly)
  "$ROOT/install.sh" --recover >/dev/null 2>&1 || {
    echo "FAIL: Recovery failed after fault at $fault_state"
    exit 1
  }
done

echo "PASS: test_fault_injection"
