# Normalization

## Frontmatter

No PyYAML. A line-oriented reader accepts only:

```text
name
description
triggers
disable-model-invocation
od.mode
od.surface
od.platform
od.category
od.upstream
capabilities_required
```

Unsupported structure sets `FRONTMATTER_PARTIAL` and
`normalization_status = partial`. Do not guess.

## Systems

Require `manifest.json`, `DESIGN.md`, `tokens.css`. Index compact
philosophy fields only. Never store the full DESIGN.md.

## Structures

Keep information architecture only when a heading or list proves it.
Empty fields plus `partial` / `manual-required` beat an invented
archetype. Record `extraction_evidence`.

## Content hash

Frame each primary file as `path NUL length NUL bytes NUL` in sorted
path order, then SHA-256 the stream.

## Generational catalog

Write `catalog-<generation>.sqlite3` and `.jsonl` under new names.
`generation_id` is a framed hash of the JSONL bytes plus every input
archive hash. A ZIP byte change that does not change extracted
metadata still produces a new generation.

`catalog.lock.json` is the commit pointer and is replaced last.
Readers require both lock artifacts, verify their hashes, and re-check
`generation_id`. A schema-invalid item fails the rebuild and leaves
the last healthy lock in place. `check_item` mirrors the catalog-item
schema (types, required nested fields, string arrays,
`additionalProperties=false`). Two raw archives that share a logical
name after `(N)` stripping fail closed.
