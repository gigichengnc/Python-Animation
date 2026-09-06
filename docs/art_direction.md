# v0.2 art direction

The engine already proved that Python can generate the motion. v0.2 shifts the priority to **cinematic pixel-art quality**.

## Composition

- The large center window is the visual anchor.
- The passenger sits right-of-center so the horizon and sunset remain readable.
- The small companion sprite balances the lower center-left.
- Structural train elements frame the world instead of competing with it.

## Depth

The outside world is separated into six speed bands:

1. clouds
2. far mountains
3. near mountains
4. far city
5. near city
6. trackside poles / lamps / gantries

Each band advances at a different integer loop rate so motion reads as actual train travel rather than one sliding background.

## Pixel discipline

- 320×180 native canvas
- no anti-aliasing
- discrete one-pixel micro-movements
- strict project palette
- nearest-neighbour upscale only
- seeded deterministic world generation

## Character direction

The passenger is original artwork rather than a copy of the visual reference. The sprite uses silhouette, block shading, and a very small animation vocabulary:

- blink
- one-pixel breathing lift
- one-pixel hair sway

The goal is quiet presence rather than attention-grabbing character animation.

## v0.2 review gate

Before adding tunnel, station, weather, or narration-triggered events, the base 10–15 second loop should already feel pleasant enough to leave running behind spoken narration.
