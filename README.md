# Python-Animation

A from-scratch Python pixel-animation project for **一段文字，一段路 / A Small Chapter for the Ride**.

This repository deliberately does **not** animate an existing GIF. The scene is generated as native pixel art in Python: the train carriage is stable, while mountains, city buildings, trackside objects, reflections, lighting, and an original passenger sprite are independently animated.

## v0.1 — Pixel Train Engine

Current prototype includes:

- 320×180 native pixel canvas
- strict fixed palette
- nearest-neighbour upscale only
- layered parallax scenery
- dusk ↔ night lighting cycle
- stars and city window lights
- fast trackside poles / lamps / signals
- stable train interior and seat
- original passenger sprite
- blinking, breathing, and one-pixel hair motion
- moving window reflections and glints
- deterministic looping
- GIF and MP4 export
- automated tests on GitHub Actions

## Run it

```bash
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell
# .venv\\Scripts\\Activate.ps1

pip install -e .
pixel-train --output output/pixel_train.mp4
```

Render a shorter GIF preview:

```bash
pixel-train --output output/preview.gif --duration 6 --scale 3
```

## How the scene is built

```text
SKY / STARS
      ↓
FAR MOUNTAINS          slow
      ↓
NEAR MOUNTAINS         medium
      ↓
CITY                    faster
      ↓
TRACK / POLES           fastest
      ↓
TRAIN INTERIOR          anchored
      ↓
PASSENGER               micro-animation
      ↓
WINDOW REFLECTIONS      independent
```

See [`docs/architecture.md`](docs/architecture.md) for the renderer rules and next milestones.

## Project direction

The engine is intended to become the reusable visual system behind individual episodes. Later scene configs can control route, weather, time of day, tunnels, passing trains, stations, and narration-triggered visual events without rebuilding the animation from scratch.
