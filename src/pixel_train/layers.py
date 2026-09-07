from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from PIL import Image


FrameFactory = Callable[[float], Image.Image]


@dataclass
class Layer:
    """A compositing layer.

    A layer can be backed by a cached static surface, a PNG asset, or a
    phase-driven factory.  The compositor does not care how the pixels were
    produced; it only knows position, z-order and opacity.
    """

    name: str
    z: int
    x: int = 0
    y: int = 0
    opacity: int = 255
    visible: bool = True
    static_surface: Image.Image | None = None
    frame_factory: FrameFactory | None = None
    asset_path: Path | None = None
    _asset_cache: Image.Image | None = field(default=None, init=False, repr=False)

    def surface(self, phase: float) -> Image.Image:
        if self.static_surface is not None:
            return self.static_surface
        if self.frame_factory is not None:
            return self.frame_factory(phase)
        if self.asset_path is not None:
            if self._asset_cache is None:
                self._asset_cache = Image.open(self.asset_path).convert("RGBA")
            return self._asset_cache
        raise RuntimeError(f"Layer {self.name!r} has no pixel source")
