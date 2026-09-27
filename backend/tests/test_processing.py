import numpy as np
from PIL import Image

from app.model_runner import generate_tile_image
from app.processing.collider import extract_polygon_colliders
from app.processing.normal_map import bake_normal_map
from app.processing.tiling import apply_seamless_tiling, verify_tile_seamlessness


def test_seamless_tiling_preserves_dimensions_and_edges():
    source = Image.new("RGB", (32, 24), (80, 120, 160))

    result = apply_seamless_tiling(source)

    assert result.size == source.size
    assert result.mode == source.mode
    assert verify_tile_seamlessness(result)


def test_normal_map_for_flat_surface_is_neutral():
    source = Image.new("RGB", (12, 10), (100, 100, 100))

    result = np.asarray(bake_normal_map(source))

    assert result.shape == (10, 12, 3)
    assert result.dtype == np.uint8
    assert np.all(result[:, :, 0] == 127)
    assert np.all(result[:, :, 1] == 127)
    assert np.all(result[:, :, 2] >= 254)


def test_collider_extraction_returns_normalized_polygon():
    source = Image.new("RGB", (64, 64), (255, 255, 255))

    polygons = extract_polygon_colliders(source, alpha_threshold=30)

    assert len(polygons) == 1
    assert len(polygons[0]) >= 4
    assert all(-0.5 <= point.x <= 0.5 for point in polygons[0])
    assert all(-0.5 <= point.y <= 0.5 for point in polygons[0])


def test_procedural_fallback_is_deterministic_and_prompt_aware():
    first = generate_tile_image("volcanic lava tile", width=128, height=128, seed=123)
    second = generate_tile_image("volcanic lava tile", width=128, height=128, seed=123)

    assert first.size == (128, 128)
    assert first.mode == "RGB"
    assert np.array_equal(np.asarray(first), np.asarray(second))
