# Cinematic VFX

Recreate or invent a photoreal shot as a planned sequence of stills, then
short videos. GrokBuild has no video-to-video. Do not pretend it does.

Identity, face-lock, size-ref, and prompt blocks: [pipeline.md](pipeline.md).
Tool contract: bundled `imagine`.

## Order

1. **Pack.** Person and/or creature sheets on grey. Expression stills if
   the face must change. `size-ref.png` if two subjects share scale.
2. **Location still.** Generate or pull a frame of the empty place. Check
   light before anything else: direction, color, weather, haze. Reject a
   still whose light will not survive animation.
3. **Beat stills.** One still per beat, seeded from the pack and the
   location. The still is frame 1 of that shot.
4. **Animate.** `image_to_video` from that still. One subject, one motion
   or one camera move. 6s default.
5. **Cut.** Empty-frame holds are cut points. Concatenate with ffmpeg
   stream copy (`imagine`). Continuity: seed the next still from the
   previous shot's last frame.

## When the user brings footage

There is no "swap the actor in this clip" tool.

1. Extract the frame that holds the camera, light, and background.
2. `image_edit` the replacement person or creature into that plate.
   Lock every pixel outside the subject. Match grain, exposure, and
   white balance to the plate.
3. `image_to_video` from the edited still if the beat needs motion.

If the **action is not in the source** (no jump, no fly-out, no landing),
do not force a swap. Shoot it as image-to-video from a location still.
Write a short empty hold after the exit so the next shot has a cut point.

## Physics

Write the motion the way a body actually moves. One sentence.

- A person leaves a cliff by stepping off or by pushing into a dive.
  Not a stiff slide at constant speed with frozen cloth.
- Cloth, hair, and loose gear react to the same acceleration as the body.
- A large creature has weight: wingbeat drives a body wave, tail follows,
  legs hang. Not a rigid toy dragged through the air.
- Water, spray, and dust belong to the air around the subject unless the
  brief soaks them. Wet vs dry is a lock.
- A near miss past camera can include a short shake and droplets on the
  lens. Those are the last beat, not the whole shot.

## Acting

For a face with no video reference, describe the doing: swallow, breath
fog, jaw, eye-line, fingers, a step that starts before the run. The
location still owns the light; the prompt owns the performance.

## Shot budget

Busy geometry, tiny logos, and heavy reflections warp in video. Keep the
subject simple and move the camera, or split into tighter shots. Do not
cram a jump, a catch, and a fly-through into one 6s generate.

`reference_to_video` only when the user asks or the beat cannot be composed
as one still (several distinct refs that must appear together). Prefer
compose with `image_edit`, then `image_to_video`.
