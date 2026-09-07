from pixel_train.scene import PixelTrainScene, RenderConfig


def test_default_native_resolution():
    cfg = RenderConfig()
    assert (cfg.width, cfg.height) == (480, 270)
    frame = PixelTrainScene(cfg).render_frame(0)
    assert frame.size == (480, 270)
    assert frame.mode == "RGB"


def test_four_x_export_is_full_hd():
    cfg = RenderConfig(duration=1, fps=2, scale=4)
    frame = PixelTrainScene(cfg).render_scaled_frame(0)
    assert frame.size == (1920, 1080)


def test_render_is_deterministic():
    cfg = RenderConfig(duration=2, fps=6, seed=99)
    a = PixelTrainScene(cfg).render_frame(3)
    b = PixelTrainScene(cfg).render_frame(3)
    assert a.tobytes() == b.tobytes()


def test_loop_phase_wraps_exactly():
    cfg = RenderConfig(duration=2, fps=6)
    scene = PixelTrainScene(cfg)
    assert scene.render_frame(0).tobytes() == scene.render_frame(cfg.frame_count).tobytes()


def test_world_moves_but_carriage_anchor_stays_stable():
    cfg = RenderConfig(duration=12, fps=12)
    scene = PixelTrainScene(cfg)
    a = scene.render_frame(0)
    b = scene.render_frame(31)

    assert a.tobytes() != b.tobytes()
    assert a.getpixel((2, 2)) == b.getpixel((2, 2))
    assert a.getpixel((80, 190)) == b.getpixel((80, 190))
