#!/usr/bin/env bash
# Cài đặt môi trường + thư viện cho Công cụ tạo audio và ghép video (Ubuntu / Linux)
set -e

cd "$(dirname "$0")"

echo "==> Cài system dependencies (ffmpeg, python3, venv)..."
sudo apt update
sudo apt install -y ffmpeg python3 python3-venv python3-pip

echo "==> Tạo virtual environment..."
python3 -m venv .venv

echo "==> Upgrade pip..."
source .venv/bin/activate
pip install --upgrade pip

echo "==> Cài PyTorch với CUDA 12.4..."
pip install torch==2.6.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu124

echo "==> Cài các thư viện còn lại..."
pip install \
    vieneu==3.0.9 \
    customtkinter==6.0.0 \
    imageio-ffmpeg \
    pygame==2.6.1 \
    opencv-python-headless \
    Pillow \
    transformers \
    onnxruntime \
    tokenizers

echo ""
echo "✅ Hoàn tất. Chạy lệnh sau để khởi động:"
echo "   source .venv/bin/activate && python gui_audio_tool.py"
echo "   — hoặc —"
echo "   bash run.sh"
