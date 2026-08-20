---
name: visual-studio
description: >
  Produce photoreal product stills, reusable identity packs, UGC/ad videos,
  cinematic VFX shots, and video thumbnails with GrokBuild image_gen,
  image_edit, image_to_video, and reference_to_video. Use when: product
  photo, studio shot, lifestyle, Pinterest pin, hero banner, carousel, ad
  pack, virtual try-on, UGC, unboxing, product review, TV spot, cinematic
  video, VFX, character sheet, size-ref, face-lock, YouTube thumbnail,
  Shorts cover, or the user runs /visual-studio. Load bundled imagine
  before any generate/edit/video call. Not for UI/frontend (use
  impeccable), game sprites or tiles (use game-asset-core), or UI motion
  (use emil-design-eng).
metadata:
  short-description: "Photoreal stills and short videos on Grok tools"
---

# Visual Studio

Production director for photoreal stills and short videos. GrokBuild already
owns the tools. This skill owns the production order, identity, modes, and
VFX method.

## Load first

Before any `image_gen`, `image_edit`, `image_to_video`, or
`reference_to_video` call, load bundled `imagine`. Tool choice, prompt
length, real-people references, exact text, shot length, and ffmpeg concat
live there. Do not restate them here.

## Hard rules

- Use only GrokBuild image/video tools. Do not call an external image/video
  API, CLI, or MCP.
- Do not invent tool parameters. If a capability is missing (video-to-video,
  15s one-take, trained identity models), use the fallback in the matching
  reference.
- Match the user's language. Mode names stay English.
- Recurring people, products, creatures, and wardrobes come from an
  identity pack ([pipeline.md](references/pipeline.md)). Never a fresh
  `image_gen` of "the same" subject.
- If `PRODUCT.md`, `DESIGN.md`, or an Impeccable pin exists, copy its hex,
  logo path, type, and forbidden treatments into the pack lock. Do not
  invent brand facts.
- Ask at most four labeled questions, and only for blockers the brief does
  not already answer.

## Handoff

| Request | Skill |
|---|---|
| UI, landing, dashboard, design system | `impeccable` |
| Scroll-scrub fly-through, diorama, 3D-world landing | `scroll-world` |
| Website/app whose UI needs designed photos or videos | `impeccable` leads the surface; this skill produces the media |
| Game sprites, tiles, icon sets, animation sheets | `game-asset-core` |
| UI motion / interaction feel | `emil-design-eng` after Impeccable |
| Photoreal stills, ads, cinematic, identity, thumbnails (no UI) | this skill |
| Photoreal person/creature inside a world page | `scroll-world` owns the chain + page; this skill cinematic for those stills/clips |

## Route

Pick one lane from the brief. Load only that reference.

| Lane | User wants | Load |
|---|---|---|
| identity | character sheet, digital twin, face-lock, reusable person/creature | [pipeline.md](references/pipeline.md) |
| still | product photo, studio, lifestyle, pin, hero, carousel, try-on, restyle | [modes.md](references/modes.md) stills |
| ad-video | UGC, how-to, unboxing, review, TV spot, try-on video | [modes.md](references/modes.md) ads |
| cinematic | VFX, plate, creature, jump, flyby, location cinematic | [cinematic-vfx.md](references/cinematic-vfx.md) |
| thumbnail | YouTube thumbnail, Shorts/Reels cover | [modes.md](references/modes.md) thumbnails |

A campaign that needs a person plus product plus video: identity pack first,
then stills, then ads or cinematic. Do not start at video.

## Run

1. Route the lane. Load `imagine` plus the one reference.
2. Reuse or build the identity pack before any scene that repeats a subject.
3. Stills first. Approve or self-check the still against the lock. Then
   animate.
4. One shot, one beat. Shot length and concat live in `imagine`.
5. Deliver the files with short labels (mode, ratio, what is locked). Do
   not dump prompts, retries, or tool names unless the user asks.
