#!/usr/bin/env python3
"""Programmatic verification of installed AntigravityBestFriend skills."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_frontmatter(text: str) -> dict[str, str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    fm_text = match.group(1)
    data = {}
    for mf in re.finditer(r"^([a-zA-Z0-9_-]+):\s*(.*(?:\n(?![a-zA-Z0-9_-]+:).*)*)", fm_text, re.MULTILINE):
        k = mf.group(1).strip()
        v = mf.group(2).strip().strip('"\'')
        data[k] = v
    return data


def validate_skills(skills_dir: Path, allowlist_file: Path, policy_file: Path) -> dict:
    allowlist = [
        line.strip()
        for line in allowlist_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    policy_data = json.loads(policy_file.read_text(encoding="utf-8")).get("skills", {})

    report = {
        "expected": len(allowlist),
        "installed": 0,
        "model_routed": 0,
        "manual_only": 0,
        "missing": [],
        "errors": [],
    }

    for name in allowlist:
        skill_path = skills_dir / name / "SKILL.md"
        if not skill_path.is_file():
            report["missing"].append(name)
            continue
        report["installed"] += 1
        text = skill_path.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        if not fm.get("name") or not fm.get("description"):
            report["errors"].append(f"{name}: missing required frontmatter name/description")

        pol = policy_data.get(name, {}).get("invocation", "model")
        if pol == "model":
            report["model_routed"] += 1
        else:
            report["manual_only"] += 1

    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skills", required=True)
    parser.add_argument("--allowlist", required=True)
    parser.add_argument("--policy", required=True)
    args = parser.parse_args()

    report = validate_skills(Path(args.skills), Path(args.allowlist), Path(args.policy))
    print(json.dumps(report, indent=2))
    if report["missing"] or report["errors"] or report["installed"] != report["expected"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
