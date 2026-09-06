# Pixel Train architecture

The renderer is intentionally **not** a filtered source GIF. Every frame is generated from code at native pixel resolution.

Layer order:

1. dusk / night sky
2. stars
3. far mountains
4. near mountains
5. city skyline
6. tracks and fast foreground poles
7. train interior and window frames
8. original passenger sprite
9. independent glass reflections / glints

Each moving world layer uses a deterministic loop phase. The train interior is anchored to the camera, so the scene reads as a moving train instead of a moving picture.

## Pixel rules

- Draw at 320×180.
- No anti-aliasing.
- Use the project palette only.
- Upscale with nearest-neighbour interpolation.
- Motion is discrete at native resolution.
- Random scene generation is seeded and deterministic.

## Next milestones

- sprite-sheet character animation
- tunnel event and station lighting timeline
- route / weather scene configuration
- narration event hooks
- 30–60 second production loops
