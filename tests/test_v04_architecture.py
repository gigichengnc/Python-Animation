from PIL import Image

from pixel_train.compositor import Compositor
from pixel_train.config import ProductionConfig
from pixel_train.layers import Layer
from pixel_train.production_scene import ProductionTrainScene


def test_v04_sizes():
    cfg = ProductionConfig()
    assert cfg.native_size == (2560, 1440)
    assert cfg.master_size == (5120, 2880)
    assert cfg.delivery_size == (3840, 2160)


def test_v04_still_size():
    scene = ProductionTrainScene()
    assert scene.render_still().size == (2560, 1440)


def test_layer_z_order():
    comp = Compositor((4, 4))
    red = Image.new("RGBA", (4, 4), (255, 0, 0, 255))
    blue = Image.new("RGBA", (4, 4), (0, 0, 255, 255))
    frame = comp.compose(
        [Layer("top", 20, static_surface=blue), Layer("bottom", 10, static_surface=red)],
        0.0,
    )
    assert frame.getpixel((0, 0))[:3] == (0, 0, 255)


def test_production_scene_is_deterministic():
    a = ProductionTrainScene().render_frame(7, 48)
    b = ProductionTrainScene().render_frame(7, 48)
    assert a.tobytes() == b.tobytes()
