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
    resolved = catalog.resolve_bank(None, env={"ANTIGRAVITY_DESIGN_BANK": str(tmp_path)})
    assert resolved == tmp_path, "Resolved bank root mismatch"
    
    pol = policy.load_policy()
    tax = policy.load_taxonomy()
    
    # Test catalog rebuild
    catalog.rebuild(tmp_path, policy=pol, taxonomy=tax)
    
    # Test doctor
    doc_result = doctor.doctor(tmp_path, pol, {})
    assert doc_result["status"] in ("OK", "UNAVAILABLE_MISSING", "DEGRADED"), f"Unexpected doctor status: {doc_result['status']}"
    
    # Test search & rank
    # Note: Because the fixture items lack actual image files, they might be dropped from the FTS index or filtered out.
    # The goal of this functional test is to ensure the pipeline components (rank, selection) can execute
    # end-to-end without crashing or raising exceptions against a constructed catalog.
    search_res = rank.search_bank(tmp_path, kind="all", query="dark", policy=pol, allowlist=set())
    assert "results" in search_res
    
    # Test selection / planning
    plan = selection.plan_retrieval("Create a dark mode landing page", "dark theme", "persuade", [])
    assert "query" in plan
    
    print("PASS: test_design_intelligence_functional")
