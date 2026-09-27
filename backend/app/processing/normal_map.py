"""Sobel-based Tangent Space Normal Map Baker for Unity 2D URP."""

import numpy as np
from PIL import Image

try:
    import cv2
    _HAS_CV2 = True
except ImportError:
    _HAS_CV2 = False


def _sobel_gradient_numpy(img_gray: np.ndarray):
    """Fallback Sobel gradient calculation using pure NumPy convolutions."""
    # Pad borders with reflection
    padded = np.pad(img_gray, ((1, 1), (1, 1)), mode="reflect")
    
    # Sobel kernels
    # Kx: [[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]]
    gx = (
        -1.0 * padded[:-2, :-2] + 1.0 * padded[:-2, 2:] +
        -2.0 * padded[1:-1, :-2] + 2.0 * padded[1:-1, 2:] +
        -1.0 * padded[2:, :-2] + 1.0 * padded[2:, 2:]
    ) / 8.0

    # Ky: [[-1, -2, -1], [0, 0, 0], [1, 2, 1]]
    gy = (
        -1.0 * padded[:-2, :-2] - 2.0 * padded[:-2, 1:-1] - 1.0 * padded[:-2, 2:] +
         1.0 * padded[2:, :-2] + 2.0 * padded[2:, 1:-1] + 1.0 * padded[2:, 2:]
    ) / 8.0

    return gx, gy


def bake_normal_map(
    image: Image.Image,
    strength: float = 2.5,
    invert_y: bool = False,
    blur_kernel: int = 3
) -> Image.Image:
    """Generates a tangent-space 2D normal map from a diffuse RGB/RGBA texture.

    Converts luminance into an approximate surface heightfield, computes spatial
    gradients using 3x3 Sobel kernels, and encodes normalized surface normal
    vectors into standard 8-bit RGB channels:
        R = Normal.X  (0 = Left,   255 = Right)
        G = Normal.Y  (0 = Down,   255 = Up, or inverted for DirectX)
        B = Normal.Z  (0 = Deep,   255 = Surface Facing Camera)

    Args:
        image: Diffuse PIL Image.
        strength: Vector relief intensity multiplier (typically 1.0 - 5.0).
        invert_y: Invert the Y (Green) channel for OpenGL vs DirectX conventions.
        blur_kernel: Optional Gaussian blur pre-pass kernel to eliminate pixel noise (3 or 5).

    Returns:
        RGB PIL Image representing the tangent-space normal map.
    """
    # 1. Convert to Grayscale Luminance [0.0, 1.0]
    rgb_img = image.convert("RGB")
    gray = np.array(rgb_img.convert("L")).astype(np.float64) / 255.0

    # 2. Compute Spatial Gradients with Sobel Filter
    if _HAS_CV2:
        if blur_kernel > 1:
            k = blur_kernel if blur_kernel % 2 != 0 else blur_kernel + 1
            gray = cv2.GaussianBlur(gray, (k, k), 0)
        grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    else:
        grad_x, grad_y = _sobel_gradient_numpy(gray)

    # In Unity Tangent Space:
    # Nx = -grad_x * strength
    # Ny = grad_y * strength (if standard upward normal)
    nx = -grad_x * strength
    ny = grad_y * strength if invert_y else -grad_y * strength
    nz = np.ones_like(nx)

    # 3. Normalize Vectors (Nx, Ny, Nz) to unit length
    magnitude = np.sqrt(nx**2 + ny**2 + nz**2) + 1e-7
    nx_norm = nx / magnitude
    ny_norm = ny / magnitude
    nz_norm = nz / magnitude

    # 4. Remap from [-1.0, 1.0] to [0, 255] RGB color space
    r = ((nx_norm * 0.5 + 0.5) * 255.0).clip(0, 255).astype(np.uint8)
    g = ((ny_norm * 0.5 + 0.5) * 255.0).clip(0, 255).astype(np.uint8)
    b = ((nz_norm * 0.5 + 0.5) * 255.0).clip(0, 255).astype(np.uint8)

    normal_np = np.stack([r, g, b], axis=2)
    return Image.fromarray(normal_np, mode="RGB")
