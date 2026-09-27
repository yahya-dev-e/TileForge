#!/usr/bin/env bash
# ==============================================================================
# TileForge AI - 1-Click Cloud GPU Provisioning Script
# Target Platforms: Brev.dev / Lambda Labs / RunPod / Vast.ai (Ubuntu 22.04 LTS)
# ==============================================================================

set -euo pipefail

echo "=========================================================="
echo "🚀 TileForge AI: Cloud GPU Environment Provisioning"
echo "=========================================================="

# 1. Verify NVIDIA Driver & CUDA
if ! command -v nvidia-smi &> /dev/null; then
    echo "⚠️ Warning: nvidia-smi not found! Please ensure NVIDIA drivers are installed."
else
    echo "✅ GPU detected:"
    nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
fi

# 2. Update System Packages & Install OS Dependencies
echo "📦 Updating system packages..."
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-venv git curl ffmpeg libsm6 libxext6 libgl1 libglib2.0-0

# 3. Create & Activate Python Virtual Environment
VENV_DIR="$HOME/tileforge-venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "🐍 Creating virtual environment at $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
pip install --upgrade pip setuptools wheel

# 4. Install PyTorch with CUDA 12.1 Acceleration
echo "🔥 Installing PyTorch with CUDA 12.1 support..."
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# 5. Install Backend Requirements
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "📚 Installing project dependencies from $SCRIPT_DIR/requirements.txt..."
pip install -r "$SCRIPT_DIR/requirements.txt"

# 6. Pre-warm & Cache Model Weights
echo "🧠 Pre-caching SD-Turbo weights from Hugging Face..."
python3 -c "
import torch
from diffusers import AutoPipelineForText2Image
print('Loading SD-Turbo into memory...')
pipe = AutoPipelineForText2Image.from_pretrained(
    'stabilityai/sd-turbo',
    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
    variant='fp16' if torch.cuda.is_available() else None
)
if torch.cuda.is_available():
    pipe.to('cuda')
    pipe('warmup check', num_inference_steps=1, guidance_scale=0.0)
print('✅ Model cached successfully!')
"

# 7. Print Success and Launch Instructions
PUBLIC_IP=$(curl -s ifconfig.me || echo "localhost")
echo "=========================================================="
echo "🎉 Setup Complete! To start the TileForge Backend Service:"
echo "   source $VENV_DIR/bin/activate"
echo "   cd $SCRIPT_DIR"
echo "   uvicorn app.main:app --host 0.0.0.0 --port 9000"
echo ""
echo "🌐 API Endpoint: http://$PUBLIC_IP:9000"
echo "📖 Swagger Docs: http://$PUBLIC_IP:9000/docs"
echo "=========================================================="

# Auto-launch option if passed --start
if [[ "${1:-}" == "--start" ]]; then
    cd "$SCRIPT_DIR"
    exec uvicorn app.main:app --host 0.0.0.0 --port 9000
fi
