from __future__ import annotations

from PIL import Image

from .layers import Layer


class Compositor:
    """Small deterministic RGBA compositor for production-sized pixel layers."""

    def __init__(self, size: tuple[int, int], background=(24, 23, 43, 255)):
        self.size = size
        self.background = background

    def compose(self, layers: list[Layer], phase: float) -> Image.Image:
        frame = Image.new("RGBA", self.size, self.background)

        for layer in sorted((l for l in layers if l.visible), key=lambda l: l.z):
            surface = layer.surface(phase)
            if surface.mode != "RGBA":
                surface = surface.convert("RGBA")

            if layer.opacity != 255:
                alpha = surface.getchannel("A").point(
                    lambda value: (value * layer.opacity) // 255
                )
                surface = surface.copy()
                surface.putalpha(alpha)

            frame.alpha_composite(surface, (layer.x, layer.y))

        return frame
