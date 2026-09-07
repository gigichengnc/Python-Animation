from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProductionConfig:
    """Central render targets for the v0.4 production pipeline."""

    native_width: int = 2560
    native_height: int = 1440
    render_fps: int = 24
    character_fps: int = 8
    preview_seconds: float = 10.0

    @property
    def native_size(self) -> tuple[int, int]:
        return self.native_width, self.native_height

    @property
    def master_size(self) -> tuple[int, int]:
        return self.native_width * 2, self.native_height * 2

    @property
    def delivery_size(self) -> tuple[int, int]:
        return 3840, 2160

    @property
    def preview_frames(self) -> int:
        return round(self.render_fps * self.preview_seconds)
