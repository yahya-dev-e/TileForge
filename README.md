# 🛠️ TileForge AI: Real-Time Generative 2D Tilemaps & Shading for Unity

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Unity 2022.3 LTS](https://img.shields.io/badge/Unity-2022.3%20LTS-blue.svg)](https://unity.com/)
[![Universal Render Pipeline](https://img.shields.io/badge/Render%20Pipeline-URP%202D-green.svg)](https://docs.unity3d.com/Packages/com.unity.render-pipelines.universal@latest)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI%20%2B%20PyTorch-009688.svg)](https://fastapi.tiangolo.com/)
[![Inference](https://img.shields.io/badge/Model-SD--Turbo%20%2F%20TensorRT-orange.svg)](https://huggingface.co/stabilityai/sd-turbo)

> **TileForge AI** is an end-to-end generative AI level design pipeline bridging sub-second text-to-image diffusion models directly into the **Unity Editor (2022.3 LTS URP 2D)**. It empowers developers and level designers to generate seamless 2D tiles, baked tangent-space normal maps, and simplified physics polygon colliders in under 1 second without leaving the engine.

---

## 🌟 Highlights & Key Features

1. **Sub-Second Diffusion Inference (SD-Turbo / TensorRT)**
   - Powered by Stable Diffusion Turbo (`stabilityai/sd-turbo`) running with 1-4 step Euler ancestral sampling.
   - Generates high-fidelity 512x512 game sprites and textures in 200–800ms on modern NVIDIA RTX GPUs.
   - Built-in CPU fallback and mockup generator for low-spec testing environments.

2. **Seamless Dual-Axis Border Wrapping & Blending**
   - Proprietary circular convolution and border-blend algorithm (`processing/tiling.py`).
   - Ensures tiles align perfectly when painted onto Unity Tilemaps without visible seams or repetition artifacts.

3. **Instant Tangent-Space Normal Map Baking**
   - High-precision Sobel gradient filter (`processing/normal_map.py`) converting diffuse luminance and height features into standard tangent-space 2D normal maps (`(R=X, G=Y, B=Z)`).
   - Fully compatible with Unity Universal Render Pipeline (URP) **Sprite-Lit-Default** and **Lit 2D Point/Global Lights**.

4. **Automated 2D Physics Polygon Collider Extraction**
   - OpenCV contour detection coupled with Ramer-Douglas-Peucker (RDP) epsilon polygon simplification (`processing/collider.py`).
   - Converts visual silhouettes into optimized vertex arrays ready for Unity `PolygonCollider2D`.

5. **Native Unity EditorWindow Integration (`LevelGenWindow.cs`)**
   - One-click asynchronous HTTP generation window inside the Unity Editor (`Window > TileForge > Level Generator`).
   - Live side-by-side Diffuse and Normal Map previews.
   - Instant asset import: automatically writes PNGs to `Assets/Generated/`, configures texture importers, instantiates URP 2D Lit materials, and assigns sprite colliders.

6. **Flexible Deployment Modes**
   - **Local GPU**: Run locally on any CUDA-compatible GPU.
   - **Cloud GPU (1-Click)**: Provision in seconds via `backend/setup_cloud.sh` (tested on Brev.dev, Lambda Labs, RunPod).
   - **Zero-Setup Google Colab**: Use `backend/colab_fallback.ipynb` paired with ngrok to tunnel inference directly into Unity.

---

## 🏛️ System Architecture

```
┌────────────────────────────────────────────────────────┐
│                   Unity 2022.3 LTS                      │
│                                                        │
│  [LevelGenWindow.cs]  ──(Async JSON/Base64 HTTP)───┐  │
│           │                                         │  │
│   Asset Database Import                             ▼  │
│    ├─ Diffuse Sprite (Assets/Generated/)      FastAPI Server
│    ├─ Normal Map (URP 2D Lit Material)       (Port 8000 / ngrok)
│    └─ PolygonCollider2D Setup                       │  │
└─────────────────────────────────────────────────────┼──┘
                                                      │
        ┌─────────────────────────────────────────────┘
        ▼
┌────────────────────────────────────────────────────────┐
│                   TileForge Backend                    │
│                                                        │
│  1. SD-Turbo Diffusion (PyTorch / TensorRT)            │
│     └── Fast 1-4 Step Text-to-Image                    │
│  2. Seamless Tiling Filter (Border Wrapping)           │
│  3. Tangent Normal Baker (Sobel Gradient Vector)       │
│  4. Collider Extractor (OpenCV + RDP Simplification)   │
└────────────────────────────────────────────────────────┘
```

See [docs/architecture.png](file:///c:/Users/yahya/OneDrive/Documentos/TileForge/TileForge/docs/architecture.png) for visual diagram breakdown.

---

## 📂 Repository Structure

```
tileforge-ai/
│
├── .gitignore                      # Configured for both Unity & Python
├── README.md                       # Main hackathon submission & setup documentation
├── LICENSE                         # MIT License
│
├── backend/                        # Python / FastAPI / NVIDIA inference service
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI application routes & endpoints
│   │   ├── schemas.py              # Pydantic models (TileRequest, TileResponse)
│   │   ├── model_runner.py         # SD-Turbo / TensorRT pipeline & warmups
│   │   └── processing/
│   │       ├── __init__.py
│   │       ├── tiling.py           # Seamless border wrapping & blending
│   │       ├── normal_map.py       # Sobel-based normal map baker
│   │       └── collider.py         # OpenCV contour detection & RDP simplification
│   │
│   ├── requirements.txt            # Python package dependencies
│   ├── setup_cloud.sh              # 1-click provisioning script for Brev / GPU instance
│   └── colab_fallback.ipynb        # Ready-to-run Google Colab + ngrok notebook
│
├── unity-client/                   # The Unity 2022.3 LTS Project root
│   ├── Assets/
│   │   ├── Editor/
│   │   │   └── LevelGenWindow.cs   # Custom EditorWindow UI & async HTTP dispatcher
│   │   ├── Materials/
│   │   │   └── URP_Lit2D_Tile.mat  # 2D Lit material supporting normal maps
│   │   ├── Prefabs/
│   │   │   └── PlayerCharacter.prefab # 2D demo platformer character
│   │   ├── Scenes/
│   │   │   └── DemoSandbox.unity   # Showcase scene with 2D Point Lights & Tilemap
│   │   ├── Scripts/
│   │   │   ├── PlayerController.cs # Quick jump/move script for testing
│   │   │   └── LightFollower.cs    # Moves 2D light with mouse to show relief
│   │   └── Generated/              # Target folder for generated textures & sprites
│   │
│   ├── Packages/
│   │   └── manifest.json           # Includes com.unity.editor-coroutines & URP
│   └── ProjectSettings/            # Engine configuration (URP 2D renderer settings)
│
└── docs/                           # Submission materials & references
    ├── architecture.png            # System architecture diagram
    ├── prompt_presets.txt          # Pre-tested prompt cheatsheet for the demo
    └── demo_video_link.txt         # Link to the mandatory 90-second submission video
```

---

## 🚀 Quick Start Guide

### Option A: Local Backend Setup

#### 1. Requirements
- Python 3.10 or 3.11
- NVIDIA GPU with CUDA 11.8+ or 12.x (8GB+ VRAM recommended for SD-Turbo)
- Unity 2022.3 LTS with Universal Render Pipeline (URP)

#### 2. Install & Start Backend
```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies (use CUDA PyTorch wheel if on NVIDIA GPU)
pip install -r requirements.txt

# Start the FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The server will be available at `http://127.0.0.1:8000`. You can test endpoints via Swagger UI at `http://127.0.0.1:8000/docs`.

### Backend Automated Tests

Install the development dependencies and run the backend test suite from the repository root:

```bash
python -m pip install -r backend/requirements-dev.txt
pytest -q backend/tests
```

The suite validates seamless edge processing, normal-map generation, polygon extraction, the procedural fallback, and the `/api/v1/generate-tile` response contract. It does not download or load SD-Turbo weights.

---

### Mock Payloads for the Unity Team

Unity devs can build the Editor UI and test sprite/material/collider wiring without waiting for the backend to
be deployed. Generate static example responses for each curated preset:

```bash
python backend/generate_mock_payloads.py
```

This writes one JSON file per preset to `backend/test_data/mock_payloads/`, e.g. `dungeon_stone.json`. Each file
is produced by calling the real `generate_tile` endpoint function in-process (using the procedural fallback, so
no GPU or model weights are needed) and dumping the actual `TileResponse` Pydantic model — so the mock JSON can
never drift from the live API contract. Load one with `File.ReadAllText(...)` + `JsonUtility.FromJson<TileResponsePayload>(...)`
in `LevelGenWindow.cs` to test locally.

---

### Option B: Cloud GPU (Brev / Lambda / RunPod)

Run the one-click provisioning script on any Ubuntu GPU instance:
```bash
chmod +x backend/setup_cloud.sh
./backend/setup_cloud.sh
```

> ⚠️ **Set an API key before exposing this publicly.** The server has no authentication by default.
> Export `TILEFORGE_API_KEY=<your-secret>` before starting `uvicorn`, then paste the same value into the
> **API Key** field of the TileForge Window in Unity — otherwise anyone with the URL can trigger (billable)
> GPU inference.

---

### Option C: Google Colab Fallback (Free T4 GPU)

1. Open `backend/colab_fallback.ipynb` in [Google Colab](https://colab.research.google.com/).
2. Select **Runtime > Change runtime type > T4 GPU**.
3. Enter your free [ngrok auth token](https://ngrok.com/).
4. Set a `TILEFORGE_API_KEY` before launching the server so the public ngrok tunnel isn't wide open.
5. Run all cells. Copy the generated public URL (e.g., `https://xyz.ngrok-free.app`).
6. Paste this URL and your API key into the **TileForge Window** inside Unity.

---

## 🎮 Unity Client Setup

1. Open **Unity Hub** and click **Open > Add project from disk**.
2. Select the `unity-client/` folder.
3. Once Unity opens, load the demo scene:
   - `Assets/Scenes/DemoSandbox.unity`
4. Open the TileForge Generator:
   - Menu: **Window > TileForge > Level Generator**
5. Enter the Backend Server URL (e.g. `http://127.0.0.1:8000` or your ngrok URL).
6. Click **Test Connection** to ensure the green status indicator lights up.
7. Choose a preset or enter a prompt (e.g., `"mossy ancient stone bricks, fantasy dungeon wall, 2d platformer texture, sharp edges"`).
8. Click **Generate Tile & Material**.
9. The tile diffuse map, normal map, and colliders will be baked and imported directly into `Assets/Generated/`.
10. Press **Play** in Unity! Use `A`/`D` to move, `Space` to jump, and move your cursor around to watch the dynamic 2D Point Light react in real time against the generated normal map!

---

## 📡 API Specification

### `POST /api/v1/generate-tile`
Generates diffuse tile, seamless tiling wrap, tangent-space normal map, and polygon colliders in a single call.

If the server is started with a `TILEFORGE_API_KEY` environment variable set, this endpoint requires a matching
`X-API-Key` header on every request (returns `401` otherwise). The key is unset by default for local development;
set it before exposing the server publicly (cloud GPU / ngrok deployments).

#### Request Body
```json
{
  "prompt": "cracked volcanic obsidian stone wall with glowing lava veins",
  "negative_prompt": "blurry, low quality, 3d perspective, watermarks, text",
  "width": 512,
  "height": 512,
  "steps": 2,
  "guidance_scale": 1.5,
  "seed": 42,
  "seamless": true,
  "generate_normal_map": true,
  "normal_strength": 2.5,
  "generate_collider": true,
  "collider_tolerance": 2.0
}
```

#### Response Body
```json
{
  "status": "success",
  "seed": 42,
  "generation_time_ms": 320.5,
  "color_map_base64": "iVBORw0KGgoAAAANSUhEUgAAAgAAAAI...",
  "normal_map_base64": "iVBORw0KGgoAAAANSUhEUgAAAgAAAAI...",
  "collider_polygons": [
    {
      "points": [
        {"x": -0.5, "y": -0.5},
        {"x": 0.5, "y": -0.5},
        {"x": 0.5, "y": 0.5},
        {"x": -0.5, "y": 0.5}
      ]
    }
  ],
  "metadata": {
    "engine": "SD-Turbo",
    "device": "cuda",
    "gpu_name": "NVIDIA RTX 4090",
    "seamless": true,
    "steps": 2,
    "normal_strength": 2.5
  }
}
```

Each entry in `collider_polygons` is wrapped in a `points` object (rather than a bare nested array) so that
Unity's `JsonUtility`, which cannot deserialize nested collections, can parse the list directly.

---

## 🎨 Tested Prompt Presets

Pre-tested and tuned prompt templates are available in [docs/prompt_presets.txt](file:///c:/Users/yahya/OneDrive/Documentos/TileForge/TileForge/docs/prompt_presets.txt).
- **Dungeon Cobblestone**: Ancient weathered mossy grey stone wall, top-down 2d game texture
- **Cyberpunk Circuitry**: Glowing cyan circuit board panel, futuristic sci-fi plate
- **Lava Bricks**: Cracked volcanic obsidian with glowing magma fissure
- **Enchanted Wood**: Carved elven oak planks with glowing golden runes
- **Crystal Cavern**: Dark amethyst crystal cluster surface, reflective facets

---

## 📹 Video Submission

The 90-second submission video demonstrating the real-time inference, normal mapping, and Unity integration is documented in [docs/demo_video_link.txt](file:///c:/Users/yahya/OneDrive/Documentos/TileForge/TileForge/docs/demo_video_link.txt).

---

## 📄 License
This project is open-source under the [MIT License](file:///c:/Users/yahya/OneDrive/Documentos/TileForge/TileForge/LICENSE).
