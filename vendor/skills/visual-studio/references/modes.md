# Modes

Pick by intent. When two modes fit, take the more specific one.

Product photo present → `image_edit` from that photo. No photo → ask once;
if the user declines, `image_gen` from a concrete description, then treat
the result as the product master.

A presenter or model who must recur: build the identity pack
([pipeline.md](pipeline.md)) before the first scene.

## Stills

| Mode | When | Ratio | Frame |
|---|---|---|---|
| `product_shot` | catalog, studio, Shopify, white/neutral | `1:1` | product isolated, true silhouette, soft contact shadow |
| `lifestyle_scene` | in use, kitchen, cafe, gym, desk | `4:5` | hands or context, product readable, real room light |
| `closeup_product_with_person` | applying, holding, demonstrating | `4:5` | tight on product + hands or partial face |
| `moodboard_pin` | Pinterest, vertical pin | `2:3` | editorial atmosphere; product still identifiable |
| `hero_banner` | site header, email, wide campaign | `16:9` | product as hero, empty space for later code type |
| `social_carousel` | 3–10 connected slides | `1:1` | one idea per slide, same light and palette |
| `ad_creative_pack` | Meta / TikTok / Pinterest / Google statics | `1:1` or `9:16` | same product, distinct hook per frame |
| `virtual_model_tryout` | worn, lookbook, on-body | `3:4` | garment/product true to master; model from pack or brief |
| `conceptual_product` | levitate, splash, CGI, sculptural | `1:1` | product shape locked; physics still readable |
| `restyle` | same subject, new season or aesthetic | keep source | change mood only; lock subject and logo |

Carousel and ad pack: generate each slide as its own `image_edit` from the
same product master. Vary angle, crop, or setting. Do not paraphrase one
prompt ten times.

Platform keyword wins format (`Pinterest` → `moodboard_pin`, `hero` →
`hero_banner`, `carousel` → `social_carousel`). "Closeup of hands applying
serum" → `closeup_product_with_person`.

Exact type, price, or UI on a still: leave space and overlay in code
(`imagine`). Do not bake long copy into the model.

## Ads

There is no 15s one-take. Each mode is a shot list. Default 6s per shot,
`9:16` for paid social, `16:9` for TV-like. Assemble with ffmpeg stream
copy (`imagine`).

Stills for every shot first. Animate the approved still.

| Mode | Shots (6s each) |
|---|---|
| `ugc` | hook to camera → product in use → hold + spoken CTA |
| `ugc_how_to` | problem → three tight demo beats → result |
| `ugc_unboxing` | closed package → first open → product in hand |
| `product_showcase` | hero orbit or push-in → material close-up → pack shot |
| `product_review` | presenter opinion → one proof detail → recommend |
| `tv_spot` | wide world → product insert → branded end card still |
| `wild_card` | one unexpected visual metaphor, then product lock |
| `ugc_virtual_try_on` | phone-shot try-on → turn → reaction |
| `virtual_try_on` | studio walk-up → garment close-up → look |

`ugc` reads as a phone. `tv_spot` reads as a crew. Do not mix those
cameras in one cut unless the brief says so.

Presenter on camera: attach `face.png`. Product in frame: attach the
product master. Both: still first with face-lock and product lock, then
`image_to_video`. Use `reference_to_video` only when a shot truly needs
several references at once; prefer a composed still.

After the cut exists, check: hook visible in shot 1, product readable in
at least one shot, one CTA. No numeric virality score.

## Thumbnails

Default `16:9` YouTube, `9:16` Shorts/Reels, `4:5` Instagram. One focal
subject. Truthful to the video — do not invent outcomes, faces, or
screenshots.

1. Write one information-gap concept (readable at ~120px).
2. `image_edit` from `face.png` and/or product/logo. Chest-up or
   medium-close. Faces in the upper two-thirds on `9:16`.
3. No baked text unless the user asks. Overlay 2–4 words in HTML/CSS
   (`imagine`) if they want a headline.
4. Split / versus / before-after only when the user asks for a split.

Surgical tweak (expression, background, rim light): `image_edit` the
picked thumbnail, change only that, lock everything else.

## Interview

Skip anything the brief or attachments already answer. Labeled options
only. Cap four.

- Product photo missing: upload now, or describe category / color / distinctive shape?
- Count: `1` / `3` / `5`?
- Lane: `Clean studio` / `Lifestyle` / `On a model` / `Ad video` / `Cinematic`?
- Where it runs: `Shopify` / `Instagram` / `Pinterest` / `Paid social` / `YouTube`?
