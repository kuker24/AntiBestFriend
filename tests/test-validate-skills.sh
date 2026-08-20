#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$ROOT/lib/validate_skills.py" \
  --skills "$ROOT/vendor/skills" \
  --allowlist "$ROOT/vendor/skill-allowlist.txt" \
  --policy "$ROOT/vendor/skill-policy.json"
echo "Skills validation test passed."
