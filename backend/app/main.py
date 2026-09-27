"""FastAPI Application Server for TileForge AI."""

import io
import os
import time
import base64
import logging
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image

from .schemas import (
    TileRequest,
    TileResponse,
    HealthResponse,
    PromptPreset,
    ColliderPolygon
)
from .model_runner import (
    initialize_model,
    generate_tile_image,
    get_hardware_info,
    is_model_loaded
)
from .processing.tiling import apply_seamless_tiling
from .processing.normal_map import bake_normal_map
from .processing.collider import extract_polygon_colliders

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("tileforge.api")

# Shared-secret API key gate. Unset by default so local/loopback usage keeps working
# without extra setup; set TILEFORGE_API_KEY before exposing the server via ngrok/cloud.
API_KEY = os.environ.get("TILEFORGE_API_KEY")


def require_api_key(x_api_key: Optional[str] = Header(default=None)):
    """Rejects the request unless it carries a matching X-API-Key header.

    No-op when TILEFORGE_API_KEY is unset, so local development needs no
    configuration; set the env var before exposing the server publicly.
    """
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key."
        )


# Helper functions for image serialization
def pil_to_base64_png(image: Image.Image) -> str:
    """Converts a PIL Image to a Base64-encoded PNG string."""
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def base64_to_pil(data_str: str) -> Image.Image:
    """Decodes a Base64 string into a PIL Image."""
    if "," in data_str:
        data_str = data_str.split(",", 1)[1]
    raw = base64.b64decode(data_str)
    return Image.open(io.BytesIO(raw))


# Lifespan context manager for FastAPI
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing TileForge AI Inference Server...")
    # Attempt to load SD-Turbo model
    initialize_model()
    yield
    logger.info("Shutting down TileForge AI Inference Server...")


app = FastAPI(
    title="TileForge AI Inference Service",
    description="Sub-second diffusion pipeline for seamless 2D tiles, normal maps, and colliders in Unity.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for Unity Editor & local tools
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_model=HealthResponse)
@app.get("/health", response_model=HealthResponse)
def health_check():
    """Returns server health, accelerator type, and pipeline readiness."""
    hw = get_hardware_info()
    return HealthResponse(
        status="ok",
        version="1.0.0",
        device=hw["device"],
        gpu_name=hw["gpu_name"],
        model_loaded=hw["model_loaded"]
    )


@app.get("/api/v1/presets", response_model=List[PromptPreset])
def get_prompt_presets():
    """Returns pre-tested curated prompt presets for quick prototyping in Unity."""
    return [
        PromptPreset(
            id="dungeon_stone",
            name="Ancient Dungeon Cobblestone",
            prompt="weathered ancient dungeon cobblestone wall, grey mossy stones, dark mortar, flat 2d game texture, seamless platformer tile, top-down orthographic, high contrast relief, crisp details",
            negative_prompt="blurry, 3d perspective, isometric, shadows cast outside, vignette, watermarks, character, hands, text, noisy",
            normal_strength=2.8,
            steps=2,
            guidance_scale=1.5
        ),
        PromptPreset(
            id="volcanic_lava",
            name="Volcanic Obsidian & Lava Veins",
            prompt="cracked volcanic obsidian rock tile, glowing molten orange magma veins, jagged basalt stones, flat 2d game texture, seamless texture, dark volcanic crust, vivid emissive fissures",
            negative_prompt="blurry, low contrast, 3d perspective angle, horizon, smooth plastic, human, text",
            normal_strength=3.2,
            steps=2,
            guidance_scale=1.8
        ),
        PromptPreset(
            id="cyber_circuit",
            name="Cyberpunk Neon Circuitry",
            prompt="futuristic sci-fi spaceship hull panel, dark brushed steel metal plates, glowing cyan neon circuitry lines, hexagonal rivets, clean hard-surface 2d game texture, seamless flat pattern",
            negative_prompt="organic, dirt, blurry, isometric, fish-eye, camera tilt, text, human, messy sketch",
            normal_strength=2.2,
            steps=2,
            guidance_scale=1.4
        ),
        PromptPreset(
            id="enchanted_wood",
            name="Enchanted Forest Wood Planks",
            prompt="weathered aged dark oak wood planks, ancient elven golden glowing runes carved into timber, leafy vines creeping, flat 2d texture, high detail grain, seamless fantasy tile",
            negative_prompt="modern, plastic, blurry, distorted, 3d view, perspective tilt, watermark",
            normal_strength=2.5,
            steps=2,
            guidance_scale=1.6
        ),
        PromptPreset(
            id="amethyst_crystal",
            name="Amethyst Crystal Cavern",
            prompt="dark underground cave bedrock embedded with vibrant purple amethyst crystal cluster facets, crystalline geode, flat orthographic 2d game texture, crisp sharp mineral edges, seamless",
            negative_prompt="blurry, low resolution, mud, character, 3d rendering artifact, sphere preview",
            normal_strength=3.0,
            steps=3,
            guidance_scale=1.7
        ),
        PromptPreset(
            id="steampunk_brass",
            name="Steampunk Rusted Brass",
            prompt="steampunk industrial brass and copper metal tiles, heavy bolts, rusted metal edges, steam vents, flat 2d platformer texture, seamless repeating pattern, high texture detail",
            negative_prompt="cartoon, lowres, blurry, perspective angle, round balls, text",
            normal_strength=2.6,
            steps=2,
            guidance_scale=1.5
        )
    ]


@app.post("/api/v1/generate-tile", response_model=TileResponse, dependencies=[Depends(require_api_key)])
def generate_tile(req: TileRequest):
    """End-to-end endpoint: Generates diffuse tile, seamless wrapping, normal map, and polygon colliders."""
    t0 = time.time()

    # Determine seed
    seed = req.seed if req.seed >= 0 else int(time.time() * 1000) % 2147483647

    # 1. Diffusion inference
    try:
        raw_image = generate_tile_image(
            prompt=req.prompt,
            negative_prompt=req.negative_prompt,
            width=req.width,
            height=req.height,
            steps=req.steps,
            guidance_scale=req.guidance_scale,
            seed=seed
        )
    except Exception as exc:
        logger.error(f"Inference generation error: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference failure: {str(exc)}"
        )

    # 2. Seamless border wrapping
    diffuse_image = raw_image
    if req.seamless:
        diffuse_image = apply_seamless_tiling(
            diffuse_image,
            blend_ratio=req.seamless_blend_ratio
        )

    color_b64 = pil_to_base64_png(diffuse_image)

    # 3. Tangent Normal Map baking
    normal_b64 = None
    if req.generate_normal_map:
        normal_image = bake_normal_map(
            diffuse_image,
            strength=req.normal_strength,
            invert_y=req.invert_normal_y
        )
        normal_b64 = pil_to_base64_png(normal_image)

    # 4. Polygon Collider Extraction
    collider_polys: List[ColliderPolygon] = []
    if req.generate_collider:
        raw_polys = extract_polygon_colliders(
            diffuse_image,
            tolerance=req.collider_tolerance,
            alpha_threshold=req.collider_alpha_threshold
        )
        collider_polys = [ColliderPolygon(points=poly) for poly in raw_polys]

    elapsed_ms = round((time.time() - t0) * 1000.0, 2)
    hw = get_hardware_info()

    return TileResponse(
        status="success",
        seed=seed,
        generation_time_ms=elapsed_ms,
        color_map_base64=color_b64,
        normal_map_base64=normal_b64,
        collider_polygons=collider_polys,
        metadata={
            "engine": "SD-Turbo" if hw["model_loaded"] else "Procedural Fallback",
            "device": hw["device"],
            "gpu_name": hw["gpu_name"],
            "seamless": req.seamless,
            "steps": req.steps,
            "normal_strength": req.normal_strength
        }
    )
