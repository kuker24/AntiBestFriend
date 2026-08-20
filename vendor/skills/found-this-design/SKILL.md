---
name: found-this-design
description: >
  Find 3 or 5 matching UI designs from the local design bank at
  `$GROK_DESIGN_BANK` or `~/Design` (Refero styles + Motionsites
  sections) for the current web project or a redesign brief, then generate a
  high-fidelity first-viewport photo of this product in each recommended
  world. Use when the user runs /found-this-design or /found_this_design, or
  asks to find a design, cari desain, rekomendasi desain, design yang cocok,
  preview desain, prototype visual, design bank, Refero, Motionsites, or
  which visual direction fits this site. Not for implementing UI (use
  impeccable after a pick) or photoreal product/ad video (use visual-studio).
metadata:
  short-description: "Match 3–5 bank designs and generate product comps"
user-invocable: true
argument-hint: "[3|5] [query]"
---

# Found This Design

Find a visual direction from the local bank. Recommend 3 (default) or 5.
Generate a high-fidelity first-viewport photo of **this product** in each
world, then stop. `/impeccable` builds after the user picks.

`/found_this_design` is the same command.

## Load

- Matching: [references/matching.md](references/matching.md)
- Bank paths and fields: [references/banks.md](references/banks.md)
- Before any `image_gen` / `image_edit`: bundled `imagine`. Do not restate it.
- Do not load `impeccable`, `emil-design-eng`, `visual-studio`, or `adhd`.

## Hard rules

- Search with the scripts. Never read either `catalog.json` into context.
- Do not implement UI, copy a Motion prompt into code, or overwrite the
  project's `DESIGN.md` unless the user asked to pin files.
- Do not crawl Refero or Motionsites. Do not open `npm run bank` unless
  the user asked to browse.
- Generate comps only for the shortlist. One viewport per candidate. No
  full-page scroll, no contact sheet.
- Comp text may be approximate. Product facts on the cards must be true.
- Match the user's language. Lane names stay English.

## Run

`<skill-dir>` is this skill's directory.

1. **Fingerprint.** From the user text, decide `count` (5 only if they
   asked for 5 / "lebih banyak") and `query`. Then:

   ```bash
   node <skill-dir>/scripts/fingerprint.mjs --cwd <project> --query "<text>" --count 3 > brief.json
   ```

   If `PRODUCT.md` is missing and the query does not name a surface or
   product, ask one round: which surface, and what mood is forbidden.
   Do not ask for hex or canned aesthetic lanes.

2. **Search.**

   ```bash
   node <skill-dir>/scripts/search.mjs --brief brief.json --lane <identity|section|both> --count <n>
   ```

   Use `laneHint` from the brief unless the user named a lane. Override
   bank root with `GROK_DESIGN_BANK` or `--bank`. Exit 2 = catalogs
   missing; report the paths and stop.

3. **Read the shortlist packs only.** For each item: `preview`,
   `files.meta`, and the start of `files.design` (Refero) or
   `files.prompt` (Motion). Collect real product name, offer, and
   visitor job from `PRODUCT.md` / the query. Do not invent claims.

4. **Comps.** After the shortlist, not before. Save:

   ```text
   .impeccable/found-this-design/<slug>-comp.png
   .impeccable/found-this-design/<slug>-comp.prompt.txt
   ```

   One first-viewport photo of **this product** wearing that bank world.
   High fidelity, not a wireframe, not the source thumb. Layout may
   leave the current site. Keep product name, offer, facts, and the
   visitor's job. Aspect `16:9` desktop; `9:16` when the surface is
   `mobile-app` or the user asked mobile.

   | Condition | Tool | References |
   |---|---|---|
   | Current-site screenshot exists | `image_edit` | screenshot (product facts) + bank preview (world) |
   | Greenfield / no UI | `image_edit` | bank preview only; prompt carries product facts |
   | Tool blocked or failed | do not retry to evade | show the bank thumb; say the comp is missing |

   If there is no screenshot but a local page or dev server exists,
   capture one first viewport through `grok-chromium-cdp` + `browser-act`
   only as an edit reference. Skip if capture fails.

   Fire 3 or 5 calls in parallel, one prompt per candidate (2–5
   sentences): surface regions in order → this product's content in
   those regions → bank northStar / hexes / type / material →
   "high-fidelity designed website viewport, not a poster, not a
   photograph of a place". If a render reads as a poster or a photo of
   the subject, regenerate that slot once with a more literal layout
   skeleton. Write the prompt beside the png.

   Re-roll generates only new ids (`--exclude` the ones already shown).
   Expanding 3 → 5 generates the two extras only.

5. **Cards.** Equal weight. Hero = generated comp (workspace-relative
   path). Bank thumb is a small "source" label.

   Each card: product-in-that-world photo, source thumb, name, bank,
   kind/jenis, theme, one sentence from `reasons` (why it fits this
   brief — not "best"), pack paths. Mark the score leader as "closest
   to the brief".

   Then offer: pick one · show 5 (if 3) · re-roll with a steer.

6. **Pin + handoff.** After a pick, write
   `.impeccable/found-this-design.json` (`slug`, `bank`, pack paths,
   `lane`, one-line reason, `comp` path). Read that pack's DESIGN.md +
   tokens or prompt. The comp is a north-star preview, not a pixel spec;
   the bank pack owns tokens and type. Say the next step is
   `/impeccable` with this world and this comp. Stop. Do not write
   components.

   Redesign: old look is anti-reference. New: pin is the starting world.
   Section: keep the project's identity; Motion fills only that section.

## Prompt checklist (every comp)

- Product name and real offer, no invented customers/prices/metrics
- Named surface regions and their scale
- Bank hexes + type character + northStar or Motion material
- "Designed website viewport" — not poster, not interior photo
