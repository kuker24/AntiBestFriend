# Classification

Static fields are computed from archive bytes. They must not change
between laptops for the same inputs.

## execution_class (persisted)

| Class | Meaning |
|---|---|
| `stub` | Catalogue pointer that tells the agent to install upstream |
| `reference-only` | Substantive text, not an executable GBF route |
| `connector-required` | Needs `od`, Open Design `agent-browser`, Figma, or similar |
| `provider-required` | Needs a named hosted API |
| `quarantined` | Community, unsafe, or untrusted executable claim |
| `native-candidate` / `adapted-candidate` | Reserved; catalog import does not emit these from ZIP rows |

Do not store `execution_status`, `runtime_availability`, or `available_via`.
Those are derived at search/doctor time.

`browser-act` is not `agent-browser`. `_official` is not first-party.

## License

- SPDX `known` only from an item-owned LICENSE file that matches the
  full canonical signature in policy (every required phrase, plus any
  grant phrase). One substring is not enough.
- Decoy text such as "not distributed under the Apache License" is
  not a grant.
- Nested vendor LICENSE files do not license the parent item.
- Manifest license without a file is `declared-only` / `local-only`.
- Missing is `unknown` / `local-only`.
- Declared SPDX must equal the file match after explicit
  `license_aliases`. Substring overlap (`MIT` vs `MIT-0`) is
  `conflicting` / `blocked`.
- Conflict is `conflicting` / `blocked`.

Unknown or local-only items may be used as local reference. They must
not be redistributed, exported, executed, or treated as authoritative.

## Evidence

Curated brand fixtures, including `tom-modern` with a GitHub origin URL,
are E1 and `inspiration-only`. A URL is recorded on `source.url`. It is
not official brand authority.

## Lineage

`plugins/_official/design-systems/<slug>/` aliases `system:<slug>` when
that system exists.

`plugins/_official/examples/<slug>/` aliases `structure:<slug>` only when
the example SKILL.md name or framed hash matches the template. Slug
overlap is a hint, not a grant.

`duplicate_of` and `alias_of` must point at a row in the same catalog.
They must not point at a vendor skill that is not a catalog item.
ZIP `emil-design-eng` stays `reference-only` with `duplicate_of = null`.
