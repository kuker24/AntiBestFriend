#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=== Checking Tracked Bytecode Gate ==="
tracked_pyc="$(git -C "$ROOT" ls-files | grep -E "(__pycache__|\.pyc$|\.pyo$)" || true)"
if [[ -n "$tracked_pyc" ]]; then
  echo "FAIL: Tracked Python bytecode detected:"
  echo "$tracked_pyc"
  exit 1
fi

echo "=== Checking Hardcoded Machine Paths Gate ==="
target_pattern="$(printf '/home/%s|/Users/%s' "fahmiagent" "fahmiagent")"
personal_paths="$(grep -rnE "$target_pattern" "$ROOT" \
  --exclude-dir=.git \
  --exclude-dir=tx \
  --exclude-dir=backups \
  --exclude-dir=stage \
  --exclude-dir=.serena \
  --exclude="test_residue_gate.sh" \
  --exclude="*.pyc" || true)"

if [[ -n "$personal_paths" ]]; then
  echo "FAIL: Hardcoded personal paths detected:"
  echo "$personal_paths"
  exit 1
fi

echo "=== Checking Forbidden Runtime Claude Residues Gate ==="
claude_residue="$(grep -rnE "(~/\.claude/CLAUDE\.md|~/\.claude/grokbestfriend-claude)" "$ROOT/rules" "$ROOT/templates" "$ROOT/runtime" 2>/dev/null || true)"
if [[ -n "$claude_residue" ]]; then
  echo "FAIL: Forbidden runtime Claude residue detected in active rules/runtime:"
  echo "$claude_residue"
  exit 1
fi

echo "PASS: test_residue_gate"
