from __future__ import annotations

import argparse
from pathlib import Path

import imageio.v2 as imageio
import numpy as np

from .scene import PixelTrainScene, RenderConfig


def render(output: Path, *, duration: float = 12.0, fps: int = 12, scale: int = 4, seed: int = 7) -> Path:
    cfg = RenderConfig(duration=duration, fps=fps, scale=scale, seed=seed)
    scene = PixelTrainScene(cfg)
    output.parent.mkdir(parents=True, exist_ok=True)

    suffix = output.suffix.lower()
    if suffix not in {".gif", ".mp4"}:
        raise ValueError("Output must end in .gif or .mp4")

    frames = [np.asarray(scene.render_scaled_frame(i)) for i in range(cfg.frame_count)]

    if suffix == ".gif":
        imageio.mimsave(output, frames, format="GIF", duration=1 / fps, loop=0)
    else:
        with imageio.get_writer(
            output,
            fps=fps,
            codec="libx264",
            quality=8,
            macro_block_size=None,
            ffmpeg_log_level="error",
        ) as writer:
            for frame in frames:
                writer.append_data(frame)
    return output


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Render the v0.1 Pixel Train scene.")
    p.add_argument("--output", "-o", type=Path, default=Path("output/pixel_train.mp4"))
    p.add_argument("--duration", type=float, default=12.0)
    p.add_argument("--fps", type=int, default=12)
    p.add_argument("--scale", type=int, default=4)
    p.add_argument("--seed", type=int, default=7)
    return p


def main() -> None:
    args = build_parser().parse_args()
    path = render(args.output, duration=args.duration, fps=args.fps, scale=args.scale, seed=args.seed)
    print(f"Rendered {path}")


if __name__ == "__main__":
    main()
