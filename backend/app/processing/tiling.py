"""Seamless border wrapping and blending algorithms for 2D tilemaps."""

import numpy as np
from PIL import Image


def apply_seamless_tiling(
    image: Image.Image,
    blend_ratio: float = 0.15,
    method: str = "cross_fade"
) -> Image.Image:
    """Transforms a generated 2D texture into a seamlessly repeatable tile.

    Uses dual-axis cyclic offset with smooth cosine cross-dissolve blending
    across both horizontal and vertical seams.

    Args:
        image: Source PIL Image (RGB or RGBA).
        blend_ratio: Normalized width of the cross-fade boundary [0.05, 0.35].
        method: Blending algorithm ('cross_fade' or 'offset_blend').

    Returns:
        Seamlessly tiling PIL Image of identical dimensions and format.
    """
    img_np = np.array(image).astype(np.float32)
    h, w = img_np.shape[:2]
    channels = img_np.shape[2] if img_np.ndim == 3 else 1

    # Shift image by half dimensions so seams meet at center
    shift_y = h // 2
    shift_x = w // 2
    rolled = np.roll(np.roll(img_np, shift_y, axis=0), shift_x, axis=1)

    # Compute blend boundary widths
    bw = max(2, int(w * blend_ratio))
    bh = max(2, int(h * blend_ratio))

    # Construct smooth cosine ramps (avoids linear harsh gradient lines)
    t_x = np.linspace(0, np.pi, bw)
    ramp_x = 0.5 * (1.0 - np.cos(t_x))  # Smooth S-curve from 0.0 to 1.0

    t_y = np.linspace(0, np.pi, bh)
    ramp_y = 0.5 * (1.0 - np.cos(t_y))

    if channels > 1:
        ramp_x = ramp_x.reshape(1, bw, 1)
        ramp_y = ramp_y.reshape(bh, 1, 1)
    else:
        ramp_x = ramp_x.reshape(1, bw)
        ramp_y = ramp_y.reshape(bh, 1)

    # Blend horizontal seam
    left_strip = rolled[:, :bw]
    right_strip = rolled[:, -bw:]
    blended_x = left_strip * ramp_x + right_strip * (1.0 - ramp_x)
    rolled[:, :bw] = blended_x
    rolled[:, -bw:] = blended_x

    # Blend vertical seam
    top_strip = rolled[:bh, :]
    bottom_strip = rolled[-bh:, :]
    blended_y = top_strip * ramp_y + bottom_strip * (1.0 - ramp_y)
    rolled[:bh, :] = blended_y
    rolled[-bh:, :] = blended_y

    # Unroll back to original coordinate space
    unrolled = np.roll(np.roll(rolled, -shift_y, axis=0), -shift_x, axis=1)

    # Clamp and cast back to uint8
    seamless_np = np.clip(unrolled, 0, 255).astype(np.uint8)
    return Image.fromarray(seamless_np, mode=image.mode)


def verify_tile_seamlessness(image: Image.Image, tolerance_rgb: float = 12.0) -> bool:
    """Verifies whether the opposite edges of an image match within a tolerance threshold.

    Checks:
        - Column 0 vs Column (Width - 1)
        - Row 0 vs Row (Height - 1)
    """
    arr = np.array(image).astype(np.float32)
    h, w = arr.shape[:2]

    diff_x = np.mean(np.abs(arr[:, 0] - arr[:, w - 1]))
    diff_y = np.mean(np.abs(arr[0, :] - arr[h - 1, :]))

    return float(diff_x) < tolerance_rgb and float(diff_y) < tolerance_rgb
