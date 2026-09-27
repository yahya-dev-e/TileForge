"""Generates static mock TileResponse JSON payloads for the Unity team.

The Unity devs need realistic /api/v1/generate-tile responses to build the
Editor UI (LevelGenWindow.cs) and test sprite/material/collider wiring before
the backend is fully deployed. Rather than hand-writing example JSON (which
drifts from the real API contract), this script calls the real `generate_tile`
endpoint function in-process and dumps the resulting Pydantic model straight
to disk, so a mock can never diverge from the live schema.

Runs entirely on the procedural fallback synthesizer (no SD-Turbo weights, no
GPU, no network) since the model is never loaded outside of FastAPI's
app lifespan.

Usage:
    python backend/generate_mock_payloads.py
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

from app.main import generate_tile, get_prompt_presets  # noqa: E402
from app.schemas import TileRequest  # noqa: E402

OUTPUT_DIR = BACKEND_DIR / "test_data" / "mock_payloads"
MOCK_SEED = 42
MOCK_SIZE = 256  # matches the standardized test_data dimensions


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for preset in get_prompt_presets():
        request = TileRequest(
            prompt=preset.prompt,
            negative_prompt=preset.negative_prompt,
            width=MOCK_SIZE,
            height=MOCK_SIZE,
            steps=preset.steps,
            guidance_scale=preset.guidance_scale,
            seed=MOCK_SEED,
            normal_strength=preset.normal_strength,
        )
        response = generate_tile(request)

        output_path = OUTPUT_DIR / f"{preset.id}.json"
        output_path.write_text(response.model_dump_json(indent=2))

        num_polygons = len(response.collider_polygons)
        print(
            f"Wrote {output_path.relative_to(BACKEND_DIR)} "
            f"({num_polygons} collider polygon(s), engine={response.metadata.get('engine')})"
        )


if __name__ == "__main__":
    main()
