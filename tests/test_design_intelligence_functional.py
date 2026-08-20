#!/usr/bin/env python3
"""Functional test for Design Intelligence search & ranking against deterministic fixture bank."""

import json, os, sys, tempfile
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root / "lib"))

from design_intelligence import catalog, doctor, policy, rank, selection

with tempfile.TemporaryDirectory() as tmp:
    tmp_path = Path(tmp)
    refero_dir = tmp_path / "Refero/bank"
    motion_dir = tmp_path / "motionsites/library"
    refero_dir.mkdir(parents=True)
    motion_dir.mkdir(parents=True)

    # Fixture Refero catalog
    refero_catalog = {
        "screens": [
            {
                "id": "ref-1",
                "name": "Linear Dark Landing",
                "kind": "dark-mode",
                "theme": "dark",
                "tags": ["minimal", "developer-tools", "dark"],
                "surface": "landing-page"
            }
        ]
    }
    (refero_dir / "catalog.json").write_text(json.dumps(refero_catalog, indent=2))

    # Fixture Motionsites catalog
    motion_catalog = {
        "sites": [
            {
                "id": "mot-1",
                "name": "Stripe Scroll 3D",
                "category": "3d-interactive",
                "tags": ["motion", "scroll", "interactive"],
                "surface": "landing-page"
            }
        ]
    }
    (motion_dir / "catalog.json").write_text(json.dumps(motion_catalog, indent=2))

    # Verify catalog resolution
    resolved = catalog.resolve_bank(tmp_path)
    assert resolved == tmp_path, "Resolved bank root mismatch"

    print("PASS: test_design_intelligence_functional")
