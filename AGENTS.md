# AGENTS.md — Công cụ tạo audio và ghép video

## Tổng quan
Ứng dụng GUI (tkinter) giúp tạo file âm thanh từ text bằng AI (Vieneu v3 Turbo) và ghép audio vào video tại vị trí chỉ định. Chạy GPU NVIDIA CUDA 12.4.

## Kiến trúc

```
PythonProject/
├── core/                          ← Business logic layer
│   ├── __init__.py
│   ├── audio_generator.py         ← Vieneu TTS: gen audio, adjust speed, voice clone
│   ├── audio_player.py            ← pygame.mixer: play/stop preview trong app
│   └── video_merger.py            ← ffmpeg: ghép audio vào video tại timestamp
├── gui/                           ← UI layer (tkinter)
│   ├── __init__.py
│   ├── app.py                     ← MainApp: Tk root + Notebook 3 tabs
│   ├── tab_gen_audio.py           ← Tab 1: nhập text + chọn giọng + tốc độ + clone → gen .mp3
│   ├── tab_merge_audio.py         ← Tab 2: chọn video + audio + start/end → ghép
│   ├── video_player_window.py     ← Cửa sổ preview popup: 640x360, play/pause, seek slider  
│   └── tab_voice_samples.py       ← Tab 3: danh sách giọng mẫu + phát thử 3 tốc độ
├── output/
│   ├── audio/                     ← File .mp3 đã gen (Tab 1)
│   ├── video/                     ← Video đã ghép (Tab 2)
│   └── samples/                   ← File mẫu cho Tab 3 + .cache/ (speed variants)
├── gui_audio_tool.py              ← Entry point
├── .venv/                         ← Virtual env (Python 3.12, GPU CUDA)
└── RUN.md                         ← Hướng dẫn chạy
```

## Modules chi tiết

### core/audio_generator.py
- `AudioGenerator.__init__()` → Khởi tạo `Vieneu()` v3 Turbo, auto GPU
- `voices` property → list 10 giọng preset
- `generate(text, voice_name, output_path, ref_audio=None, on_done, on_error)` → Threaded TTS + WAV→MP3
- `adjust_speed(input_path, speed_factor, output_path)` → Static, dùng ffmpeg atempo

### core/audio_player.py
- `AudioPlayer.__init__()` → `pygame.mixer.init()` 
- `play(path, on_finish)` → Phát async, callback khi kết thúc
- `stop()` → `fadeout(100ms)`
- `is_playing` property → poll từ UI

### core/video_merger.py
- `VideoMerger.__init__()` → `imageio_ffmpeg.get_ffmpeg_exe()`
- `get_video_info(path)` → duration, has_audio, width, height
- `merge(video_path, audio_path, start_sec, end_sec, output_path, on_done, on_error)` → Threaded
- Dùng filter_complex: volume=0 + adelay + amix

### gui/app.py
- 820x680, center màn hình
- 3 tabs: "Tạo âm thanh" | "Ghép vào video" | "Nghe giọng mẫu"
- Singleton: AudioPlayer, AudioGenerator, VideoMerger

### gui/tab_gen_audio.py
- Combobox chọn giọng (10 preset) + Combobox tốc độ (0.8x / 1.0x / 1.25x / 1.5x)
- Voice Cloning: chọn file WAV/MP3 3-5s → `ref_audio` → infer
- ScrolledText nhập text + nút "Tạo âm thanh" (threaded)
- Danh sách file đã gen (Listbox) + Phát thử / Dừng / Xóa / Mở thư mục
- Tự động điều chỉnh tốc độ sau gen nếu chọn speed ≠ 1.0

### gui/tab_merge_audio.py
- File dialog chọn video + audio
- Canvas thumbnail 320x180 khi chọn video
- "▶ Xem video" → mở VideoPlayerWindow popup (play/pause/seek)
- Entry "Từ giây" / "Đến giây"
- "Xem thông tin video" → duration, resolution, has_audio
- "Phát thử" audio preview
- "Ghép vào video" → Threaded ffmpeg + progress
- Sau thành công: hỏi mở file

### gui/video_player_window.py
- Toplevel riêng, kích thước động theo tỷ lệ video (mặc định 800x480)
- Resize được (bind Configure → redraw canvas)
- Play / Pause / Stop
- Seek slider độ chính xác 0.1s (giá trị float seconds)
- Hiển thị thời gian (phút:giây.1/10)
- Combobox tốc độ: 0.25x → 2.0x
- Tự động phát khi mở
- Giao diện tối theme (clam theme, #1e1e1e bg)
- Click/drag seek trực tiếp trên canvas video (hiện overlay thời gian)
- Timeline thumbnail strip dưới canvas (30 ảnh nhỏ) + playhead
- Click/drag seek trên timeline strip
- Nút nudge ◀◀ ▶▶ (tua 0.5s)
- Phím tắt: ← → (1 frame), ↑ ↓ (1s), Space (play/pause), J/K/L

### gui/tab_voice_samples.py
- Gen 11 file mẫu (10 giọng + Trúc Ly với `[cười]`) khi lần đầu chạy
- Mỗi giọng 3 nút: Chậm (0.8x) / Thường (1.0x) / Nhanh (1.25x)
- Speed variant cache: `output/samples/.cache/*.mp3`
- `[cười]` emotion cue cho Trúc Ly → giọng sáng hơn

## Dependencies
- vieneu==3.0.9 (v3 Turbo, 48 kHz)
- torch==2.6.0+cu124 (CUDA 12.4)
- imageio-ffmpeg (bundled ffmpeg)
- pygame==2.6.1 (audio playback)
- opencv-python-headless (video frame reading)
- transformers, onnxruntime, tokenizers

## GPU Requirements
- NVIDIA RTX 3050 6GB (tested)
- VRAM: ~2.1 GB khi infer, ~3.9 GB trống
- CUDA 12.4 required

## Voice Cloning
- Input: file WAV/MP3 3-5s (ref_audio)
- Dùng `tts.infer(text=..., voice=..., ref_audio=path)`
- Không cần transcript mẫu (zero-shot)

## Emotion Cues (v3 Turbo)
- `[cười]` - giọng tươi hơn
- `[thở dài]` - giọng trầm hơn
- `[hắng giọng]` - giọng rõ hơn
- Đặt trong text (experimental)

## Edge Cases & Notes
- Tab 3 speed cache: `output/samples/.cache/` bị ignore trong git
- Nếu chưa gen file mẫu → Tab 3 hiện nút "Tạo tất cả file mẫu"
- File output tự động đánh số `audio_001.mp3`, `audio_002.mp3`, ...
- Khi merge: video có audio cũ → tự động silence segment đó + mix audio mới
- Khi merge: video không audio → tự động thêm silent padding
- PYTHONIOENCODING=utf-8 bắt buộc trên Windows console (GUI không ảnh hưởng)
