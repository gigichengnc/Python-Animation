from pathlib import Path

from pixel_train.render import render

render(Path("output/demo.gif"), duration=6, fps=12, scale=3)
