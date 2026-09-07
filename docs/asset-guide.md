# v0.4 asset guide

The v0.4 compositor is designed so procedural layers can be replaced with authored PNG assets one by one.

## Required source assets

### carriage
- `ceiling.png`
- `window_frames.png`
- `side_panels.png`
- `handles.png`
- `seat.png`
- `floor.png`
- `props.png`

### character
- `hair_back.png`
- `body.png`
- `clothes.png`
- `face_open.png`
- `face_blink.png`
- `hair_front.png`
- `hands.png`
- `legs.png`

### bunny
- `base.png`
- `blink.png`

### world
- `sky.png`
- `clouds_far.png`
- `mountains_far.png`
- `mountains_near.png`
- `city_far.png`
- `city_near.png`
- `trackside.png`

### effects
- `glass_reflections.png`
- `window_glow.png`
- `sparkles.png`

## Pixel rules

- RGBA PNG
- no anti-aliasing
- hard-edged alpha only unless the effect layer explicitly needs translucency
- coordinates authored against the 2560×1440 native canvas
- do not pre-scale art
- keep source layers separate so Python can animate them independently
