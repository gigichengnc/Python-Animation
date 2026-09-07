from __future__ import annotations

from dataclasses import dataclass
import math
import random

from PIL import Image, ImageDraw

from .palette import PALETTE as C


def _mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


@dataclass(frozen=True)
class RenderConfig:
    width: int = 480
    height: int = 270
    fps: int = 12
    duration: float = 12.0
    scale: int = 4
    seed: int = 7

    @property
    def frame_count(self) -> int:
        return max(1, round(self.fps * self.duration))


class PixelTrainScene:
    """480×270 native pixel-art train scene for v0.3."""

    MAIN_WINDOW = (111, 39, 371, 158)
    SIDE_WINDOWS = ((14, 47, 91, 151), (389, 47, 466, 151))
    ALL_WINDOWS = (MAIN_WINDOW,) + SIDE_WINDOWS

    def __init__(self, config: RenderConfig | None = None):
        self.config = config or RenderConfig()
        self.rng = random.Random(self.config.seed)
        self._stars = self._make_stars(150)
        self._far_city = self._make_city(1280, 8, 20, 12, 40)
        self._near_city = self._make_city(1040, 13, 31, 22, 65)
        self._foreground = self._make_foreground(1100)

    def _phase(self, frame_index):
        return (frame_index % self.config.frame_count) / self.config.frame_count

    def _make_stars(self, count):
        return [
            (
                self.rng.randrange(5, 475),
                self.rng.randrange(8, 106),
                self.rng.choice((1, 1, 1, 1, 2)),
            )
            for _ in range(count)
        ]

    def _make_city(self, world_width, min_w, max_w, min_h, max_h):
        out, x = [], 0
        while x < world_width:
            bw = self.rng.randrange(min_w, max_w + 1)
            bh = self.rng.randrange(min_h, max_h + 1)
            roof = self.rng.choice(("flat", "flat", "step", "antenna", "antenna"))
            light_phase = self.rng.randrange(0, 11)
            out.append((x, bw, bh, roof, light_phase))
            x += bw + self.rng.randrange(3, 9)
        return out

    def _make_foreground(self, world_width):
        out, x = [], 0
        while x < world_width:
            out.append((x, self.rng.choice(("pole", "pole", "pole", "lamp", "signal", "gantry"))))
            x += self.rng.randrange(34, 72)
        return out

    def render_frame(self, frame_index: int) -> Image.Image:
        phase = self._phase(frame_index)
        img = Image.new("RGB", (self.config.width, self.config.height), C["ink"])
        self._draw_world(img, phase)
        self._draw_carriage(img, phase)
        self._draw_bunny(img, phase)
        self._draw_passenger(img, phase)
        self._draw_reflections(img, phase)
        self._draw_glints(img, phase)
        return img

    def render_scaled_frame(self, frame_index: int) -> Image.Image:
        frame = self.render_frame(frame_index)
        return frame.resize(
            (self.config.width * self.config.scale, self.config.height * self.config.scale),
            Image.Resampling.NEAREST,
        )

    def _draw_world(self, img, phase):
        d = ImageDraw.Draw(img)
        night = 0.5 - 0.5 * math.cos(phase * math.tau)
        top = _mix(C["sky_top"], C["night"], 0.72 * night)
        mid = _mix(C["sky_mid"], C["night"], 0.44 * night)
        low = _mix(C["sky_low"], C["sky_mid"], 0.40 * night)

        horizon = 165
        for y in range(horizon):
            t = y / (horizon - 1)
            col = _mix(top, mid, t / 0.58) if t < 0.58 else _mix(mid, low, (t - 0.58) / 0.42)
            d.line((0, y, 479, y), fill=col)

        sun_strength = max(0.0, 1.0 - night * 1.35)
        if sun_strength > 0.02:
            sx, sy = 243, 132
            sun = _mix(C["sky_low"], C["lamp"], 0.82)
            d.rectangle((sx - 6, sy - 6, sx + 6, sy + 6), fill=sun)
            d.rectangle((sx - 11, sy - 2, sx + 11, sy + 2), fill=_mix(sun, C["white"], 0.22))
            d.rectangle((sx - 2, sy - 11, sx + 2, sy + 11), fill=_mix(sun, C["white"], 0.20))

        star_strength = max(0.0, (night - 0.20) / 0.80)
        if star_strength > 0:
            col = _mix(C["sky_mid"], C["white"], 0.35 + 0.65 * star_strength)
            for x, y, s in self._stars:
                d.rectangle((x, y, x + s - 1, y + s - 1), fill=col)

        self._draw_clouds(d, phase, mid)
        self._mountains(d, phase, 170, C["mountain_far"], 780, 1, 42, 48)
        self._mountains(d, phase, 181, C["mountain_near"], 860, 2, 50, 42)
        self._city_layer(d, phase, self._far_city, 1280, 3, 191, night, False)
        self._city_layer(d, phase, self._near_city, 1040, 4, 202, night, True)
        self._track_bed(d, phase)
        self._fast_foreground(d, phase)

    def _draw_clouds(self, d, phase, sky_mid):
        world = 680
        offset = int((phase * world) % world)
        clouds = ((40, 48, 64), (160, 73, 46), (275, 52, 56), (404, 84, 42), (555, 58, 70))
        for cx, cy, cw in clouds:
            sx = (cx - offset) % world - 80
            col = _mix(sky_mid, C["white"], 0.12)
            d.rectangle((sx, cy, sx + cw, cy + 3), fill=col)
            d.rectangle((sx + 12, cy - 3, sx + cw - 12, cy), fill=col)
            if cw > 55:
                d.rectangle((sx + 23, cy - 6, sx + cw - 24, cy - 3), fill=col)

    def _mountains(self, d, phase, baseline, color, world, cycles, amp, step):
        offset = int((phase * world * cycles) % world)
        pts = [(0, 270)]
        for i in range(-5, 480 // step + 10):
            x = i * step - offset
            peak = amp - ((i * 17 + cycles * 9) % 18)
            shoulder = max(8, peak // 3)
            pts.extend(
                (
                    (x, baseline),
                    (x + step // 4, baseline - shoulder),
                    (x + step // 2, baseline - peak),
                    (x + 3 * step // 4, baseline - shoulder - 3),
                    (x + step, baseline),
                )
            )
        pts.append((480, 270))
        d.polygon(pts, fill=color)

    def _city_layer(self, d, phase, buildings, world, cycles, ground, night, near):
        offset = int((phase * world * cycles) % world)
        for x, bw, bh, roof, light_phase in buildings:
            sx = (x - offset) % world - 38
            if sx > 480 or sx + bw < 0:
                continue
            base = C["city_near"] if near else C["city_far"]
            if near and (x // 29) % 2:
                base = _mix(base, C["ink2"], 0.14)
            d.rectangle((sx, ground - bh, sx + bw, ground), fill=base)
            if roof == "antenna":
                d.line((sx + bw // 2, ground - bh - 10, sx + bw // 2, ground - bh), fill=base)
                d.point((sx + bw // 2, ground - bh - 11), fill=C["red"])
            elif roof == "step" and bw >= 14:
                d.rectangle((sx + 4, ground - bh - 5, sx + bw - 5, ground - bh), fill=base)

            glow = _mix(C["sky_low"], C["window_glow"], 0.55 + 0.45 * night)
            if bh > 23:
                for wy in range(ground - bh + 6, ground - 5, 9):
                    for wx in range(sx + 4, sx + bw - 3, 8):
                        if ((wx + wy + light_phase) // 4) % 5 == 0:
                            d.rectangle((wx, wy, wx + (1 if near else 0), wy + 1), fill=glow)

    def _track_bed(self, d, phase):
        d.rectangle((0, 202, 479, 269), fill=C["ink2"])
        d.line((0, 211, 479, 211), fill=C["metal"], width=3)
        d.line((0, 235, 479, 235), fill=C["wall_dark"], width=3)
        spacing = 29
        shift = int((phase * spacing * 12) % spacing)
        for x in range(-spacing, 480 + spacing, spacing):
            sx = x - shift
            d.polygon(((sx, 219), (sx + 15, 219), (sx + 12, 225), (sx - 3, 225)), fill=C["wall_dark"])

    def _fast_foreground(self, d, phase):
        world = 1100
        offset = int((phase * world * 7) % world)
        for x, kind in self._foreground:
            sx = (x - offset) % world - 36
            if not (-40 <= sx <= 520):
                continue
            if kind == "pole":
                d.rectangle((sx, 21, sx + 3, 207), fill=C["metal"])
                d.rectangle((sx - 14, 43, sx + 17, 46), fill=C["metal"])
                d.rectangle((sx + 1, 21, sx + 2, 28), fill=C["reflection"])
            elif kind == "lamp":
                d.rectangle((sx, 103, sx + 3, 207), fill=C["wall_dark"])
                d.rectangle((sx - 6, 94, sx + 9, 103), fill=C["lamp"])
                d.rectangle((sx - 11, 97, sx + 14, 99), fill=_mix(C["lamp"], C["white"], 0.22))
            elif kind == "signal":
                d.rectangle((sx, 121, sx + 4, 207), fill=C["wall_dark"])
                d.rectangle((sx - 5, 107, sx + 9, 121), fill=C["ink"])
                d.rectangle((sx - 1, 110, sx + 4, 115), fill=C["red"])
            else:
                d.rectangle((sx, 44, sx + 3, 207), fill=C["metal"])
                d.rectangle((sx - 24, 66, sx + 27, 69), fill=C["metal"])
                d.rectangle((sx - 19, 70, sx - 16, 84), fill=C["metal"])
                d.rectangle((sx + 20, 70, sx + 23, 84), fill=C["metal"])

    def _draw_carriage(self, img, phase):
        d = ImageDraw.Draw(img)

        d.rectangle((0, 0, 479, 35), fill=C["wall_dark"])
        d.rectangle((0, 35, 479, 39), fill=C["trim"])
        d.rectangle((0, 10, 479, 15), fill=C["metal"])
        d.rectangle((0, 16, 479, 22), fill=C["wall"])
        for x in range(6, 480, 54):
            d.rectangle((x, 2, x + 32, 6), fill=C["ink2"])
            d.rectangle((x + 4, 7, x + 28, 9), fill=C["metal"])

        d.rectangle((0, 39, 13, 159), fill=C["wall"])
        d.rectangle((92, 39, 110, 159), fill=C["wall"])
        d.rectangle((372, 39, 388, 159), fill=C["wall"])
        d.rectangle((467, 39, 479, 159), fill=C["wall"])
        d.rectangle((0, 159, 479, 269), fill=C["wall"])

        for x1, y1, x2, y2 in self.ALL_WINDOWS:
            d.rectangle((x1 - 4, y1 - 4, x2 + 4, y2 + 4), outline=C["trim"], width=4)
            d.line((x1 - 2, y2 + 3, x2 + 2, y2 + 3), fill=C["ink2"], width=3)
            d.line((x1 - 1, y1 - 1, x2 + 1, y1 - 1), fill=C["wall_dark"])

        for x in (46, 434):
            d.line((x, 39, x, 161), fill=C["ink2"], width=2)
            d.rectangle((x - 2, 84, x + 2, 111), fill=C["metal"])
            d.rectangle((x - 1, 94, x + 1, 101), fill=C["trim"])

        d.rectangle((105, 22, 378, 25), fill=C["metal"])
        for hx in (128, 168, 208, 248, 288, 328, 368):
            d.line((hx, 25, hx, 31), fill=C["trim"])
            d.line((hx - 7, 32, hx - 5, 41), fill=C["trim"])
            d.line((hx + 7, 32, hx + 5, 41), fill=C["trim"])
            d.line((hx - 5, 41, hx + 5, 41), fill=C["trim"])
            d.line((hx - 7, 32, hx + 7, 32), fill=C["trim"])
            d.point((hx, 42), fill=C["white"])

        d.rectangle((136, 27, 346, 35), fill=C["ink2"])
        d.rectangle((142, 29, 340, 31), fill=C["metal"])
        for i, x in enumerate(range(154, 334, 20)):
            col = C["lamp"] if i == int((phase * 9) % 9) else C["wall"]
            d.rectangle((x, 32, x + 2, 33), fill=col)

        d.rectangle((73, 166, 406, 182), fill=C["seat_hi"])
        d.line((73, 166, 406, 166), fill=C["trim"], width=2)
        d.rectangle((73, 183, 406, 224), fill=C["seat"])
        for sx in (128, 183, 238, 293, 348):
            d.line((sx, 167, sx, 223), fill=C["ink2"], width=2)
            d.line((sx + 1, 168, sx + 1, 221), fill=_mix(C["seat"], C["trim"], 0.12))

        d.rectangle((65, 225, 414, 233), fill=C["ink"])
        d.rectangle((0, 234, 479, 269), fill=C["ink"])
        d.rectangle((0, 235, 479, 239), fill=C["metal"])
        d.rectangle((0, 240, 479, 245), fill=C["wall_dark"])
        d.rectangle((0, 250, 479, 269), fill=C["ink2"])
        for x in range(0, 480, 24):
            d.line((x, 251, x + 16, 269), fill=C["ink"])

        d.rectangle((160, 150, 169, 165), fill=C["red"])
        d.rectangle((162, 151, 168, 154), fill=_mix(C["red"], C["white"], 0.30))
        d.rectangle((164, 156, 167, 158), fill=C["white"])

        d.rectangle((398, 188, 420, 219), fill=C["hair_dark"])
        d.rectangle((402, 183, 416, 190), fill=C["trim"])
        d.rectangle((406, 186, 412, 188), fill=C["lamp"])

    def _draw_bunny(self, img, phase):
        d = ImageDraw.Draw(img)
        x, y = 189, 168
        bob = 1 if math.sin(phase * math.tau * 4 + 0.8) > 0.65 else 0

        d.rectangle((x + 5, y - 25 - bob, x + 10, y - 7 - bob), fill=C["white"])
        d.rectangle((x + 18, y - 25 - bob, x + 23, y - 7 - bob), fill=C["white"])
        d.rectangle((x + 7, y - 22 - bob, x + 8, y - 11 - bob), fill=C["scarf"])
        d.rectangle((x + 20, y - 22 - bob, x + 21, y - 11 - bob), fill=C["scarf"])
        d.rectangle((x, y - 8 - bob, x + 28, y + 13 - bob), fill=C["white"])
        d.rectangle((x + 2, y + 10 - bob, x + 26, y + 16 - bob), fill=_mix(C["white"], C["trim"], 0.25))
        d.rectangle((x + 4, y + 17 - bob, x + 24, y + 36 - bob), fill=C["coat_dark"])
        d.rectangle((x + 9, y + 18 - bob, x + 19, y + 27 - bob), fill=C["red"])
        d.rectangle((x + 6, y + 37 - bob, x + 12, y + 42 - bob), fill=C["scarf"])
        d.rectangle((x + 17, y + 37 - bob, x + 23, y + 42 - bob), fill=C["scarf"])
        d.rectangle((x + 7, y + 1 - bob, x + 9, y + 3 - bob), fill=C["ink"])
        d.rectangle((x + 19, y + 1 - bob, x + 21, y + 3 - bob), fill=C["ink"])
        d.point((x + 14, y + 8 - bob), fill=C["scarf"])

    def _draw_passenger(self, img, phase):
        d = ImageDraw.Draw(img)
        cx = 305
        breath = 1 if math.sin(phase * math.tau * 4) > 0.62 else 0
        sway = 1 if math.sin(phase * math.tau * 3 + 0.6) > 0.35 else 0
        f = phase * self.config.frame_count
        blink = any(abs(f - b) < 1.25 for b in (17, 18, 59, 101, 102, 136))

        d.rectangle((cx - 13, 205, cx - 7, 231), fill=C["skin"])
        d.rectangle((cx + 8, 205, cx + 14, 231), fill=C["skin"])
        d.rectangle((cx - 18, 230, cx - 6, 236), fill=C["shoe"])
        d.rectangle((cx + 7, 230, cx + 19, 236), fill=C["shoe"])
        d.line((cx - 16, 232, cx - 8, 232), fill=C["trim"])
        d.line((cx + 9, 232, cx + 17, 232), fill=C["trim"])

        body_top = 163 - breath
        d.polygon(((cx - 25, body_top + 25), (cx + 25, body_top + 25), (cx + 31, 209), (cx - 31, 209)), fill=C["coat"])
        d.polygon(((cx - 25, body_top + 28), (cx - 9, 209), (cx - 2, 209), (cx - 13, body_top + 28)), fill=C["coat_dark"])
        d.polygon(((cx + 13, body_top + 28), (cx + 2, 209), (cx + 9, 209), (cx + 25, body_top + 28)), fill=C["coat_dark"])
        d.line((cx - 30, 208, cx + 30, 208), fill=C["trim"], width=2)
        for rx in (-22, -9, 4, 17):
            d.rectangle((cx + rx, 205, cx + rx + 7, 210), fill=C["white"])

        d.rectangle((cx - 18, body_top, cx + 18, body_top + 34), fill=C["coat_dark"])
        d.rectangle((cx - 12, body_top + 3, cx + 12, body_top + 31), fill=C["coat"])
        d.rectangle((cx - 7, body_top + 2, cx + 7, body_top + 7), fill=C["white"])
        d.rectangle((cx - 8, body_top + 8, cx + 8, body_top + 11), fill=C["scarf"])
        d.rectangle((cx - 3, body_top + 10, cx + 3, body_top + 30), fill=C["trim"])
        d.rectangle((cx - 1, body_top + 13, cx + 1, body_top + 15), fill=C["gold"])
        d.rectangle((cx - 1, body_top + 21, cx + 1, body_top + 23), fill=C["gold"])

        d.polygon(((cx - 18, body_top + 5), (cx - 27, body_top + 16), (cx - 24, body_top + 37), (cx - 18, body_top + 34)), fill=C["coat"])
        d.polygon(((cx + 18, body_top + 5), (cx + 27, body_top + 16), (cx + 24, body_top + 37), (cx + 18, body_top + 34)), fill=C["coat"])
        d.rectangle((cx - 26, body_top + 36, cx - 22, body_top + 40), fill=C["skin"])
        d.rectangle((cx + 22, body_top + 36, cx + 26, body_top + 40), fill=C["skin"])

        d.rectangle((cx - 5, 149 - breath, cx + 5, 158 - breath), fill=C["skin"])
        face_top = 128 - breath
        d.rectangle((cx - 14, face_top, cx + 14, face_top + 24), fill=C["skin"])
        d.rectangle((cx - 11, face_top + 22, cx + 11, face_top + 27), fill=C["skin_shadow"])
        d.rectangle((cx - 8, face_top + 20, cx + 8, face_top + 24), fill=C["skin"])

        ht = 112 - breath
        d.rectangle((cx - 23, ht + 7, cx + 23 + sway, ht + 27), fill=C["hair_dark"])
        d.rectangle((cx - 27, ht + 18, cx - 18, ht + 52), fill=C["hair_dark"])
        d.rectangle((cx + 18 + sway, ht + 17, cx + 28 + sway, ht + 53), fill=C["hair_dark"])
        d.rectangle((cx - 20, ht + 1, cx + 18, ht + 15), fill=C["hair"])
        d.rectangle((cx - 24, ht + 8, cx - 16, ht + 24), fill=C["hair"])
        d.rectangle((cx + 13, ht + 7, cx + 24 + sway, ht + 24), fill=C["hair"])
        d.rectangle((cx - 14, ht + 7, cx - 9, ht + 17), fill=C["hair_mid"])
        d.rectangle((cx - 4, ht + 5, cx + 2, ht + 15), fill=C["hair_mid"])
        d.rectangle((cx + 7, ht + 7, cx + 12, ht + 17), fill=C["hair_mid"])
        d.line((cx - 14, ht + 3, cx + 5, ht + 3), fill=_mix(C["hair"], C["white"], 0.18))
        d.line((cx + 9, ht + 6, cx + 17, ht + 6), fill=_mix(C["hair"], C["white"], 0.12))

        eye_y = face_top + 12
        if blink:
            d.line((cx - 8, eye_y, cx - 4, eye_y), fill=C["ink"])
            d.line((cx + 4, eye_y, cx + 8, eye_y), fill=C["ink"])
        else:
            d.rectangle((cx - 8, eye_y - 1, cx - 5, eye_y + 2), fill=C["ink"])
            d.rectangle((cx + 5, eye_y - 1, cx + 8, eye_y + 2), fill=C["ink"])
            d.point((cx - 6, eye_y - 1), fill=C["white"])
            d.point((cx + 6, eye_y - 1), fill=C["white"])
            d.point((cx - 7, eye_y + 1), fill=C["hair"])
            d.point((cx + 7, eye_y + 1), fill=C["hair"])
        d.point((cx, face_top + 17), fill=C["skin_shadow"])
        d.line((cx - 2, face_top + 20, cx + 2, face_top + 20), fill=C["scarf"])

        for ox, oy in ((-27, 143), (-24, 151), (25, 145), (28, 153)):
            d.rectangle((cx + ox, oy - breath, cx + ox + 4, oy + 5 - breath), fill=C["hair_mid"])
            d.rectangle((cx + ox + 2, oy + 5 - breath, cx + ox + 6, oy + 8 - breath), fill=C["hair_dark"])

    def _draw_reflections(self, img, phase):
        for i, (x1, y1, x2, y2) in enumerate(self.ALL_WINDOWS):
            span = x2 - x1 + 66
            sweep = x1 - 33 + int((phase * span * 2 + i * 29) % span)
            for y in range(y1 + 5, y2 - 5):
                x = sweep + (y - y1) // 10
                if x1 <= x <= x2:
                    for dx, amount in ((0, 0.11), (1, 0.08), (3, 0.05), (6, 0.025)):
                        xx = x + dx
                        if x1 <= xx <= x2:
                            img.putpixel((xx, y), _mix(img.getpixel((xx, y)), C["reflection"], amount))

    def _draw_glints(self, img, phase):
        d = ImageDraw.Draw(img)
        pulse = (phase * 6) % 1.0
        if pulse < 0.16:
            strength = 1 - pulse / 0.16
            gx, gy = 244, 132
            arm = 3 + round(strength * 6)
            col = _mix(C["lamp"], C["white"], 0.35)
            d.line((gx - arm, gy, gx + arm, gy), fill=col)
            d.line((gx, gy - arm, gx, gy + arm), fill=col)
