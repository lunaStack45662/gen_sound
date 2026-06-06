---
license: apache-2.0
datasets:
- pnnbao-ump/VieNeu-TTS-10k-ENVI
language:
- vi
- en
pipeline_tag: text-to-speech
tags:
- podcast
- code-switching
- voice-cloning
---

# 🦜 VieNeu-TTS

[![GitHub](https://img.shields.io/badge/GitHub-Repository-blue)](https://github.com/pnnbao97/VieNeu-TTS)
[![Model](https://img.shields.io/badge/Hugging%20Face-Model-yellow)](https://huggingface.co/pnnbao-ump/VieNeu-TTS-v2)
[![Discord](https://img.shields.io/badge/Discord-Join%20Us-5865F2?logo=discord&logoColor=white)](https://discord.gg/yJt8kzjzWZ)

<video controls src="https://cdn-uploads.huggingface.co/production/uploads/68b923a86c86c127a1975eda/q_6GIX5qXs9ZbIwKyy8GS.mp4" width="100%"></video>

## Overview

**VieNeu-TTS-v2** is the next generation of Vietnamese TTS, designed for **Natural Communication**, **Podcasts**, and **Bilingual (En-Vi) Code-switching**.

> [!IMPORTANT]
> **What's new in V2:**
> - **10,000+ Hours Data:** Trained on a massive bilingual dataset for unparalleled naturalness.
> - **Multi-Speaker Conversation:** Support for podcast-style scripts with distinct voices and emotional nuances.
> - **Seamless Code-switching:** High-quality English integration within Vietnamese sentences.
> - **Instant Voice Cloning:** Still supports cloning with just **3-5 seconds** of audio.

This project features the flagship **VieNeu-TTS-v2** architecture:
- **VieNeu-TTS-v2 (0.3B):** Optimized for high-fidelity bilingual speech and long-form content.
- **VieNeu-TTS-v2-Turbo:** Optimized for ultra-low latency and CPU deployment using GGUF.

Tác giả: **Phạm Nguyễn Ngọc Bảo**

## ☕ Support This Project

Training high-quality TTS models requires significant GPU resources. If you find this model useful, please consider supporting the development:

[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-Support-orange?logo=buy-me-a-coffee)](https://buymeacoffee.com/pnnbao)

---

## 🔥 Quick Start (Web UI)
```bash
git clone https://github.com/pnnbao97/VieNeu-TTS.git
cd VieNeu-TTS

# Install uv (if you haven't)
# Windows: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
# Linux/macOS: curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies & Run
uv sync --group gpu
uv run vieneu-web
```

---

## 📦 Using Python SDK (vieneu)

Install the SDK to integrate VieNeu-TTS-0.3B into your research or applications:

```bash
# Windows (Avoid llama-cpp build errors)
pip install vieneu --extra-index-url https://pnnbao97.github.io/llama-cpp-python-v0.3.16/cpu/

# Linux / MacOS
pip install vieneu
```

### Full Features Guide
```python
from vieneu import Vieneu

# Initialize in Standard mode (Default - Highest quality)
tts = Vieneu(emotion="natural") # emotion="natural" (giọng tự nhiên - mặc định) hoặc "storytelling" (giọng kể chuyện)

# 1. Simple synthesis (uses default Northern Female voice 'Trúc Ly')
text = "Chào bạn. Tôi là VieNeu-TTS, tôi có thể giúp bạn đọc sách, làm chatbot thời gian thực, thậm chí clone giọng nói của bạn."
audio = tts.infer(text=text)

# Save to file
tts.save(audio, "output_Trúc Ly.wav")
print("💾 Saved to output_Trúc Ly.wav")

# 2. Using a specific Preset Voice
voices = tts.list_preset_voices()
for desc, voice_id in voices:
    print(f"Voice: {desc} (ID: {voice_id})")

my_voice_id = voices[1][1] if len(voices) > 1 else voices[0][1] # Giọng Phạm Tuyên
voice_data = tts.get_preset_voice(my_voice_id)

audio_custom = tts.infer(text="Tôi đang nói bằng giọng của Bác sĩ Tuyên.", voice=voice_data)

# 3. Save to file
tts.save(audio_custom, "output_Phạm Tuyên.wav")
print("💾 Saved to output_Phạm Tuyên.wav")
```

### Remote Mode (Ultra-Fast with LMDeploy Server)
Deploy VieNeu-TTS as a high-performance API Server (powered by LMDeploy) with a single command.

### 1. Run with Docker (Recommended)

**Requirement**: [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) is required for GPU support.

**Start the Server with a Public Tunnel (No port forwarding needed):**
```bash
docker run --gpus all -p 23333:23333 -v huggingface_cache:/root/.cache/huggingface pnnbao/vieneu-tts:latest --tunnel
```

*   **Default**: The server loads the `VieNeu-TTS-v2` model for maximum quality.
*   **Tunneling**: The Docker image includes a built-in `bore` tunnel. Check the container logs to find your public address (e.g., `bore.pub:31631`).

### 2. Using the SDK (Remote Mode)

Once the server is running, you can connect from anywhere (Colab, Web Apps, etc.) without loading heavy models locally.

**Installation**:
```bash
pip install "vieneu[gpu]"
```

**Usage**:
```python
from vieneu import Vieneu
import os

# Configuration
REMOTE_API_BASE = 'http://your-server-ip:23333/v1'  # Or bore tunnel URL
REMOTE_MODEL_ID = "pnnbao-ump/VieNeu-TTS-v2"

# Initialization (LIGHTWEIGHT - only loads small codec locally)
# Default emotion is "natural" (conversational) - set emotion="storytelling" for storytelling mode
tts = Vieneu(mode='remote', api_base=REMOTE_API_BASE, model_name=REMOTE_MODEL_ID, emotion="natural")
os.makedirs("outputs", exist_ok=True)

# List remote voices
available_voices = tts.list_preset_voices()
for desc, name in available_voices:
    print(f"   - {desc} (ID: {name})")

# Use specific voice (dynamically select second voice)
if available_voices:
    _, my_voice_id = available_voices[1]
    voice_data = tts.get_preset_voice(my_voice_id)
    audio_spec = tts.infer(text="Chào bạn, tôi đang nói bằng giọng của bác sĩ Tuyên.", voice=voice_data)
    tts.save(audio_spec, f"outputs/remote_{my_voice_id}.wav")
    print(f"💾 Saved synthesis to: outputs/remote_{my_voice_id}.wav")

# Standard synthesis (uses default voice)
text_input = "Chế độ remote giúp tích hợp VieNeu vào ứng dụng Web hoặc App cực nhanh mà không cần GPU tại máy khách."
audio = tts.infer(text=text_input)
tts.save(audio, "outputs/remote_output.wav")
print("💾 Saved remote synthesis to: outputs/remote_output.wav")

# Zero-shot voice cloning (encodes audio locally, sends codes to server)
if os.path.exists("examples/audio_ref/example_ngoc_huyen.wav"):
    cloned_audio = tts.infer(
        text="Đây là giọng nói được clone và xử lý thông qua VieNeu Server.",
        ref_audio="examples/audio_ref/example_ngoc_huyen.wav",
        ref_text="Tác phẩm dự thi bảo đảm tính khoa học, tính đảng, tính chiến đấu, tính định hướng."
    )
    tts.save(cloned_audio, "outputs/remote_cloned_output.wav")
    print("💾 Saved remote cloned voice to: outputs/remote_cloned_output.wav")
```

---

## 📋 Reference Voices

| File | Gender | Accent | Description |
|---|---|---|---|
| Bình | Male | North | Male voice, North accent |
| Tuyên | Male | North | Male voice, North accent |
| Nguyên | Male | South | Male voice, South accent |
| Hương | Female | North | Female voice, North accent |
| Ngọc | Female | North | Female voice, North accent |
| Đoan | Female | South | Female voice, South accent |

---

## 🔬 Model Variants

| Model                   | Format  | Device  | Quality    | Features                |
| ----------------------- | ------- | ------- | ---------- | ----------------------- |
| VieNeu-TTS-v2           | PyTorch | GPU/CPU | ⭐⭐⭐⭐⭐ | **Podcast, En-Vi CS**   |
| VieNeu-TTS-v2 (GGUF)    | GGUF Q4 | CPU     | ⭐⭐⭐⭐   | **Fastest CPU, Podcast**|
| VieNeu-TTS-v1           | PyTorch | GPU     | ⭐⭐⭐⭐   | Stable (Vi only)        |
| VieNeu-TTS-0.3B         | PyTorch | GPU/CPU | ⭐⭐⭐     | Legacy Ultra-Fast       |

---

## 📑 Citation

```bibtex
@misc{vieneutts2026,
  title        = {VieNeu-TTS-v2: Vietnamese Text-to-Speech with Instant Voice Cloning},
  author       = {Pham Nguyen Ngoc Bao},
  year         = {2026},
  publisher    = {Hugging Face},
  howpublished = {\url{https://huggingface.co/pnnbao-ump/VieNeu-TTS}}
}
```

---

**Made with ❤️ for the Vietnamese TTS community**