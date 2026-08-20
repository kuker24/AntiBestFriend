---
name: scroll-world
description: >
  Build a scroll-scrubbed fly-through landing: as the visitor scrolls, a
  pre-rendered camera flies into each scene and on to the next with no
  cuts. Use when: 3D world landing, diorama site, Emons-style isometric
  world, scroll cinematic, browse-through-the-industry hero, camera-scrub
  page, or the user runs /scroll-world. Uses GrokBuild image_gen,
  image_edit, and image_to_video plus a portable vanilla-JS scrub engine.
  Load bundled imagine before any generate/edit/video call. Not for an
  ordinary landing without a camera world (use impeccable), photoreal
  ads/identity with no world page (use visual-studio), or UI chrome motion
  (use emil-design-eng after Impeccable).
metadata:
  short-description: "Scroll-scrub fly-through world landing"
---

# Scroll World

A landing where **scroll drives a camera**. The camera flies into a scene,
then on to the next, as one connected flight. Stills and clips come from
GrokBuild tools. The page only scrubs pre-rendered video by scroll
position.

## Load first

Before any `image_gen`, `image_edit`, `image_to_video`, or
`reference_to_video` call, load bundled `imagine`. Tool choice, prompt
length, real-people references, shot length, and ffmpeg live there. Do
not restate them here.

## Hard rules

- Use only GrokBuild image/video tools. Do not call an external
  image/video API, CLI, or MCP.
- Do not invent tool parameters. There is no end-image lock and no
  video-to-video. Missing capability uses the fallback in
  [pipeline.md](references/pipeline.md).
- If `PRODUCT.md`, `DESIGN.md`, or an Impeccable pin exists, copy hex,
  name, type, and forbidden treatments into the pack lock. Do not invent
  brand facts.
- Ask at most four labeled questions, and only for blockers the brief
  does not already answer.
- Keep the mechanic fixed: continuous fly-through, scroll as scrubber.
- Match the user's language. Architecture names stay A / B.

## Handoff

| Request | Skill |
|---|---|
| Fly-through, diorama, 3D world, camera-scrub landing | this skill |
| Existing site; world is the hero | this skill produces world + engine; `impeccable` owns chrome, tokens, copy system |
| Ordinary landing without a camera world | `impeccable` |
| Photoreal stills, ads, cinematic, identity, thumbnails (no world page) | `visual-studio` |
| Photoreal person/creature inside this world | this skill owns the chain + page; load `visual-studio` cinematic for those stills/clips |
| Game sprites, tiles, icon sets | `game-asset-core` |
| UI chrome motion (nav, buttons), not the video scrub | `emil-design-eng` after Impeccable |

Do not load Emil for stills. Do not load Impeccable to render the video
chain. Do not load visual-studio for an ordinary landing.

## Run

1. Interview only what is missing. Write the pack at
   `.grok/scroll-world/<slug>/`. Templates:
   [prompts.md](references/prompts.md).
2. Generate stills. One style preamble, byte-for-byte, on every still.
   Review cohesion before any video.
3. Pick the architecture the user chose. Default **A** (walkthrough /
   locked-iso). **B** only for diorama / miniature / god's-eye.
   [pipeline.md](references/pipeline.md).
4. Encode for scrubbing. Mount
   [scrub-engine.js](references/scrub-engine.js) with
   [index-template.html](references/index-template.html) or into the
   existing site.
5. QA seams in background Chromium. Save screenshots to files.

## Interview

Ask at most these four, skip any the brief already answered:

1. **Subject** (open) — business or idea + one-line pitch.
2. **Camera** — fly-through (B: dives + aerial hops) / walkthrough
   (A, default) / locked-iso (A + fixed angle). One-line trade-off each.
3. **Journey** — propose 5–7 ordered scenes from the subject's own
   value chain; let the user edit. Last scene is the hero + CTA.
4. **Mobile** — native 9:16 second chain, or desktop only. State the
   generate count. Never ship a 16:9 centre-crop as "the mobile version."

Art-direction default: clay diorama isometric for B; grounded / photoreal
for A. User may override. Palette: design system first; otherwise propose
4–6 named hexes.

Count before generating: A = `N` stills + `N` videos. B = `N` stills +
`N` dives + `N−1` connectors. Mobile doubles the video count.

## Architectures

**A — continuous forward take (default).** Each leg starts on the
previous leg's **actual last frame**. No connectors. Wire
`connectors: []` and a small `crossfade` (~0.08). Camera never reverses
across a seam. Locked-iso is A plus the locked-iso clause in every leg.

**B — dive + aerial hop (diorama only).** One dive per scene from that
scene's still. A connector starts on dive *i*'s actual last frame and
flies toward scene *i+1*. Grok cannot lock the connector's last frame to
the next dive. The engine crossfade covers the near-miss. If a hop is
unusable, set that connector to `null` (direct crossfade). Do not use B
on a grounded photoreal walkthrough without saying it will read as a
rewind.

Inside one clip the camera may orbit, crane, or push-in. Across a seam
it must not reverse. Every A leg ends in a slow forward drift (final
second) and the next leg begins by continuing that drift.

## QA

Follow the live browser contract: `grok-chromium-cdp start`, then
browser-act or chrome-devtools-axi attached to that CDP. Never Google
Chrome, `chrome-direct`, `--headed`, or `HEADED=1` unless the user asks
to see a window.

- Screenshot just before and after each seam. Judge composition, not
  PSNR. A pop means the handoff used a still instead of a rendered frame,
  or B's crossfade cannot hide a content jump.
- Confirm `video.seekable.end(0) > 0` (blob URLs) and that `currentTime`
  tracks scroll.
- `prefers-reduced-motion`: stills only, no video, no particles.
- Mobile opt-in: serve the 9:16 files (`videoWidth < videoHeight`).
  Desktop-only: one phone-viewport sanity check; engine hardening is
  already on.

## Deliver

The page (or the mount into the existing site), the asset folder, and
short labels (architecture, N, mobile yes/no, what is locked). Do not
dump prompts, retries, or tool names unless the user asks.
