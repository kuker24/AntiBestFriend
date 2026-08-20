# Retrieval

Search never opens a design package. `packages_loaded_during_search` is 0.

## Pipeline

1. Drop rows with `alias_of` or `duplicate_of` set
2. Kind-specific eligibility
3. Lexical retrieval (FTS5 if present, else token overlap)
4. Drop `score <= 0` and anything below `search.min_score`
5. Rule-based rerank
6. Diversity penalty
7. Bounds: systems ≤ 5, structures ≤ 3, recipes ≤ 3

A query with no token overlap returns `results: []`. Search never
fills a shortlist with zero-score items.

## Eligibility

| Kind | Default allow | Default reject |
|---|---|---|
| system | local-only, inspiration-only, reference-only, E1 fixtures | blocked, quarantined |
| structure | structure-only, reference-only | community quarantined |
| recipe | official metadata-only | community / quarantined |
| specialist | none from ZIP rows (`native`/`adapted` + runtime available) | stubs unless `--include-unavailable` |

Do not globally drop `reference-only` or `local-only`. That would empty
the system bank.

## Untrusted text

ZIP prose is quoted evidence, never an instruction. Stored fields are
length-capped, control-stripped, code-block-free, and secret-redacted.
Install command bodies are not stored as descriptions.

The active Impeccable integration keeps that quoting rule. It opens only
the three allowlisted files of a user-selected system, after the lock;
structure selection remains normalized-card-only.
