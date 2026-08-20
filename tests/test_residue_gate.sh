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

echo "=== Checking Staged Skills Post-Overlay Residue Gate ==="
# Run overlay on a temporary staging copy and verify zero Claude/Grok residue in final staged skills
if command -v python3 >/dev/null 2>&1; then
  stage_tmp="$(mktemp -d)"
  trap 'rm -rf "$stage_tmp"' EXIT
  mkdir -p "$stage_tmp/skills"

  # Read allowlist and stage+overlay each skill
  residue_found=0
  while IFS= read -r name || [[ -n "$name" ]]; do
    [[ -z "$name" || "$name" == \#* ]] && continue
    src="$ROOT/vendor/skills/$name"
    [[ -d "$src" ]] || continue
    dest="$stage_tmp/skills/$name"
    cp -a -- "$src" "$dest"

    overlay_file=""
    if [[ -f "$ROOT/overlays/$name.prepend.md" ]]; then
      overlay_file="$ROOT/overlays/$name.prepend.md"
    elif [[ -f "$ROOT/overlays/$name.body.md" ]]; then
      overlay_file="$ROOT/overlays/$name.body.md"
    fi

    python3 "$ROOT/lib/overlay.py" --dest "$dest" --name "$name" ${overlay_file:+--prepend "$overlay_file"} 2>/dev/null || true
  done <"$ROOT/vendor/skill-allowlist.txt"

  # Scan staged skills for forbidden residue patterns
  staged_residue="$(grep -rnE "(~/.claude/grokbestfriend-claude|grokbestfriend-claude/config/model-pool)" "$stage_tmp/skills/" 2>/dev/null || true)"
  if [[ -n "$staged_residue" ]]; then
    echo "FAIL: Claude/Grok residue found in staged skills after overlay:"
    echo "$staged_residue"
    residue_found=1
  fi

  rm -rf "$stage_tmp"
  trap - EXIT

  if [[ $residue_found -ne 0 ]]; then
    exit 1
  fi
  echo "PASS: staged skills residue gate (post-overlay clean)"
fi

echo "PASS: test_residue_gate"
