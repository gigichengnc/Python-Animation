from pixel_train.scene import PixelTrainScene, RenderConfig


def test_native_frame_size_and_mode():
    cfg = RenderConfig(width=320, height=180, duration=2, fps=6, scale=2)
    scene = PixelTrainScene(cfg)
    frame = scene.render_frame(0)
    assert frame.size == (320, 180)
    assert frame.mode == "RGB"


def test_scaled_frame_uses_integer_pixel_scale():
    cfg = RenderConfig(width=320, height=180, duration=2, fps=6, scale=3)
    scene = PixelTrainScene(cfg)
    frame = scene.render_scaled_frame(0)
    assert frame.size == (960, 540)


def test_render_is_deterministic():
    cfg = RenderConfig(duration=2, fps=6, seed=99)
    a = PixelTrainScene(cfg).render_frame(3)
    b = PixelTrainScene(cfg).render_frame(3)
    assert a.tobytes() == b.tobytes()


def test_loop_phase_wraps_exactly():
    cfg = RenderConfig(duration=2, fps=6)
    scene = PixelTrainScene(cfg)
    first = scene.render_frame(0)
    wrapped = scene.render_frame(cfg.frame_count)
    assert first.tobytes() == wrapped.tobytes()
