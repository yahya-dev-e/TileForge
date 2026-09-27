import base64
import io

from PIL import Image

from app import main
from app.schemas import TileRequest


def test_generate_tile_returns_serializable_response(monkeypatch):
    monkeypatch.setattr(
        main,
        "generate_tile_image",
        lambda **kwargs: Image.new("RGB", (128, 128), (100, 100, 100)),
    )

    response = main.generate_tile(
        TileRequest(
            prompt="test tile",
            width=128,
            height=128,
            generate_normal_map=True,
            generate_collider=True,
        )
    )

    decoded = base64.b64decode(response.color_map_base64)
    generated = Image.open(io.BytesIO(decoded))

    assert response.status == "success"
    assert response.seed >= 0
    assert response.generation_time_ms >= 0
    assert generated.size == (128, 128)
    assert response.normal_map_base64 is not None
    assert response.collider_polygons
    assert response.metadata["seamless"] is True
