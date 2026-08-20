#!/usr/bin/env python3
"""Automated skill parity & policy verification test."""

import json, sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root / "lib"))

from validate_skills import validate_skills

allowlist = root / "vendor/skill-allowlist.txt"
policy = root / "vendor/skill-policy.json"
skills_dir = root / "vendor/skills"

report = validate_skills(skills_dir, allowlist, policy)
print("Skills Parity Report:", json.dumps(report, indent=2))

assert report["expected"] == 40, f"Expected 40 skills, got {report['expected']}"
assert report["installed"] == 40, f"Installed {report['installed']} skills"
assert report["model_routed"] == 24, f"Expected 24 model-routed, got {report['model_routed']}"
assert report["manual_only"] == 16, f"Expected 16 manual-only, got {report['manual_only']}"
assert len(report["missing"]) == 0, f"Missing skills: {report['missing']}"
assert len(report["errors"]) == 0, f"Skill errors: {report['errors']}"

print("PASS: test_skills_parity")
