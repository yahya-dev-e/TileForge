"""Pydantic request and response schemas for TileForge AI."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Point2D(BaseModel):
    """Normalized 2D vertex coordinate for Unity PolygonCollider2D."""
    x: float = Field(..., description="Normalized X coordinate in range [-0.5, 0.5]")
    y: float = Field(..., description="Normalized Y coordinate in range [-0.5, 0.5]")


class ColliderPolygon(BaseModel):
    """A single simplified polygon vertex loop, wrapped so clients using flat
    (non-nested-collection) JSON deserializers, such as Unity's JsonUtility,
    can parse a list of these without hitting nested-list limitations."""
    points: List[Point2D]


class TileRequest(BaseModel):
    """Configuration payload for sub-second tile generation."""
    prompt: str = Field(
        ...,
        description="Text description of the tile texture.",
        json_schema_extra={"example": "weathered ancient dungeon cobblestone wall, grey mossy stones, seamless flat 2d game texture"}
    )
    negative_prompt: str = Field(
        default="blurry, low quality, 3d perspective, isometric, shadows cast outside, vignette, watermarks, text, noisy",
        description="Negative conditioning to avoid unwanted artifacts."
    )
    width: int = Field(default=512, ge=128, le=1024, description="Tile texture width in pixels.")
    height: int = Field(default=512, ge=128, le=1024, description="Tile texture height in pixels.")
    steps: int = Field(default=2, ge=1, le=10, description="Inference steps (1-4 recommended for SD-Turbo).")
    guidance_scale: float = Field(default=1.5, ge=0.0, le=10.0, description="Classifier-free guidance scale.")
    seed: int = Field(default=-1, description="Random seed (-1 for random).")

    # Post-Processing Toggles
    seamless: bool = Field(default=True, description="Apply dual-axis seamless border wrapping.")
    seamless_blend_ratio: float = Field(default=0.15, ge=0.05, le=0.35, description="Border seam cross-fade width.")

    generate_normal_map: bool = Field(default=True, description="Bake tangent-space normal map.")
    normal_strength: float = Field(default=2.5, ge=0.1, le=10.0, description="Sobel normal vector height intensity.")
    invert_normal_y: bool = Field(default=False, description="Invert green channel for DirectX/OpenGL conventions.")

    generate_collider: bool = Field(default=True, description="Extract simplified polygon physics colliders.")
    collider_tolerance: float = Field(default=2.0, ge=0.5, le=10.0, description="Ramer-Douglas-Peucker epsilon simplification.")
    collider_alpha_threshold: int = Field(default=30, ge=0, le=255, description="Alpha or luminance threshold for contour detection.")


class TileResponse(BaseModel):
    """Response containing base64 encoded textures, vector colliders, and metrics."""
    status: str = Field(default="success")
    seed: int
    generation_time_ms: float
    color_map_base64: str = Field(..., description="Base64 PNG encoded diffuse texture.")
    normal_map_base64: Optional[str] = Field(default=None, description="Base64 PNG encoded tangent normal map.")
    collider_polygons: List[ColliderPolygon] = Field(default_factory=list, description="Simplified 2D polygon vertex loops.")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PromptPreset(BaseModel):
    """Cheatsheet prompt preset for quick prototyping in Unity."""
    id: str
    name: str
    prompt: str
    negative_prompt: str
    normal_strength: float = 2.5
    steps: int = 2
    guidance_scale: float = 1.5


class HealthResponse(BaseModel):
    """Service status and hardware accelerator diagnostics."""
    status: str
    version: str
    device: str
    gpu_name: Optional[str] = None
    model_loaded: bool
