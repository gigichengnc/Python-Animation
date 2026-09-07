from __future__ import annotations

import math
import random

from PIL import Image, ImageDraw

from .compositor import Compositor
from .config import ProductionConfig
from .layers import Layer
from .palette import PALETTE as C


def mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


class ProductionTrainScene:
    """v0.4 high-resolution scene architecture.

    This milestone deliberately separates the frame into cached / reusable
    surfaces.  Procedural factories are placeholders for future PNG pixel-art
    assets, but they already obey the final production layer boundaries.
    """

    def __init__(self, config: ProductionConfig | None = None):
        self.config = config or ProductionConfig()
        self.compositor = Compositor(self.config.native_size)
        self.rng = random.Random(40)
        self._stars = [
            (self.rng.randrange(80, 2480), self.rng.randrange(80, 780), self.rng.choice((2, 2, 3, 4)))
            for _ in range(210)
        ]
        self.layers = self._build_layers()

    def _build_layers(self) -> list[Layer]:
        return [
            Layer("sky", 0, frame_factory=self._sky),
            Layer("far_clouds", 10, frame_factory=self._far_clouds),
            Layer("far_mountains", 20, frame_factory=lambda p: self._mountains(p, speed=0.08, near=False)),
            Layer("near_mountains", 30, frame_factory=lambda p: self._mountains(p, speed=0.17, near=True)),
            Layer("far_city", 40, frame_factory=lambda p: self._city(p, speed=0.34, near=False)),
            Layer("near_city", 50, frame_factory=lambda p: self._city(p, speed=0.55, near=True)),
            Layer("trackside", 60, frame_factory=self._trackside),
            Layer("carriage", 100, static_surface=self._carriage()),
            Layer("bunny", 110, frame_factory=self._bunny),
            Layer("passenger", 120, frame_factory=self._passenger),
            Layer("glass", 140, frame_factory=self._glass),
        ]

    def render_frame(self, frame_index: int, total_frames: int | None = None) -> Image.Image:
        if total_frames is None:
            total_frames = self.config.preview_frames
        phase = (frame_index % total_frames) / total_frames
        return self.compositor.compose(self.layers, phase)

    def render_still(self, phase: float = 0.12) -> Image.Image:
        return self.compositor.compose(self.layers, phase)

    def _transparent(self):
        return Image.new("RGBA", self.config.native_size, (0, 0, 0, 0))

    def _sky(self, phase):
        img = self._transparent()
        d = ImageDraw.Draw(img)
        night = 0.5 - 0.5 * math.cos(phase * math.tau)
        top = mix(C["sky_top"], C["night"], 0.72 * night)
        mid = mix(C["sky_mid"], C["night"], 0.44 * night)
        low = mix(C["sky_low"], C["sky_mid"], 0.40 * night)
        for y in range(0, 1010, 4):
            t = y / 1010
            col = mix(top, mid, t / 0.58) if t < 0.58 else mix(mid, low, (t - 0.58) / 0.42)
            d.rectangle((0, y, 2559, y + 3), fill=(*col, 255))

        if night > 0.25:
            star = mix(C["sky_mid"], C["white"], 0.65)
            for x, y, size in self._stars:
                d.rectangle((x, y, x + size, y + size), fill=(*star, 255))

        sun = mix(C["sky_low"], C["lamp"], 0.84)
        d.rectangle((1268, 730, 1292, 754), fill=(*sun, 255))
        d.rectangle((1248, 740, 1312, 744), fill=(*mix(sun, C["white"], 0.22), 255))
        d.rectangle((1278, 710, 1282, 774), fill=(*mix(sun, C["white"], 0.22), 255))
        return img

    def _far_clouds(self, phase):
        img = self._transparent()
        d = ImageDraw.Draw(img)
        shift = round(phase * 540)
        clouds = ((140, 290, 300), (610, 410, 220), (1120, 250, 360), (1760, 390, 260), (2220, 300, 330))
        for x, y, w in clouds:
            sx = (x - shift) % 2840 - 140
            col = (*mix(C["sky_mid"], C["white"], 0.14), 210)
            d.rectangle((sx, y, sx + w, y + 13), fill=col)
            d.rectangle((sx + 42, y - 14, sx + w - 44, y), fill=col)
        return img

    def _mountains(self, phase, speed, near):
        img = self._transparent()
        d = ImageDraw.Draw(img)
        world = 3100 if near else 3600
        shift = round(phase * world * (3 if near else 1))
        baseline = 1040 if near else 970
        step = 190 if near else 245
        amp = 250 if near else 190
        color = C["mountain_near"] if near else C["mountain_far"]
        pts = [(0, 1440)]
        for i in range(-8, 28):
            x = i * step - shift
            peak = amp - ((i * 37) % 74)
            pts.extend(((x, baseline), (x + step // 2, baseline - peak), (x + step, baseline)))
        pts.append((2560, 1440))
        d.polygon(pts, fill=(*color, 255))
        return img

    def _city(self, phase, speed, near):
        img = self._transparent()
        d = ImageDraw.Draw(img)
        world = 3300 if near else 3900
        shift = round(phase * world * (5 if near else 3))
        ground = 1130 if near else 1080
        rng = random.Random(13 if near else 9)
        x = 0
        buildings = []
        while x < world:
            w = rng.randrange(55, 130) if near else rng.randrange(35, 90)
            h = rng.randrange(150, 410) if near else rng.randrange(90, 270)
            buildings.append((x, w, h))
            x += w + rng.randrange(20, 48)

        color = C["city_near"] if near else C["city_far"]
        glow = C["window_glow"]
        for bx, bw, bh in buildings:
            sx = (bx - shift) % world - 150
            if sx > 2560 or sx + bw < 0:
                continue
            d.rectangle((sx, ground - bh, sx + bw, ground), fill=(*color, 255))
            for wy in range(ground - bh + 35, ground - 20, 42 if near else 50):
                for wx in range(sx + 24, sx + bw - 15, 38 if near else 44):
                    if ((wx + wy + bx) // 19) % 4 == 0:
                        d.rectangle((wx, wy, wx + (8 if near else 5), wy + (11 if near else 7)), fill=(*glow, 255))
        return img

    def _trackside(self, phase):
        img = self._transparent()
        d = ImageDraw.Draw(img)
        shift = round(phase * 1500 * 7)
        for x in range(-300, 3100, 240):
            sx = (x - shift) % 3100 - 250
            d.rectangle((sx, 300, sx + 14, 1220), fill=(*C["metal"], 255))
            d.rectangle((sx - 70, 410, sx + 90, 422), fill=(*C["metal"], 255))
        return img

    def _carriage(self):
        img = self._transparent()
        d = ImageDraw.Draw(img)
        # ceiling + framing
        d.rectangle((0, 0, 2559, 250), fill=(*C["wall_dark"], 255))
        d.rectangle((0, 250, 2559, 285), fill=(*C["trim"], 255))
        d.rectangle((0, 1015, 2559, 1439), fill=(*C["wall"], 255))

        # side pillars
        d.rectangle((0, 285, 125, 1025), fill=(*C["wall"], 255))
        d.rectangle((545, 285, 670, 1025), fill=(*C["wall"], 255))
        d.rectangle((1890, 285, 2015, 1025), fill=(*C["wall"], 255))
        d.rectangle((2440, 285, 2559, 1025), fill=(*C["wall"], 255))

        # window borders
        for rect in ((125, 330, 545, 970), (670, 295, 1890, 970), (2015, 330, 2440, 970)):
            x1, y1, x2, y2 = rect
            d.rectangle((x1 - 24, y1 - 24, x2 + 24, y2 + 24), outline=(*C["trim"], 255), width=24)
            d.line((x1, y2 + 18, x2, y2 + 18), fill=(*C["ink2"], 255), width=16)

        # route display + handles
        d.rectangle((820, 120, 1750, 175), fill=(*C["ink2"], 255))
        d.rectangle((850, 137, 1720, 151), fill=(*C["metal"], 255))
        for hx in range(860, 1761, 145):
            d.line((hx, 180, hx, 238), fill=(*C["trim"], 255), width=8)
            d.line((hx - 35, 238, hx - 23, 290), fill=(*C["trim"], 255), width=8)
            d.line((hx + 35, 238, hx + 23, 290), fill=(*C["trim"], 255), width=8)
            d.line((hx - 23, 290, hx + 23, 290), fill=(*C["trim"], 255), width=8)

        # seat
        d.rectangle((380, 1005, 2180, 1100), fill=(*C["seat_hi"], 255))
        d.rectangle((380, 1100, 2180, 1310), fill=(*C["seat"], 255))
        d.line((380, 1100, 2180, 1100), fill=(*C["trim"], 255), width=9)
        for sx in range(680, 2180, 300):
            d.line((sx, 1010, sx, 1305), fill=(*C["ink2"], 255), width=8)

        # floor
        d.rectangle((0, 1310, 2559, 1439), fill=(*C["ink"], 255))
        d.rectangle((0, 1320, 2559, 1345), fill=(*C["metal"], 255))
        for x in range(-100, 2700, 130):
            d.line((x, 1350, x + 95, 1439), fill=(*C["ink2"], 255), width=10)

        # red can
        d.rectangle((800, 930, 848, 1003), fill=(*C["red"], 255))
        d.rectangle((812, 937, 840, 949), fill=(*mix(C["red"], C["white"], 0.28), 255))
        return img

    def _bunny(self, phase):
        img = self._transparent()
        d = ImageDraw.Draw(img)
        bob = 7 if math.sin(phase * math.tau * 4) > 0.65 else 0
        x, y = 970, 1030 - bob
        d.rectangle((x + 24, y - 120, x + 50, y - 35), fill=(*C["white"], 255))
        d.rectangle((x + 86, y - 120, x + 112, y - 35), fill=(*C["white"], 255))
        d.rectangle((x, y - 40, x + 135, y + 70), fill=(*C["white"], 255))
        d.rectangle((x + 18, y + 65, x + 118, y + 160), fill=(*C["coat_dark"], 255))
        d.rectangle((x + 43, y + 75, x + 93, y + 118), fill=(*C["red"], 255))
        d.rectangle((x + 34, y - 5, x + 45, y + 8), fill=(*C["ink"], 255))
        d.rectangle((x + 90, y - 5, x + 101, y + 8), fill=(*C["ink"], 255))
        return img

    def _passenger(self, phase):
        img = self._transparent()
        d = ImageDraw.Draw(img)
        # intentionally higher-detail sprite placeholder; this will become PNG assets.
        cx = 1600
        breathe = 8 if math.sin(phase * math.tau * 4) > 0.62 else 0
        sway = 8 if math.sin(phase * math.tau * 3 + 0.6) > 0.35 else 0
        top = 625 - breathe

        # legs / shoes
        d.rectangle((cx - 70, 1125, cx - 35, 1300), fill=(*C["skin"], 255))
        d.rectangle((cx + 38, 1125, cx + 73, 1300), fill=(*C["skin"], 255))
        d.rectangle((cx - 94, 1288, cx - 28, 1325), fill=(*C["shoe"], 255))
        d.rectangle((cx + 28, 1288, cx + 94, 1325), fill=(*C["shoe"], 255))

        # dress + torso
        d.polygon(((cx - 130, 920), (cx + 130, 920), (cx + 190, 1155), (cx - 190, 1155)), fill=(*C["coat"], 255))
        d.rectangle((cx - 92, 815, cx + 92, 1035), fill=(*C["coat_dark"], 255))
        d.rectangle((cx - 66, 830, cx + 66, 1025), fill=(*C["coat"], 255))
        d.rectangle((cx - 32, 840, cx + 32, 1010), fill=(*C["trim"], 255))
        d.rectangle((cx - 52, 825, cx + 52, 855), fill=(*C["white"], 255))
        d.rectangle((cx - 58, 870, cx + 58, 890), fill=(*C["scarf"], 255))

        # face
        face_y = 675 - breathe
        d.rectangle((cx - 75, face_y, cx + 75, face_y + 142), fill=(*C["skin"], 255))
        d.rectangle((cx - 60, face_y + 126, cx + 60, face_y + 154), fill=(*C["skin_shadow"], 255))

        # hair mass + layered locks
        hy = 575 - breathe
        d.rectangle((cx - 145, hy + 25, cx + 145 + sway, hy + 155), fill=(*C["hair_dark"], 255))
        d.rectangle((cx - 175, hy + 105, cx - 115, hy + 310), fill=(*C["hair_dark"], 255))
        d.rectangle((cx + 115 + sway, hy + 100, cx + 180 + sway, hy + 315), fill=(*C["hair_dark"], 255))
        d.rectangle((cx - 120, hy, cx + 110, hy + 90), fill=(*C["hair"], 255))
        for ox in (-95, -40, 15, 70):
            d.rectangle((cx + ox, hy + 52, cx + ox + 28, hy + 130), fill=(*C["hair_mid"], 255))

        # eyes / blink at character cadence
        char_frame = int(phase * self.config.preview_seconds * self.config.character_fps)
        blink = char_frame % 43 in (0, 1)
        eye_y = face_y + 70
        if blink:
            d.line((cx - 48, eye_y, cx - 20, eye_y), fill=(*C["ink"], 255), width=8)
            d.line((cx + 20, eye_y, cx + 48, eye_y), fill=(*C["ink"], 255), width=8)
        else:
            d.rectangle((cx - 50, eye_y - 10, cx - 22, eye_y + 18), fill=(*C["ink"], 255))
            d.rectangle((cx + 22, eye_y - 10, cx + 50, eye_y + 18), fill=(*C["ink"], 255))
            d.rectangle((cx - 38, eye_y - 7, cx - 31, eye_y), fill=(*C["white"], 255))
            d.rectangle((cx + 31, eye_y - 7, cx + 38, eye_y), fill=(*C["white"], 255))

        d.rectangle((cx - 8, face_y + 110, cx + 8, face_y + 118), fill=(*C["scarf"], 255))
        return img

    def _glass(self, phase):
        img = self._transparent()
        d = ImageDraw.Draw(img)
        windows = ((125, 330, 545, 970), (670, 295, 1890, 970), (2015, 330, 2440, 970))
        for i, (x1, y1, x2, y2) in enumerate(windows):
            span = x2 - x1 + 330
            sweep = x1 - 165 + int((phase * span * 2 + i * 210) % span)
            for y in range(y1 + 30, y2 - 30, 7):
                x = sweep + (y - y1) // 8
                if x1 < x < x2:
                    d.rectangle((x, y, x + 10, y + 5), fill=(*C["reflection"], 22))
                    d.rectangle((x + 22, y, x + 28, y + 5), fill=(*C["reflection"], 13))
        return img
