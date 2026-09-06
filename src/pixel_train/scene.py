from __future__ import annotations

from dataclasses import dataclass
import math
import random

from PIL import Image, ImageDraw

from .palette import PALETTE as C


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


@dataclass(frozen=True)
class RenderConfig:
    width: int = 320
    height: int = 180
    fps: int = 12
    duration: float = 12.0
    scale: int = 4
    seed: int = 7

    @property
    def frame_count(self) -> int:
        return max(1, round(self.fps * self.duration))


class PixelTrainScene:
    """Production-oriented v0.2 pixel train scene.

    Everything is rendered from code at native pixel resolution.
    The carriage is anchored while the world outside uses deterministic,
    looping parallax layers.
    """

    MAIN_WINDOW = (69, 25, 251, 108)
    SIDE_WINDOWS = ((8, 31, 59, 101), (261, 31, 312, 101))
    ALL_WINDOWS = (MAIN_WINDOW,) + SIDE_WINDOWS

    def __init__(self, config: RenderConfig | None = None):
        self.config = config or RenderConfig()
        self.rng = random.Random(self.config.seed)
        self._stars = self._make_stars(92)
        self._city_far = self._make_city(840, 7, 17, 10, 32)
        self._city_near = self._make_city(720, 10, 24, 17, 48)
        self._foreground = self._make_foreground(760)

    def _make_stars(self, count: int):
        return [
            (
                self.rng.randrange(4, self.config.width - 4),
                self.rng.randrange(5, 74),
                self.rng.choice((1, 1, 1, 1, 2)),
            )
            for _ in range(count)
        ]

    def _make_city(self, world_width: int, min_w: int, max_w: int, min_h: int, max_h: int):
        out = []
        x = 0
        while x < world_width:
            bw = self.rng.randrange(min_w, max_w + 1)
            bh = self.rng.randrange(min_h, max_h + 1)
            roof = self.rng.choice(("flat", "flat", "antenna", "step"))
            light_phase = self.rng.randrange(0, 7)
            out.append((x, bw, bh, roof, light_phase))
            x += bw + self.rng.randrange(2, 7)
        return out

    def _make_foreground(self, world_width: int):
        out = []
        x = 0
        while x < world_width:
            kind = self.rng.choice(("pole", "pole", "pole", "lamp", "signal", "gantry"))
            out.append((x, kind))
            x += self.rng.randrange(26, 56)
        return out

    def _phase(self, frame_index: int) -> float:
        return (frame_index % self.config.frame_count) / self.config.frame_count

    def render_frame(self, frame_index: int) -> Image.Image:
        phase = self._phase(frame_index)
        img = Image.new("RGB", (self.config.width, self.config.height), C["ink"])
        self._draw_world(img, phase)
        self._draw_carriage(img, phase)
        self._draw_bunny(img, phase)
        self._draw_passenger(img, phase)
        self._draw_window_reflections(img, phase)
        self._draw_foreground_glints(img, phase)
        return img

    def render_scaled_frame(self, frame_index: int) -> Image.Image:
        frame = self.render_frame(frame_index)
        return frame.resize(
            (self.config.width * self.config.scale, self.config.height * self.config.scale),
            Image.Resampling.NEAREST,
        )

    def _draw_world(self, img: Image.Image, phase: float) -> None:
        d = ImageDraw.Draw(img)
        night = 0.5 - 0.5 * math.cos(phase * math.tau)

        top = _mix(C["sky_top"], C["night"], 0.74 * night)
        mid = _mix(C["sky_mid"], C["night"], 0.44 * night)
        low = _mix(C["sky_low"], C["sky_mid"], 0.42 * night)

        horizon = 105
        for y in range(horizon):
            t = y / max(1, horizon - 1)
            col = _mix(top, mid, t / 0.58) if t < 0.58 else _mix(mid, low, (t - 0.58) / 0.42)
            d.line((0, y, self.config.width, y), fill=col)

        sun_strength = max(0.0, 1.0 - night * 1.35)
        if sun_strength > 0.02:
            sun = _mix(C["sky_low"], C["lamp"], 0.76)
            sx, sy = 160, 86
            d.rectangle((sx - 4, sy - 4, sx + 4, sy + 4), fill=sun)
            d.rectangle((sx - 7, sy - 1, sx + 7, sy + 1), fill=_mix(sun, C["white"], 0.2))
            d.rectangle((sx - 1, sy - 7, sx + 1, sy + 7), fill=_mix(sun, C["white"], 0.18))

        star_strength = max(0.0, (night - 0.22) / 0.78)
        if star_strength:
            col = _mix(C["sky_mid"], C["white"], 0.34 + 0.66 * star_strength)
            for sx, sy, size in self._stars:
                d.rectangle((sx, sy, sx + size - 1, sy + size - 1), fill=col)

        self._draw_clouds(d, phase, mid)
        self._mountain_strip(d, phase, baseline=106, color=C["mountain_far"], world=512, cycles=1, amp=27, step=34)
        self._mountain_strip(d, phase, baseline=117, color=C["mountain_near"], world=576, cycles=2, amp=33, step=30)
        self._draw_city_layer(d, phase, self._city_far, world=840, cycles=3, ground=125, night=night, near=False)
        self._draw_city_layer(d, phase, self._city_near, world=720, cycles=4, ground=132, night=night, near=True)
        self._draw_track_bed(d, phase)
        self._draw_fast_foreground(d, phase)

    def _draw_clouds(self, d: ImageDraw.ImageDraw, phase: float, sky_mid):
        world = 430
        offset = int((phase * world) % world)
        clouds = ((22, 36, 42), (96, 51, 30), (172, 31, 38), (260, 58, 26), (344, 42, 48))
        for cx, cy, cw in clouds:
            sx = (cx - offset) % world - 55
            col = _mix(sky_mid, C["white"], 0.11)
            d.rectangle((sx, cy, sx + cw, cy + 2), fill=col)
            if cw > 32:
                d.rectangle((sx + 8, cy - 2, sx + cw - 9, cy), fill=col)

    def _mountain_strip(self, d, phase, baseline, color, world, cycles, amp, step):
        offset = int((phase * world * cycles) % world)
        points = [(0, self.config.height)]
        for i in range(-4, self.config.width // step + 8):
            world_x = i * step - offset
            peak = amp - ((i * 13 + cycles * 7) % 14)
            shoulder = max(4, peak // 3)
            points.extend(
                (
                    (world_x, baseline),
                    (world_x + step // 4, baseline - shoulder),
                    (world_x + step // 2, baseline - peak),
                    (world_x + (3 * step) // 4, baseline - shoulder - 2),
                    (world_x + step, baseline),
                )
            )
        points.append((self.config.width, self.config.height))
        d.polygon(points, fill=color)

    def _draw_city_layer(self, d, phase, buildings, world, cycles, ground, night, near):
        offset = int((phase * world * cycles) % world)
        for x, bw, bh, roof, light_phase in buildings:
            sx = (x - offset) % world - 28
            if sx > self.config.width or sx + bw < 0:
                continue
            base = C["city_near"] if near else C["city_far"]
            if near and (x // 23) % 2:
                base = _mix(base, C["ink2"], 0.12)
            d.rectangle((sx, ground - bh, sx + bw, ground), fill=base)
            if roof == "antenna":
                d.line((sx + bw // 2, ground - bh - 7, sx + bw // 2, ground - bh), fill=base)
                d.point((sx + bw // 2, ground - bh - 8), fill=C["red"])
            elif roof == "step" and bw >= 12:
                d.rectangle((sx + 3, ground - bh - 4, sx + bw - 4, ground - bh), fill=base)
            if bh >= 18:
                glow = _mix(C["sky_low"], C["window_glow"], 0.55 + 0.45 * night)
                for wy in range(ground - bh + 5, ground - 4, 7):
                    for wx in range(sx + 3, sx + bw - 2, 6):
                        if ((wx + wy + light_phase) // 3) % 5 == 0:
                            d.rectangle((wx, wy, wx + (1 if near else 0), wy + 1), fill=glow)

    def _draw_track_bed(self, d, phase):
        d.rectangle((0, 132, self.config.width, self.config.height), fill=C["ink2"])
        d.line((0, 139, self.config.width, 139), fill=C["metal"], width=2)
        d.line((0, 156, self.config.width, 156), fill=C["wall_dark"], width=2)
        spacing = 22
        shift = int((phase * spacing * 10) % spacing)
        for x in range(-spacing, self.config.width + spacing, spacing):
            sx = x - shift
            d.polygon([(sx, 145), (sx + 10, 145), (sx + 8, 149), (sx - 2, 149)], fill=C["wall_dark"])

    def _draw_fast_foreground(self, d, phase):
        world = 760
        offset = int((phase * world * 7) % world)
        for x, kind in self._foreground:
            sx = (x - offset) % world - 26
            if not (-30 <= sx <= self.config.width + 30):
                continue
            if kind == "pole":
                d.rectangle((sx, 16, sx + 2, 135), fill=C["metal"])
                d.rectangle((sx - 9, 29, sx + 12, 31), fill=C["metal"])
                d.point((sx + 1, 17), fill=C["reflection"])
            elif kind == "lamp":
                d.rectangle((sx, 70, sx + 2, 135), fill=C["wall_dark"])
                d.rectangle((sx - 4, 63, sx + 6, 70), fill=C["lamp"])
                d.rectangle((sx - 7, 65, sx + 9, 67), fill=_mix(C["lamp"], C["white"], 0.25))
            elif kind == "signal":
                d.rectangle((sx, 83, sx + 3, 135), fill=C["wall_dark"])
                d.rectangle((sx - 3, 73, sx + 6, 84), fill=C["ink"])
                d.rectangle((sx - 1, 75, sx + 3, 79), fill=C["red"])
            else:
                d.rectangle((sx, 28, sx + 2, 135), fill=C["metal"])
                d.rectangle((sx - 16, 42, sx + 18, 44), fill=C["metal"])
                d.rectangle((sx - 13, 45, sx - 11, 54), fill=C["metal"])
                d.rectangle((sx + 13, 45, sx + 15, 54), fill=C["metal"])

    def _draw_carriage(self, img: Image.Image, phase: float) -> None:
        d = ImageDraw.Draw(img)
        w, h = self.config.width, self.config.height
        d.rectangle((0, 0, w, 25), fill=C["wall_dark"])
        d.rectangle((0, 105, w, h), fill=C["wall"])
        d.rectangle((0, 21, w, 24), fill=C["trim"])
        d.rectangle((0, 6, w, 10), fill=C["metal"])
        d.rectangle((0, 25, 7, 105), fill=C["wall"])
        d.rectangle((60, 25, 68, 105), fill=C["wall"])
        d.rectangle((252, 25, 260, 105), fill=C["wall"])
        d.rectangle((313, 25, w, 105), fill=C["wall"])

        for x1, y1, x2, y2 in self.ALL_WINDOWS:
            d.rectangle((x1 - 3, y1 - 3, x2 + 3, y2 + 3), outline=C["trim"], width=3)
            d.line((x1 - 1, y2 + 2, x2 + 1, y2 + 2), fill=C["ink2"], width=2)

        d.rectangle((65, 14, 255, 24), fill=C["wall_dark"])
        d.rectangle((66, 15, 254, 17), fill=C["metal"])
        d.rectangle((78, 18, 242, 20), fill=C["wall"])

        for hx in (88, 120, 152, 184, 216):
            d.line((hx, 9, hx, 15), fill=C["trim"])
            d.line((hx - 5, 16, hx - 3, 22), fill=C["trim"])
            d.line((hx + 5, 16, hx + 3, 22), fill=C["trim"])
            d.line((hx - 3, 22, hx + 3, 22), fill=C["trim"])
            d.line((hx - 5, 16, hx + 5, 16), fill=C["trim"])

        for x in (31, 289):
            d.line((x, 26, x, 106), fill=C["ink2"])
            d.rectangle((x - 1, 57, x + 1, 73), fill=C["metal"])

        d.rectangle((48, 108, 272, 120), fill=C["seat_hi"])
        d.rectangle((48, 121, 272, 148), fill=C["seat"])
        d.line((48, 121, 272, 121), fill=C["trim"])
        d.line((48, 148, 272, 148), fill=C["ink"])
        for sx in (92, 136, 180, 224):
            d.line((sx, 109, sx, 147), fill=C["ink2"])
        d.rectangle((42, 149, 278, 154), fill=C["ink"])
        d.rectangle((0, 155, w, h), fill=C["ink"])
        d.rectangle((0, 156, w, 159), fill=C["metal"])
        d.rectangle((0, 160, w, 163), fill=C["wall_dark"])

        d.rectangle((110, 96, 116, 107), fill=C["red"])
        d.rectangle((112, 97, 115, 99), fill=_mix(C["red"], C["white"], 0.35))
        d.point((114, 103), fill=C["white"])

        indicator = int((phase * 18) % 18)
        for i, ix in enumerate((281, 286, 291)):
            col = C["lamp"] if indicator == i else C["wall"]
            d.rectangle((ix, 16, ix + 1, 17), fill=col)

    def _draw_bunny(self, img: Image.Image, phase: float) -> None:
        d = ImageDraw.Draw(img)
        x, y = 148, 111
        bob = 1 if math.sin(phase * math.tau * 4 + 0.8) > 0.68 else 0
        d.rectangle((x + 2, y - 15 - bob, x + 5, y - 4 - bob), fill=C["white"])
        d.rectangle((x + 10, y - 15 - bob, x + 13, y - 4 - bob), fill=C["white"])
        d.rectangle((x + 3, y - 13 - bob, x + 4, y - 7 - bob), fill=C["scarf"])
        d.rectangle((x + 11, y - 13 - bob, x + 12, y - 7 - bob), fill=C["scarf"])
        d.rectangle((x, y - 5 - bob, x + 15, y + 9 - bob), fill=C["white"])
        d.rectangle((x + 2, y + 10 - bob, x + 13, y + 22 - bob), fill=C["coat_dark"])
        d.rectangle((x + 5, y + 11 - bob, x + 10, y + 17 - bob), fill=C["red"])
        d.rectangle((x + 3, y + 23 - bob, x + 6, y + 26 - bob), fill=C["scarf"])
        d.rectangle((x + 10, y + 23 - bob, x + 13, y + 26 - bob), fill=C["scarf"])
        d.point((x + 4, y + 1 - bob), fill=C["ink"])
        d.point((x + 11, y + 1 - bob), fill=C["ink"])
        d.point((x + 8, y + 5 - bob), fill=C["scarf"])

    def _draw_passenger(self, img: Image.Image, phase: float) -> None:
        d = ImageDraw.Draw(img)
        cx = 211
        breath = 1 if math.sin(phase * math.tau * 4) > 0.65 else 0
        sway = 1 if math.sin(phase * math.tau * 3 + 0.6) > 0.38 else 0
        f = phase * self.config.frame_count
        blink = any(abs(f - b) < 1.2 for b in (18, 19, 62, 101, 102, 136))

        d.rectangle((cx - 8, 130, cx - 4, 147), fill=C["skin"])
        d.rectangle((cx + 5, 130, cx + 9, 147), fill=C["skin"])
        d.rectangle((cx - 11, 147, cx - 3, 151), fill=C["shoe"])
        d.rectangle((cx + 4, 147, cx + 12, 151), fill=C["shoe"])
        d.rectangle((cx - 10, 146, cx - 6, 147), fill=C["coat_dark"])
        d.rectangle((cx + 6, 146, cx + 10, 147), fill=C["coat_dark"])

        body_top = 105 - breath
        d.polygon([(cx - 15, body_top + 16), (cx + 15, body_top + 16), (cx + 19, 132), (cx - 19, 132)], fill=C["coat"])
        d.polygon([(cx - 15, body_top + 18), (cx - 6, 132), (cx - 2, 132), (cx - 8, body_top + 18)], fill=C["coat_dark"])
        d.line((cx - 18, 131, cx + 18, 131), fill=C["trim"])
        d.rectangle((cx - 13, body_top, cx + 13, body_top + 21), fill=C["coat_dark"])
        d.rectangle((cx - 8, body_top + 2, cx + 8, body_top + 19), fill=C["coat"])
        d.rectangle((cx - 3, body_top + 3, cx + 3, body_top + 18), fill=C["trim"])
        d.rectangle((cx - 7, body_top + 1, cx + 7, body_top + 4), fill=C["white"])
        d.rectangle((cx - 6, body_top + 5, cx + 6, body_top + 7), fill=C["scarf"])
        d.point((cx, body_top + 8), fill=C["lamp"])
        d.point((cx, body_top + 13), fill=C["lamp"])

        d.polygon([(cx - 14, body_top + 3), (cx - 20, body_top + 11), (cx - 17, body_top + 25), (cx - 13, body_top + 23)], fill=C["coat"])
        d.polygon([(cx + 14, body_top + 3), (cx + 20, body_top + 11), (cx + 17, body_top + 25), (cx + 13, body_top + 23)], fill=C["coat"])
        d.rectangle((cx - 18, body_top + 24, cx - 15, body_top + 27), fill=C["skin"])
        d.rectangle((cx + 15, body_top + 24, cx + 18, body_top + 27), fill=C["skin"])

        d.rectangle((cx - 4, 92 - breath, cx + 4, 99 - breath), fill=C["skin"])
        face_top = 80 - breath
        d.rectangle((cx - 10, face_top, cx + 10, face_top + 17), fill=C["skin"])
        d.rectangle((cx - 9, face_top + 14, cx + 9, face_top + 18), fill=C["skin"])

        hair_top = 72 - breath
        d.rectangle((cx - 15, hair_top + 3, cx + 15 + sway, hair_top + 16), fill=C["hair_dark"])
        d.rectangle((cx - 18, hair_top + 10, cx - 12, hair_top + 31), fill=C["hair_dark"])
        d.rectangle((cx + 12 + sway, hair_top + 9, cx + 19 + sway, hair_top + 32), fill=C["hair_dark"])
        d.rectangle((cx - 13, hair_top, cx + 12, hair_top + 9), fill=C["hair"])
        d.rectangle((cx - 16, hair_top + 5, cx - 10, hair_top + 16), fill=C["hair"])
        d.rectangle((cx + 8, hair_top + 4, cx + 16 + sway, hair_top + 15), fill=C["hair"])
        d.rectangle((cx - 9, hair_top + 6, cx - 6, hair_top + 13), fill=C["hair"])
        d.rectangle((cx - 2, hair_top + 5, cx + 2, hair_top + 11), fill=C["hair"])
        d.rectangle((cx + 5, hair_top + 6, cx + 8, hair_top + 13), fill=C["hair"])

        eye_y = face_top + 8
        if blink:
            d.line((cx - 6, eye_y, cx - 3, eye_y), fill=C["ink"])
            d.line((cx + 3, eye_y, cx + 6, eye_y), fill=C["ink"])
        else:
            d.rectangle((cx - 6, eye_y - 1, cx - 4, eye_y + 1), fill=C["ink"])
            d.rectangle((cx + 4, eye_y - 1, cx + 6, eye_y + 1), fill=C["ink"])
            d.point((cx - 5, eye_y - 1), fill=C["white"])
            d.point((cx + 5, eye_y - 1), fill=C["white"])
        d.point((cx, face_top + 12), fill=C["scarf"])
        d.line((cx - 9, hair_top + 2, cx + 3, hair_top + 2), fill=_mix(C["hair"], C["white"], 0.14))

    def _draw_window_reflections(self, img: Image.Image, phase: float) -> None:
        for i, (x1, y1, x2, y2) in enumerate(self.ALL_WINDOWS):
            span = x2 - x1 + 40
            sweep = x1 - 20 + int((phase * span * 2 + i * 23) % span)
            for y in range(y1 + 4, y2 - 4):
                diag = (y - y1) // 8
                x = sweep + diag
                if x1 <= x <= x2:
                    for dx, amount in ((0, 0.11), (1, 0.08), (3, 0.04)):
                        xx = x + dx
                        if x1 <= xx <= x2:
                            old = img.getpixel((xx, y))
                            img.putpixel((xx, y), _mix(old, C["reflection"], amount))

    def _draw_foreground_glints(self, img: Image.Image, phase: float) -> None:
        d = ImageDraw.Draw(img)
        pulse = (phase * 6.0) % 1.0
        if pulse < 0.18:
            strength = 1.0 - pulse / 0.18
            gx, gy = 162, 88
            arm = 2 + round(strength * 4)
            col = _mix(C["lamp"], C["white"], 0.35)
            d.line((gx - arm, gy, gx + arm, gy), fill=col)
            d.line((gx, gy - arm, gx, gy + arm), fill=col)
