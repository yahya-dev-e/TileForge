"""Offline validation for the OpenCV/NumPy post-processing pipeline (Step 3).

Runs the real seamless-tiling, normal-map baking, and collider-extraction
functions against every PNG in backend/test_data/raw/, writes the processed
outputs to backend/test_data/processed/, and prints diagnostics against the
team's acceptance criteria:

  - Seamless wrap must pass verify_tile_seamlessness (opposite edges match).
  - Normal map should sit near the neutral tangent-space color (R,G ~ 128,
    B high) on average, confirming the Sobel bake isn't over/under-driven.
  - Extracted collider polygons should have 4-20 vertices each; fewer means
    poor collision fidelity, more means excessive PolygonCollider2D geometry
    in Unity (tune collider tolerance/epsilon between 1.5 and 3.0 if not).

Needs zero GPU and no model weights - it only exercises app/processing/*.py.
If backend/test_data/raw/ is empty (the curated Kenney.nl sprites haven't
landed yet), a couple of synthetic placeholder tiles are generated so the
pipeline can still be exercised end-to-end; drop real sprites into raw/ and
re-run once they're available.

Usage:
    python backend/test_pipeline.py
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image

BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

from app.processing.tiling import apply_seamless_tiling, verify_tile_seamlessness  # noqa: E402
from app.processing.normal_map import bake_normal_map  # noqa: E402
from app.processing.collider import extract_polygon_colliders  # noqa: E402

RAW_DIR = BACKEND_DIR / "test_data" / "raw"
PROCESSED_DIR = BACKEND_DIR / "test_data" / "processed"

MIN_VERTICES = 4
MAX_VERTICES = 20


def _ensure_placeholder_raw_images() -> None:
    """Creates synthetic RGBA tiles if test_data/raw/ (including subfolders) is
    empty, so this script has something to run on before the curated sprites
    land in that folder."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if any(RAW_DIR.rglob("*.png")):
        return

    print(f"No PNGs found in {RAW_DIR} yet - generating placeholder tiles.")
    print("Drop the curated Kenney.nl sprites in there and re-run once available.\n")

    rng = np.random.default_rng(7)

    # Placeholder 1: solid opaque textured tile (brick-like noise pattern).
    solid = np.full((256, 256, 4), (110, 95, 80, 255), dtype=np.uint8)
    solid[:, :, :3] = np.clip(
        solid[:, :, :3].astype(np.int16) + rng.integers(-20, 20, (256, 256, 3)), 0, 255
    ).astype(np.uint8)
    Image.fromarray(solid, mode="RGBA").save(RAW_DIR / "placeholder_solid_brick.png")

    # Placeholder 2: disconnected floating debris (separate island shapes),
    # to exercise the multi-contour / small-noise-contour filtering path.
    floating = np.zeros((256, 256, 4), dtype=np.uint8)
    yy, xx = np.ogrid[:256, :256]
    for cx, cy, r in [(64, 64, 40), (180, 90, 30), (110, 190, 50)]:
        mask = (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r
        floating[mask] = (90, 80, 100, 255)
    Image.fromarray(floating, mode="RGBA").save(RAW_DIR / "placeholder_floating_debris.png")


def _normal_map_is_plausible(normal_arr: np.ndarray) -> bool:
    """Coarse sanity check: on average a tile should sit near the neutral
    tangent-space normal (R=G=128, B high), per the doc's 'primarily
    purple/periwinkle' visual expectation."""
    r_mean, g_mean, b_mean = (normal_arr[..., c].mean() for c in range(3))
    return abs(r_mean - 128) < 40 and abs(g_mean - 128) < 40 and b_mean > 180


def run_pipeline_on(image_path: Path) -> bool:
    # Flatten the path relative to raw/ (e.g. "Colored/tile_0000") so files that
    # share a filename across category subfolders don't overwrite each other's
    # processed/ output.
    label = str(image_path.relative_to(RAW_DIR).with_suffix("")).replace("/", "_")
    print(f"--- {label} ---")
    source = Image.open(image_path).convert("RGBA")

    seamless = apply_seamless_tiling(source)
    seamless_ok = verify_tile_seamlessness(seamless)
    seamless.save(PROCESSED_DIR / f"{label}_seamless.png")
    print(f"  seamless wrap: {'OK' if seamless_ok else 'FAIL'} (verify_tile_seamlessness)")

    normal = bake_normal_map(seamless)
    normal_arr = np.asarray(normal)
    normal_ok = _normal_map_is_plausible(normal_arr)
    normal.save(PROCESSED_DIR / f"{label}_normal.png")
    mean_rgb = tuple(round(float(normal_arr[..., c].mean()), 1) for c in range(3))
    print(f"  normal map: {'OK' if normal_ok else 'CHECK'} (mean RGB = {mean_rgb})")

    polygons = extract_polygon_colliders(seamless, tolerance=2.0)
    vertex_counts = [len(poly) for poly in polygons]
    polys_ok = bool(vertex_counts) and all(MIN_VERTICES <= n <= MAX_VERTICES for n in vertex_counts)
    status = "OK" if polys_ok else "CHECK epsilon (1.5-3.0)"
    print(f"  collider polygons: {len(polygons)} polygon(s), vertex counts = {vertex_counts} ({status})")

    print()
    return seamless_ok and normal_ok and polys_ok


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    _ensure_placeholder_raw_images()

    images = sorted(RAW_DIR.rglob("*.png"))
    results = {str(img.relative_to(RAW_DIR)): run_pipeline_on(img) for img in images}

    passed = sum(results.values())
    print(f"{passed}/{len(results)} tile(s) passed all checks. Outputs written to {PROCESSED_DIR}")


if __name__ == "__main__":
    main()
