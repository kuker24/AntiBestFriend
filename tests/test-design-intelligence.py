#!/usr/bin/env python3
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root / "lib"))

from design_intelligence import catalog, doctor, policy, rank, selection

pol = policy.load_policy()
tax = policy.load_taxonomy()
known = policy.load_known_sources()
assert pol, "policy loaded"
assert tax, "taxonomy loaded"
assert known, "known sources loaded"

print("Design intelligence modules test passed.")
