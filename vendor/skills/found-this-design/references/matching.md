# Matching spec

Implemented by `scripts/search.mjs`. Do not restate the numbers in SKILL.md.

## Brief (from `fingerprint.mjs`)

`intent` (`new`|`redesign`|`section`), `mode` (Persuade|Operate|Read|Experience), `surface`, `industry`, `theme` (`dark`|`light`|`unknown`), `kinds[]`, `query` (compact distinctive tokens, not whole files), `hexes[]`, `productName`, `count` (3 or 5), `laneHint`, `avoid[]`.

## Weights — Refero

| Signal | Points |
|---|---|
| `kind` in `brief.kinds` | +24 |
| any `tag` in `brief.kinds` | +12 (if kind itself did not already hit) |
| `theme` equals brief | +20 |
| theme opposite brief | −8 |
| token overlap on name + northStar + tags + fonts + industry vs `query` | 0–24 |
| industry string overlap | +12 |
| closest accent-hue Δ ≤ 30° (ignore gray / near-black / near-white) | 0–10 |
| `trendingRank` or `popularRank` present | +4 × (21 − rank) / 20 |
| `thumbMissing` | −15 |

## Weights — Motion

| Signal | Points |
|---|---|
| `jenis` / `page_type` / `types_source` equals `brief.surface` | +28 |
| related pair `hero` ↔ `landing-page` | +16 |
| industry or `category_source` overlap | +20 |
| title + id token overlap vs `query` | 0–16 |
| `featured` | +4 |
| `popular_score` | +min(4, score / 8) |

## Aliases (fingerprint)

**Theme / kind:** dark, gelap, midnight, noir → `theme=dark` + kind `dark-mode`. light, terang, cream, paper, ivory → `theme=light`. editorial, magazine, newspaper, serif → `editorial`. playful, fun, colorful, cartoon → `playful`. mono, monochrome, grayscale → `monochrome`. contrast, swiss engineering → `high-contrast`. gradient, aurora, glow, soft → `soft-gradients`. brutalist, raw, concrete → `brutalist`. minimal, clean, swiss, quiet → `minimal`. Kinds come from the user query, then `PRODUCT.md` — not from `DESIGN.md`. Theme may still use `DESIGN.md` hex luminance.

**Surface:** hero → `hero`. landing, homepage, marketing → `landing-page`. about, tentang → `about`. pricing, harga → `pricing`. footer → `footer`. 404, not found → `404`. mobile, app screen → `mobile-app`. feature, benefits → `features`. blog, article, docs → `blog`. testimonial, review → `testimonials`. stats, metrics → `stats`. cta, waitlist → `cta`. 3d, webgl → `3d-website`. dashboard, admin, settings → `dashboard`.

**Industry:** saas, software, b2b, productivity → `saas`. wellness, health, healthcare, medical → `wellness`. portfolio, personal → `portfolio`. agency, studio → `agency`. finance, fintech, bank → `finance`. shop, store, ecommerce → `commerce`.

**Lane hint:** `dashboard` → `identity`. `redesign`/`new` on a whole surface (`landing-page`, `hero`, `mobile-app`, `3d-website`, `portfolio`) → `both`. other motion jenis → `section`. leftover `redesign`/`new` → `identity`. else `both`.

**Mode:** landing/marketing/pricing/campaign → Persuade. dashboard/admin/settings/app UI → Operate. docs/article/blog/help → Read. portfolio/gallery/showcase → Experience.

## Diversity and mix

- Slug family = slug/id with a trailing 8-hex suffix stripped, then a trailing `-hero` stripped. One family per shortlist.
- `--lane identity` = Refero only. `section` = Motion only.
- `both`: if each bank has at least one item scoring ≥ 8, reserve one slot each, then fill by score. Do not fill all 3/5 from one bank while the other still has hits ≥ 8.
- `--exclude` drops those slugs/ids (re-roll).

## Reason codes

`kind`, `theme`, `tokens`, `industry`, `surface`, `hue`, `rank`, `featured`. Agent writes one user-facing sentence from these. Do not show raw score unless asked.
