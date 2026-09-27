"""OpenCV Contour Detection and RDP (Ramer-Douglas-Peucker) Polygon Simplification."""

from typing import List
import numpy as np
from PIL import Image
from ..schemas import Point2D

try:
    import cv2
    _HAS_CV2 = True
except ImportError:
    _HAS_CV2 = False


def extract_polygon_colliders(
    image: Image.Image,
    tolerance: float = 2.0,
    min_area_pixels: float = 120.0,
    alpha_threshold: int = 30,
    solid_fill_fallback: bool = True
) -> List[List[Point2D]]:
    """Extracts simplified 2D physics collider polygon contours from a tile sprite.

    Uses OpenCV contour detection coupled with the Ramer-Douglas-Peucker (RDP)
    algorithm (cv2.approxPolyDP) to reduce complex raster silhouettes into
    efficient polygon vertex loops ready for Unity PolygonCollider2D.

    Coordinates are normalized to Unity Sprite coordinates:
        X: [-0.5 (left), +0.5 (right)]
        Y: [-0.5 (bottom), +0.5 (top)]
    """
    img_np = np.array(image)
    h, w = img_np.shape[:2]

    # If OpenCV is not installed, fallback to standard bounding box collider
    if not _HAS_CV2:
        return [[
            Point2D(x=-0.5, y=-0.5),
            Point2D(x=0.5, y=-0.5),
            Point2D(x=0.5, y=0.5),
            Point2D(x=-0.5, y=0.5)
        ]]

    # 1. Determine Binary Mask (Alpha channel if present, otherwise luminance thresholding)
    if img_np.ndim == 3 and img_np.shape[2] == 4:
        alpha = img_np[:, :, 3]
        mask = (alpha > alpha_threshold).astype(np.uint8) * 255
    else:
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY) if img_np.ndim == 3 else img_np
        _, mask = cv2.threshold(gray, alpha_threshold, 255, cv2.THRESH_BINARY)

    # Clean up mask with morphological closing
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    # 2. Extract External Contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    polygons: List[List[Point2D]] = []

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area_pixels:
            continue

        # 3. Ramer-Douglas-Peucker (RDP) Polygon Approximation
        approx = cv2.approxPolyDP(cnt, epsilon=tolerance, closed=True)

        if len(approx) < 3:
            continue

        # 4. Map from Raster Pixels (top-left origin) to Unity 2D Sprite Space (center origin, +Y up)
        poly_points: List[Point2D] = []
        for pt in approx:
            px, py = float(pt[0][0]), float(pt[0][1])
            unity_x = round((px / float(w)) - 0.5, 4)
            unity_y = round(0.5 - (py / float(h)), 4)
            poly_points.append(Point2D(x=unity_x, y=unity_y))

        if len(poly_points) >= 3:
            polygons.append(poly_points)

    # Fallback to full tile square collider if mask is completely solid or empty
    if not polygons and solid_fill_fallback:
        polygons.append([
            Point2D(x=-0.5, y=-0.5),
            Point2D(x=0.5, y=-0.5),
            Point2D(x=0.5, y=0.5),
            Point2D(x=-0.5, y=0.5)
        ])

    return polygons
