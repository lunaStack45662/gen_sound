# Hướng Dẫn Chạy Project

## Công cụ GUI: Tạo audio + Ghép video

Quy trình mới, thủ công từng bước qua giao diện:

```
Text ──[Tab 1]──→ .mp3 ──[Tab 2]──→ ghép vào video
```

---

## Chuẩn Bị (chỉ làm 1 lần)

```powershell
# 1. Mở PowerShell trong thư mục project
cd d:\codePython\PythonProject

# 2. Activate virtual environment
.\.venv\Scripts\Activate.ps1
```

## Chạy ứng dụng GUI

```powershell
python gui_audio_tool.py
```

### Tab 1 — Tạo âm thanh từ text
1. Chọn giọng đọc từ dropdown (10 giọng có sẵn)
2. Nhập nội dung cần đọc
3. Bấm **"Tạo âm thanh"** → AI gen ra file `.mp3` trong `output/audio/`
4. Danh sách file hiện ra, có thể phát thử / xóa

### Tab 2 — Ghép audio vào video
1. **Chọn video** (file `.mp4`, `.avi`, `.mov`, `.mkv`)
2. **Chọn audio** (file `.mp3` hoặc `.wav` đã gen ở Tab 1)
3. Nhập **Từ giây** và **Đến giây** (vị trí trong video muốn chèn audio)
4. Bấm **"Ghép vào video"** → tạo file mới trong `output/video/`

> Audio gốc của video sẽ tự động tắt trong khoảng thời gian đã chọn.
> Video gốc không bị thay đổi.

---

## Cấu Trúc Thư Mục

```
PythonProject/
├── core/
│   ├── __init__.py
│   ├── audio_generator.py     ← Xử lý TTS (Vieneu v3 Turbo, GPU)
│   └── video_merger.py        ← Xử lý ghép audio-video (ffmpeg)
├── gui/
│   ├── __init__.py
│   ├── app.py                 ← Cửa sổ chính + Notebook 2 tab
│   ├── tab_gen_audio.py       ← Tab 1: nhập text → gen .mp3
│   └── tab_merge_audio.py     ← Tab 2: chọn video/audio → ghép
├── output/
│   ├── audio/                 ← File .mp3 đã gen (tự động đánh số)
│   └── video/                 ← Video đã ghép audio
├── gui_audio_tool.py          ← Entry point
├── .venv/                     ← Virtual environment (GPU: CUDA 12.4)
├── main.py                    ← Scratch file cũ (không dùng)
└── RUN.md                     ← File này
```

---

## Yêu Cầu Hệ Thống

| Thành phần | Phiên bản |
|-----------|-----------|
| Python | 3.12 |
| GPU | NVIDIA RTX 3050 6GB (CUDA 12.4) |
| Vieneu | v3 Turbo (48 kHz, GPU PyTorch) |
| ffmpeg | bundled với imageio-ffmpeg |

## Troubleshooting

| Lỗi | Nguyên nhân | Cách sửa |
|-----|-------------|----------|
| `No module named 'vieneu'` | Chưa activate venv | `.\.venv\Scripts\Activate.ps1` |
| Vieneu load chậm | Lần đầu tải model từ HuggingFace | Chờ 1-2 phút, lần sau nhanh hơn |
| Unicode lỗi khi in | Windows console | App dùng GUI tkinter nên không ảnh hưởng |
