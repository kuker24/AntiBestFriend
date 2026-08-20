# Pipeline

Build identity once. Derive every later still and shot from it.

## Identity pack

Project path: `.grok/visual-studio/<slug>/`

| File | What it is |
|---|---|
| `face.png` | Collar-to-crown close-up. The only face source. |
| `body-front.png` | Full-body front, head to toe, arms slightly off the body. |
| `body-back.png` | Full-body back, same framing. |
| `lock.txt` | Fixed traits, wardrobe, scale laws, forbidden changes. |
| `mouth-closed.png` / `mouth-open.png` | Creatures or any face that must change expression. |
| `size-ref.png` | Two-or-more subjects at locked proportion. Only when scale matters. |

Grey studio background on every sheet still. Soft even light. No environment,
no props unless they are part of the locked wardrobe.

Generate each view as its own image. Do not ask the image model for a
multi-panel sheet. If the user needs a contact sheet, assemble it in code
after the views exist (`imagine`: accurate visuals with code).

### Build

1. **Face.** User photo → `image_edit` into `face.png` on grey. Named real
   people stay reference-first (`imagine`). No photo → ask for one. Do not
   invent a likeness.
2. **Bodies.** `image_edit` from `face.png` plus the wardrobe brief. Keep
   the face identical. Front, then back from the front.
3. **Expressions.** For a creature or a face that must roar/speak/emote
   across shots: two stills of the same head, mouth closed and mouth open.
   Do not rely on the video model to invent the open mouth.
4. **`lock.txt`.** Short factual lines only: hair, bone, marks, wardrobe,
   logo placement, scale law, "do not enlarge / restyle / add sun". If a
   design system exists, paste exact hex and the logo path.

Reuse the pack on later turns. Do not rebuild because the session is new
if the folder is still there.

### Face-lock

When a later still needs the person:

- Attach `face.png` as the identity image.
- Do not attach `body-front.png` as the face source. Full-body heads are
  too small and drift.
- Restate the lock's face lines in the prompt.
- Wardrobe and body come from `body-front.png` only when the shot shows
  more than the head.

### Size-ref

When two subjects share a frame and their relative size is part of the
brief (rider on a creature, product in a hand, person next to a vehicle):

1. Start from the larger subject's still.
2. `image_edit`: add the smaller subject at the locked proportion. If scale
   is uncertain, render the smaller subject smaller, never larger.
3. Save as `size-ref.png`. Attach it to every later still or shot that
   includes both.
4. Prompt names the law in visible terms ("rider no taller than half a
   neck spike"), not only a multiplier.

## Prompt grammar

Compact blocks. `imagine` owns prompt length. Use the blocks to keep
locks; do not write an essay.

```text
SCENE: one concrete moment
REFS: what each attached image is (face / body / product / location / size-ref)
CHANGE: the one edit or action
LOCKS: identity, wardrobe, scale, camera, background, duration
PHYSICS: one real motion (video only)
```

Describe what stays as positive locks ("same rock wall, same exposure"),
not a list of negations. Acting is physical: swallow, jaw, breath, fingers,
cloth, hair. Do not write "dramatic" or "emotional" and stop.

## Images first

1. Location or set still. Reject it if the light is fake, flat, or
   conflicting. Bad light becomes bad video.
2. Hero still of the subject in that light, seeded from the pack.
3. Check the still against `lock.txt` before any video call.
4. Animate that still. The still is frame 1 (`imagine`).

Do not start a video from a text prompt when a still can be locked first.

## Fail-fast

One retry with a more concrete visual sentence. If the same defect
returns (drifted face, wrong scale, missing action, melted logo), change
the method: simpler still, split into two shots, or a new source frame.
Do not keep generating the same prompt.
