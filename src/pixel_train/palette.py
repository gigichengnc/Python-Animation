"""Fixed colour palette used by the pixel renderer.

Keeping the palette intentionally small is part of the visual style: every
frame is drawn at native pixel resolution with no anti-aliasing.
"""

PALETTE = {
    "ink": (25, 24, 46),
    "ink2": (38, 37, 66),
    "wall_dark": (63, 62, 90),
    "wall": (82, 80, 112),
    "metal": (111, 108, 137),
    "trim": (151, 145, 176),
    "seat": (57, 55, 82),
    "seat_hi": (72, 69, 101),
    "sky_top": (65, 68, 116),
    "sky_mid": (126, 116, 160),
    "sky_low": (225, 177, 168),
    "night": (35, 38, 72),
    "mountain_far": (87, 80, 124),
    "mountain_near": (67, 62, 98),
    "city_far": (92, 83, 121),
    "city_near": (69, 64, 97),
    "window_glow": (246, 220, 170),
    "lamp": (255, 236, 190),
    "reflection": (235, 225, 244),
    "skin": (238, 214, 207),
    "hair": (154, 137, 187),
    "hair_dark": (112, 99, 151),
    "coat": (94, 133, 177),
    "coat_dark": (64, 91, 133),
    "scarf": (220, 185, 199),
    "shoe": (47, 47, 70),
    "red": (177, 70, 78),
    "white": (247, 239, 233),
}
