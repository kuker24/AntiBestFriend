# Design bank paths and catalog fields

Root: `$GROK_DESIGN_BANK` if set, otherwise `~/Design`. Both catalogs must exist or search exits non-zero.

| Bank | Catalog | Item files |
|---|---|---|
| Refero | `Refero/bank/catalog.json` | `Refero` + `files.design` / `files.tokens` / `files.tailwind` / `thumb` (those fields start with `/bank/...`) |
| Motion | `motionsites/library/catalog.json` | `motionsites/library/<jenis>/<id>/{meta.json,prompt.md,<preview>}` |

Do not crawl. Do not open `npm run bank` unless the user asked to browse.

## Refero style fields used for match

`name`, `slug`, `northStar`, `theme` (`dark`/`light`), `kind`, `tags[]`, `industry`, `fonts[]`, `colors[].hex`, `thumb`, `thumbMissing`, `trendingRank`, `popularRank`, `files`.

Kinds on disk: `dark-mode`, `editorial`, `playful`, `monochrome`, `high-contrast`, `soft-gradients`, `brutalist`, `minimal`, `lainnya`.

## Motion item fields used for match

`id`, `title`, `jenis`, `page_type`, `types_source[]`, `category_source`, `industry`, `preview`, `featured`, `popular_score`.

Jenis on disk: `hero`, `landing-page`, `features`, `about`, `footer`, `cta`, `pricing`, `404`, `mobile-app`, `testimonials`, `stats`, `blog`, `carousel`, `3d-website`.

`preview` is a filename next to `prompt.md`. Prefer a still (`webp`/`png`/`jpg`/`gif`) over `mp4`.
