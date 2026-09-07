from __future__ import annotations

import argparse
from pathlib import Path

import imageio.v2 as imageio
import numpy as np
from PIL import Image

from .config import ProductionConfig
from .production_scene import ProductionTrainScene


def save_still(path: Path, phase: float = 0.12) -> Path:
    scene = ProductionTrainScene()
    path.parent.mkdir(parents=True, exist_ok=True)
    scene.render_still(phase).convert("RGB").save(path)
    return path


def render_preview(path: Path, seconds: float = 10.0, fps: int = 24) -> Path:
    cfg = ProductionConfig(render_fps=fps, preview_seconds=seconds)
    scene = ProductionTrainScene(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)

    with imageio.get_writer(
        path,
        fps=fps,
        codec="libx264",
        quality=8,
        macro_block_size=None,
        ffmpeg_log_level="error",
    ) as writer:
        for i in range(cfg.preview_frames):
            frame = scene.render_frame(i, cfg.preview_frames).convert("RGB")
            writer.append_data(np.asarray(frame))
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("output/v04_still.png"))
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--seconds", type=float, default=10.0)
    parser.add_argument("--fps", type=int, default=24)
    args = parser.parse_args()

    if args.preview:
        render_preview(args.output, args.seconds, args.fps)
    else:
        save_still(args.output)

    print(f"Rendered {args.output}")


if __name__ == "__main__":
    main()
