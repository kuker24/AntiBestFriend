# Prompt templates and intake

Fill-in-the-slots. Keep the **style preamble** byte-for-byte identical
across every scene still — that identical text is what makes the world
one place.

Shot length, prompt length, and tool choice live in bundled `imagine`.
Do not restate them here.

## Intake

Write into `.grok/scroll-world/<slug>/lock.txt`:

- `SUBJECT` — business + one-line pitch.
- `BRAND_NAME` — display name.
- `PALETTE` — 4–6 named hexes. One is the scene **background** (usually
  the lightest). One is the **accent**.
- `TONE` — a word or two.
- `STYLE` — art direction (default below).
- `CAMERA` — fly-through (B) | walkthrough (A) | locked-iso (A + clause).
- `MOBILE` — yes / no.
- `SECTIONS[]` — ordered; each: `id`, `label`, `subject` (what is in the
  scene), `eyebrow`, `title`, `body` (≤ 1 sentence), `tags[]` (0–3).
  Last section = hero product + CTA.

Copy brand facts from `PRODUCT.md` / `DESIGN.md` / an Impeccable pin
when they exist. Do not invent hex, name, or type.

## Style preamble

Reuse verbatim in every scene prompt. Swap only the bracketed bits.

Default (B / miniature):

```
Isometric low-poly 3D diorama floating as a small rounded island on a
plain solid [BG_HEX] background with a soft contact shadow beneath it.
Soft matte clay 3D render, rounded toy-model shapes, gentle warm studio
lighting, soft long shadows, tilt-shift miniature look. Cohesive color
palette of [PALETTE]. Highly detailed, centered composition, no text,
no letters, no numbers, no logos.
```

Swap the first two sentences for an alternate; keep the palette / no-text
tail:

- **Flat papercraft:** "Isometric layered paper-craft diorama, matte
  cardstock, clean die-cut edges, subtle drop shadows between layers."
- **Glossy toy:** "Isometric glossy vinyl-toy diorama, smooth plastic
  shading, soft rim light, collectible figurine look."
- **Claymation:** "Isometric stop-motion clay set, visible thumbprints,
  handmade plasticine texture, soft studio softbox light."
- **Neon night:** "Isometric miniature at night, warm interior glow and
  neon signage, moody rim light, wet reflective ground."
- **Photoreal architectural** (A / hospitality / luxury): "Ultra-
  photorealistic architectural photography of a single cohesive
  [subject], cinematic wide-angle, warm golden-hour light, natural
  materials, restrained designer furnishings, editorial magazine
  quality, shallow depth of field, no people." Drop the floating-island
  framing. Scenes are full-bleed. Cohesion is the identical preamble;
  do not restyle one still into a clone of another room.

## Scene still

```
[STYLE PREAMBLE]
Subject: [SECTION.subject — the building or space, a few figures doing
the work, the props that signal this stage].
```

- Name concrete props. They anchor the scene.
- Final hero section: drop the island framing; one oversized product
  on the same background with a few orbiting props.
- Compose for the centre. The page uses `object-fit: cover`. Keep the
  focal subject horizontally centred with a little headroom.
- First still: `image_gen`. Later stills: `image_edit` from an approved
  still so style does not drift. Recurring people or products: seed
  from a `visual-studio` identity pack, not a fresh `image_gen`.
- Desktop stills `3:2` or `16:9`. Mobile chain stills `9:16`.

## Leg — architecture A

Start image = previous leg's **actual last frame** (leg 0: first
scene still). No end image. Bold clauses stay verbatim.

```
Single continuous cinematic camera move, no cuts. **Continue the same
slow, steady forward glide.** [MID-LEG MOVE]. The camera moves into
[SCENE i] toward [FOCAL POINT]. **In the final second, settle back
into a slow, steady forward glide toward [the doorway / opening /
direction of the next scene].** [STYLE tail + PALETTE]. Smooth,
graceful, slow motion, subtle parallax. No text, no captions.
```

### Mid-leg library

Omit for a plain glide. Reversals are safe *inside* a leg.

**Locked-iso** (`CAMERA` = locked isometric glide): skip the library.
Put this clause, verbatim, in every leg:

```
The camera keeps exactly the same high isometric angle throughout —
no rotation, no orbit, no tilt. It only travels straight and level,
the world sliding past beneath the same view.
```

When checking each last frame, also check the angle has not drifted.

- **Half-orbit** (product, luxury): "sweeping in a slow half-orbit
  around [the hero object], keeping it centered, then continuing past it"
- **Crane-up** (atriums, campuses): "rising smoothly as the full scale
  of [the space] reveals below"
- **Low lateral track** (lines, counters): "tracking low and level
  alongside [the line], foreground objects sliding past in parallax"
- **Push-in + ease back** (craft): "pushing in close to [the craft
  moment] until it nearly fills the frame, then easing gently back out"
- **Rise-and-swoop** (outdoors): "climbing in a gentle arc over [the
  terrain], then swooping down toward [the next focal point]"

Eyeball each last frame before the next leg. It must read as a calm
forward glide. A bad handoff frame poisons every leg after it.

## Dive — architecture B

Start image = the scene still (solid background, not a knockout).

```
Single continuous cinematic camera move, no cuts. Begin high and far,
looking down at the whole [SECTION.subject] from outside like a tiny
model. The camera slowly glides forward and descends toward [FOCAL
POINT], as if flying inside. As the camera pushes in, the roof and
upper structure gently lift and open away to reveal the interior.
[STYLE tail + PALETTE]. Smooth, graceful, slow motion, subtle
parallax. No text, no captions.
```

No building to open (field, plaza, road): replace the roof clause with
"the camera flies low across [the scene] toward [focal point]."

## Connector — architecture B

Start image = dive *i* **last** frame (extracted). There is no end-image
lock. Prompt toward scene *i+1*; the engine crossfade covers the landing.

```
Single continuous cinematic camera move, no cuts. The camera smoothly
pulls up and back out of [SCENE i], rising into the sky, then glides
forward across the connected miniature world and arrives above
[SCENE i+1], beginning to descend toward it. One connected miniature
world, seamless flowing aerial transition. [STYLE tail + PALETTE].
Smooth graceful slow motion. No text, no captions.
```

Last connector into a hero-product finale: "…glides forward and the
world dissolves toward a single giant [PRODUCT] floating in soft [BG]
space, arriving in front of it."

## Copy per section

- `eyebrow` — 2–4 words, uppercase feel.
- `title` — 3–6 words. First section = the site's hero line. Last =
  the payoff and carries the CTA.
- `body` — one sentence, plain-spoken, from the visitor's side.
- `tags` — 0–3 short proof chips.

Exact words belong in the HTML config, never in a generated still or
clip (`imagine`: accurate visuals with code).
