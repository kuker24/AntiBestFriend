# Design Intelligence

Local reference engine for GrokBestFriend 1.3.1. **Not an independent
router or skill.** Impeccable `new-work` owns its bounded retrieval stage.

This tree is policy, taxonomy, and schemas. The indexer lives in
`lib/design_intelligence/` and the CLI is `scripts/design-intelligence.py`.

```text
GROK_DESIGN_BANK                 → ~/Design              Refero + Motionsites
GROK_DESIGN_INTELLIGENCE_BANK    → ~/DesignIntelligence  this catalog
```

The two banks must not mix. Raw Open Design ZIPs stay on the operator machine.
They are not git objects and this repository does not redistribute them.

## Trust

- `_official` is an Open Design label, not GrokBestFriend trust.
- Brand-named systems in the curated fixture are evidence tier E1 and
  `inspiration-only`.
- Unknown license is local reference only. It is not permission to ship,
  export, or treat the item as authoritative.
- Catalogue stubs are not specialists. Availability is
  `vendor/skill-allowlist.txt` plus a host probe at search/doctor time.
- Catalog identity is a function of archive bytes. Host probes are never
  written into `catalog.jsonl`.

## Commands

```bash
python3 scripts/design-intelligence.py inspect-archive pack.zip
python3 scripts/design-intelligence.py import --bank /tmp/di --archive pack.zip
python3 scripts/design-intelligence.py rebuild --bank /tmp/di
python3 scripts/design-intelligence.py search --bank /tmp/di --kind system --query "editorial dashboard"
python3 scripts/design-intelligence.py plan --intent greenfield --scope world --mode Operate --authority none
python3 scripts/design-intelligence.py shortlist --bank /tmp/di --intent greenfield --mode Operate --query "developer dashboard"
python3 scripts/design-intelligence.py doctor --bank /tmp/di
```

Bank resolution: `--bank` → `GROK_DESIGN_INTELLIGENCE_BANK` → `~/DesignIntelligence`.
Tests must pass `--bank` at a temporary path.

See [docs/design-intelligence.md](../../docs/design-intelligence.md).
