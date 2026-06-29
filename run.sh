#!/usr/bin/env bash
# Công cụ tạo audio và ghép video - Run script (Ubuntu / Linux)
set -e

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo "❌ Chưa có virtual environment. Chạy install.sh trước."
    exit 1
fi

source .venv/bin/activate

export PYTHONIOENCODING=utf-8
export HF_HUB_DISABLE_SYMLINKS_WARNING=1
export TOKENIZERS_PARALLELISM=false

python gui_audio_tool.py
