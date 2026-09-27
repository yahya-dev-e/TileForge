"""Image processing and computer vision sub-package for TileForge AI.

Contains modules for seamless border blending, tangent normal map baking,
and OpenCV polygon collider extraction.
"""

from .tiling import apply_seamless_tiling
from .normal_map import bake_normal_map
from .collider import extract_polygon_colliders

__all__ = ["apply_seamless_tiling", "bake_normal_map", "extract_polygon_colliders"]
