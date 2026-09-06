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
        return round(self.fps * self.duration)


class PixelTrainScene:
    """Original layered pixel-art train scene.

    Motion is frame-driven and deterministic. The outside world loops using
    integer cycle counts, while the train interior remains visually anchored.
    """

    WINDOWS = ((18, 30, 80, 102), (94, 24, 231, 102), (246, 30, 308, 102))

    def __init__(self, config: RenderConfig | None = None):
        self.config = config or RenderConfig()
        self.rng = random.Random(self.config.seed)
        self._stars = self._make_stars(70)
        self._city = self._make_city(620)
        self._foreground = self._make_foreground(620)

    def _make_stars(self, count: int):
        return [
            (self.rng.randrange(8, self.config.width - 8), self.rng.randrange(6, 66), self.rng.choice((1, 1, 1, 2)))
            for _ in range(count)
        ]

    def _make_city(self, world_width: int):
        buildings = []
        x = 0
        while x < world_width:
            w = self.rng.randrange(6, 16)
            h = self.rng.randrange(11, 43)
            roof = self.rng.choice(("flat", "antenna", "step"))
            buildings.append((x, w, h, roof))
            x += w + self.rng.randrange(2, 7)
        return buildings

    def _make_foreground(self, world_width: int):
        items = []
        x = 0
        while x < world_width:
            kind = self.rng.choice(("pole", "pole", "pole", "lamp", "signal"))
            items.append((x, kind))
            x += self.rng.randrange(24, 52)
        return items

    def _phase(self, frame_index: int) -> float:
        return (frame_index % self.config.frame_count) / self.config.frame_count

    def render_frame(self, frame_index: int) -> Image.Image:
        phase = self._phase(frame_index)
        img = Image.new("RGB", (self.config.width, self.config.height), C["ink"])
        self._draw_outside(img, phase)
        self._draw_carriage(img, phase)
        self._draw_passenger(img, phase)
        self._draw_glass_reflection(img, phase)
        return img

    def render_scaled_frame(self, frame_index: int) -> Image.Image:
        frame = self.render_frame(frame_index)
        return frame.resize(
            (self.config.width * self.config.scale, self.config.height * self.config.scale),
            Image.Resampling.NEAREST,
        )

    # ---------- outside world ----------
    def _draw_outside(self, img: Image.Image, phase: float) -> None:
        d = ImageDraw.Draw(img)
        w = self.config.width

        # A seamless dusk -> night -> dusk lighting cycle.
        night_amount = 0.5 - 0.5 * math.cos(phase * math.tau)
        top = _mix(C["sky_top"], C["night"], night_amount * 0.72)
        mid = _mix(C["sky_mid"], C["night"], night_amount * 0.45)
        low = _mix(C["sky_low"], C["sky_mid"], night_amount * 0.45)

        horizon = 104
        for y in range(horizon):
            t = y / max(1, horizon - 1)
            if t < 0.62:
                col = _mix(top, mid, t / 0.62)
            else:
                col = _mix(mid, low, (t - 0.62) / 0.38)
            d.line((0, y, w, y), fill=col)

        # Stars fade in around the middle of the loop.
        star_strength = max(0.0, (night_amount - 0.22) / 0.78)
        if star_strength:
            col = _mix(C["sky_mid"], C["white"], 0.35 + 0.65 * star_strength)
            for sx, sy, size in self._stars:
                d.rectangle((sx, sy, sx + size - 1, sy + size - 1), fill=col)

        self._draw_mountains(d, phase, horizon)
        self._draw_city(d, phase, horizon, night_amount)
        self._draw_tracks(d, phase)

    def _draw_mountains(self, d: ImageDraw.ImageDraw, phase: float, horizon: int) -> None:
        self._mountain_strip(d, phase, horizon + 2, C["mountain_far"], world=384, cycles=1, amp=24, step=32)
        self._mountain_strip(d, phase, horizon + 10, C["mountain_near"], world=448, cycles=2, amp=29, step=28)

    def _mountain_strip(self, d, phase, baseline, color, world, cycles, amp, step):
        offset = int((phase * world * cycles) % world)
        points = [(0, self.config.height)]
        for i in range(-3, self.config.width // step + 6):
            world_x = i * step - offset
            peak = amp - ((i * 11 + cycles * 7) % 13)
            points.extend(((world_x, baseline), (world_x + step // 2, baseline - peak), (world_x + step, baseline)))
        points.append((self.config.width, self.config.height))
        d.polygon(points, fill=color)

    def _draw_city(self, d: ImageDraw.ImageDraw, phase: float, horizon: int, night_amount: float) -> None:
        world = 620
        offset = int((phase * world * 3) % world)
        ground = horizon + 21
        for x, bw, bh, roof in self._city:
            sx = (x - offset) % world - 22
            if sx > self.config.width or sx + bw < 0:
                continue
            col = C["city_far"] if (x // 17) % 2 == 0 else C["city_near"]
            d.rectangle((sx, ground - bh, sx + bw, ground), fill=col)
            if roof == "antenna":
                d.line((sx + bw // 2, ground - bh - 5, sx + bw // 2, ground - bh), fill=col)
            elif roof == "step" and bw >= 10:
                d.rectangle((sx + 2, ground - bh - 3, sx + bw - 3, ground - bh), fill=col)

            if bh >= 18:
                glow = _mix(C["sky_low"], C["window_glow"], 0.6 + night_amount * 0.4)
                for wy in range(ground - bh + 5, ground - 4, 7):
                    for wx in range(sx + 3, sx + bw - 2, 6):
                        if ((wx + wy + x) // 4) % 5 == 0:
                            d.point((wx, wy), fill=glow)

    def _draw_tracks(self, d: ImageDraw.ImageDraw, phase: float) -> None:
        d.rectangle((0, 126, self.config.width, self.config.height), fill=C["ink2"])
        d.line((0, 135, self.config.width, 135), fill=C["metal"], width=2)
        d.line((0, 150, self.config.width, 150), fill=C["wall_dark"], width=2)

        sleeper_spacing = 22
        shift = int((phase * sleeper_spacing * 9) % sleeper_spacing)
        for x in range(-sleeper_spacing, self.config.width + sleeper_spacing, sleeper_spacing):
            sx = x - shift
            d.rectangle((sx, 139, sx + 8, 142), fill=C["wall_dark"])

        world = 620
        offset = int((phase * world * 6) % world)
        for x, kind in self._foreground:
            sx = (x - offset) % world - 18
            if not (-18 <= sx <= self.config.width + 18):
                continue
            if kind == "pole":
                d.rectangle((sx, 18, sx + 2, 132), fill=C["metal"])
                d.rectangle((sx - 8, 33, sx + 10, 35), fill=C["metal"])
            elif kind == "lamp":
                d.rectangle((sx, 69, sx + 2, 132), fill=C["wall_dark"])
                d.rectangle((sx - 3, 64, sx + 5, 69), fill=C["lamp"])
            else:
                d.rectangle((sx, 86, sx + 3, 132), fill=C["wall_dark"])
                d.rectangle((sx - 2, 79, sx + 5, 86), fill=C["red"])

    # ---------- carriage ----------
    def _draw_carriage(self, img: Image.Image, phase: float) -> None:
        d = ImageDraw.Draw(img)
        w, h = self.config.width, self.config.height

        d.rectangle((0, 0, w, 23), fill=C["wall_dark"])
        d.rectangle((0, 103, w, h), fill=C["wall"])
        d.rectangle((0, 22, 17, 103), fill=C["wall"])
        d.rectangle((81, 22, 93, 103), fill=C["wall"])
        d.rectangle((232, 22, 245, 103), fill=C["wall"])
        d.rectangle((309, 22, w, 103), fill=C["wall"])

        for x1, y1, x2, y2 in self.WINDOWS:
            d.rectangle((x1 - 3, y1 - 3, x2 + 3, y2 + 3), outline=C["trim"], width=3)
            d.line((x1 - 3, y2 + 3, x2 + 3, y2 + 3), fill=C["ink2"], width=2)

        d.rectangle((0, 6, w, 10), fill=C["metal"])
        d.rectangle((0, 19, w, 23), fill=C["trim"])

        for hx in (72, 104, 136, 168, 200, 232):
            d.line((hx, 9, hx, 16), fill=C["trim"], width=1)
            d.rectangle((hx - 4, 16, hx + 4, 20), outline=C["trim"])

        d.rectangle((56, 107, 263, 122), fill=C["seat_hi"])
        d.rectangle((56, 123, 263, 145), fill=C["seat"])
        d.rectangle((56, 145, 263, 149), fill=C["ink"])
        d.rectangle((0, 150, w, h), fill=C["ink"])
        d.rectangle((0, 151, w, 154), fill=C["metal"])

        for sx in (97, 139, 181, 223):
            d.line((sx, 108, sx, 144), fill=C["ink2"])

        for x in (7, 314):
            d.rectangle((x, 36, x + 2, 134), fill=C["trim"])
        d.rectangle((109, 96, 115, 107), fill=C["red"])
        d.point((112, 99), fill=C["white"])

        blink = 1 if math.sin(phase * math.tau * 16) > 0.82 else 0
        if blink:
            d.point((286, 17), fill=C["lamp"])
            d.point((288, 17), fill=C["lamp"])

    # ---------- passenger sprite ----------
    def _draw_passenger(self, img: Image.Image, phase: float) -> None:
        d = ImageDraw.Draw(img)
        seat_y = 122

        breath = 1 if math.sin(phase * math.tau * 4) > 0.65 else 0
        hair_sway = 1 if math.sin(phase * math.tau * 3 + 0.7) > 0.45 else 0

        f = phase * self.config.frame_count
        blink = any(abs(f - b) < 1.3 for b in (22, 23, 73, 113, 114))

        d.rectangle((188, seat_y + 8, 192, seat_y + 29), fill=C["skin"])
        d.rectangle((199, seat_y + 8, 203, seat_y + 29), fill=C["skin"])
        d.rectangle((185, seat_y + 29, 193, seat_y + 33), fill=C["shoe"])
        d.rectangle((198, seat_y + 29, 206, seat_y + 33), fill=C["shoe"])

        body_top = 97 - breath
        d.rectangle((181, body_top, 210, seat_y + 11), fill=C["coat_dark"])
        d.rectangle((185, body_top + 3, 206, seat_y + 8), fill=C["coat"])
        d.rectangle((189, body_top + 5, 202, body_top + 8), fill=C["scarf"])
        d.rectangle((180, body_top + 8, 184, body_top + 26), fill=C["coat"])
        d.rectangle((207, body_top + 8, 211, body_top + 26), fill=C["coat"])
        d.point((181, body_top + 27), fill=C["skin"])
        d.point((210, body_top + 27), fill=C["skin"])

        d.rectangle((191, 83 - breath, 199, 90 - breath), fill=C["skin"])
        d.rectangle((186, 70 - breath, 204, 86 - breath), fill=C["skin"])

        hy = 66 - breath
        d.rectangle((183, hy, 207 + hair_sway, hy + 15), fill=C["hair_dark"])
        d.rectangle((181, hy + 6, 186, hy + 25), fill=C["hair_dark"])
        d.rectangle((204 + hair_sway, hy + 4, 211 + hair_sway, hy + 26), fill=C["hair_dark"])
        d.rectangle((185, hy - 3, 204, hy + 7), fill=C["hair"])
        d.rectangle((184, hy + 2, 189, hy + 13), fill=C["hair"])
        d.rectangle((199, hy + 1, 207, hy + 12), fill=C["hair"])
        d.rectangle((188, hy + 6, 191, hy + 9), fill=C["hair"])
        d.rectangle((196, hy + 5, 199, hy + 8), fill=C["hair"])

        eye_y = 78 - breath
        if blink:
            d.line((189, eye_y, 192, eye_y), fill=C["ink"])
            d.line((198, eye_y, 201, eye_y), fill=C["ink"])
        else:
            d.rectangle((189, eye_y - 1, 191, eye_y + 1), fill=C["ink"])
            d.rectangle((199, eye_y - 1, 201, eye_y + 1), fill=C["ink"])
            d.point((190, eye_y - 1), fill=C["white"])
            d.point((200, eye_y - 1), fill=C["white"])

        d.rectangle((216, 113, 229, 125), fill=C["hair_dark"])
        d.rectangle((219, 111, 226, 113), fill=C["trim"])
        d.point((222, 117), fill=C["lamp"])

    def _draw_glass_reflection(self, img: Image.Image, phase: float) -> None:
        d = ImageDraw.Draw(img)
        for i, (x1, y1, x2, y2) in enumerate(self.WINDOWS):
            span = x2 - x1 + 26
            sweep = x1 - 13 + int((phase * span * 2 + i * 19) % span)
            for dx, alpha in ((0, 0.12), (2, 0.08), (5, 0.05)):
                x = sweep + dx
                if x1 <= x <= x2:
                    for y in range(y1 + 4, y2 - 3):
                        old = img.getpixel((x, y))
                        img.putpixel((x, y), _mix(old, C["reflection"], alpha))

            if ((phase * 8 + i * 0.3) % 1.0) < 0.04:
                gx = (x1 + x2) // 2 + (i - 1) * 7
                gy = y1 + 18 + i * 5
                d.line((gx - 3, gy, gx + 3, gy), fill=C["lamp"])
                d.line((gx, gy - 3, gx, gy + 3), fill=C["lamp"])
