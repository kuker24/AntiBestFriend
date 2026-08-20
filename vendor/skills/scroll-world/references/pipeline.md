# Pipeline

Grok tools + ffmpeg. Shot length (6s default, 10s only if asked) lives
in bundled `imagine`. Do not invent end-image, video-to-video, or extra
durations.

Project pack: `.grok/scroll-world/<slug>/`

Site assets: `./assets` (stills as webp) and `./assets/vid` (mp4).

| File | What it is |
|---|---|
| `lock.txt` | Subject, palette, style preamble, camera, mobile, section list |
| `still_<id>.png` | Approved scene still |
| `first_<id>.png` / `last_<id>.png` | Boundary frames from a **rendered** clip |
| `leg_<id>.mp4` or `dive_<id>.mp4` | Raw generate |
| `conn_<n>.mp4` | Architecture B hop (optional) |

Reuse the pack on later turns if the folder is still there.

## 1. Stills

Write one prompt file per section ([prompts.md](prompts.md)). First
still: `image_gen`. Later stills: `image_edit` from an approved still
so the world does not drift.

Recurring people, products, or creatures: load `visual-studio` and
seed from its identity pack. Do not `image_gen` "the same" person.

Review the set before any video. Same angle family, palette, and light.
Re-roll an off-style still with `image_edit` from a good neighbour.

Posters for the page: convert to webp. To float a diorama, either match
`--sw-bg` to the scene background or `image_edit` the flat background
to transparency. Do not add a Python knockout path.

Desktop stills `3:2` or `16:9`. Mobile chain (only if opted in): a
second set at `9:16`, composed for portrait, not a crop.

## 2. Architecture A — sequential legs

No connectors. Legs **are** the journey.

1. Leg 0: `image_to_video` from `still_<first>.png`.
2. Extract the last frame:

```bash
ffmpeg -v error -sseof -0.15 -i "$WORK/leg_$prev.mp4" \
  -frames:v 1 -q:v 2 "$WORK/last_$prev.png"
```

3. Next leg: `image_to_video` from that last frame. Prompt continues
   the forward drift ([prompts.md](prompts.md)).
4. Eyeball `last_*.png` before spending the next generate. It must look
   like a frame from a gentle forward glide (locked-iso: angle unmoved).
   Re-roll the current leg if it does not.

Wire each leg as a section `clip` with `connectors: []` and
`crossfade` ≈ 0.08.

## 3. Architecture B — dives then hops

Diorama / miniature only.

1. One dive per scene: `image_to_video` from that scene's **solid**
   still. These may run in the same step.
2. Extract both ends from the **rendered** dives, never from the stills:

```bash
ffmpeg -v error -ss 0 -i "$WORK/dive_$n.mp4" \
  -frames:v 1 -q:v 2 "$WORK/first_$n.png"
ffmpeg -v error -sseof -0.15 -i "$WORK/dive_$n.mp4" \
  -frames:v 1 -q:v 2 "$WORK/last_$n.png"
```

3. Connector *i*: `image_to_video` from `last_<i>.png`. Prompt flies
   toward scene *i+1*. There is no end-image lock — the next dive's
   first frame will not be pixel-identical. Keep the engine `crossfade`
   (~0.12). A large content jump cannot be hidden; re-roll or set that
   connector to `null` (direct dissolve).
4. Do not start a connector from a diorama still. That is the usual
   seam pop.

## 4. Encode for scrubbing

Seekability comes from blob URLs in the engine, not from all-intra
video. Encode native resolution (do not upscale), strip audio, small
GOP, faststart:

```bash
enc() {
  ffmpeg -v error -y -i "$1" -an -vf "unsharp=5:5:0.8:5:5:0.0" \
    -c:v libx264 -preset slow -crf 20 -pix_fmt yuv420p \
    -g 8 -keyint_min 8 -sc_threshold 0 -movflags +faststart "$2"
}
```

Same settings for every clip in a chain so quality is uniform.

**Mobile opt-in** — native 9:16 renders encoded `scale=720:-2`, `-g 4`,
crf 23. Wire `clipMobile`, `connectorsMobile`, `stillMobile` (each
portrait clip's first frame). A 16:9 centre-crop is a labelled stopgap
only, never the silent default.

Desktop-only builds skip the second chain. The engine still hardens
phone scrubbing (seek-coalesce, iOS prime, safe-area).

## 5. Mount

Copy `scrub-engine.js` into the project. Standalone page:
`index-template.html`. Existing site: call `mountScrollWorld` on a
container; `impeccable` owns the chrome around it.

```js
mountScrollWorld(document.getElementById('world'), {
  brand: { name: 'BRAND' },
  diveScroll: 1.3, connScroll: 0.9,
  sections: [
    { id:'farm', label:'The Farms', still:'assets/farm.webp',
      clip:'assets/vid/farm.mp4',
      scroll: 1.6, linger: 0.45,
      accent:'#8FB98A', eyebrow:'…', title:'…', body:'…', tags:[] },
  ],
  connectors: [],          // A: empty. B: one url per gap, or null
});
```

`--sw-bg` must match the scene background. `--sw-ink` and `--sw-accent`
come from the lock. Give hero and finale a higher `scroll` + some
`linger` (keep `linger` ≤ 0.6). Transit scenes stay brisk.

Pacing lives in the engine (`scroll`, `linger`). Prefer expressive
motion in the clip and restraint in the scrub map.

## 6. Fail-fast

One retry with a more concrete camera sentence. If the same defect
returns (style drift, reverse-across-seam, melted geometry), change
the method: simpler still, plain forward glide, or drop that connector.
Do not keep generating the same prompt.

A safety block on a generate: stop, tell the user, offer a different
scene. Do not paraphrase to evade (`imagine`).
