# AGENTS.md — Công cụ tạo audio và ghép video

## Tổng quan
Ứng dụng GUI (tkinter) giúp tạo file âm thanh từ text bằng AI (Vieneu v3 Turbo) và ghép audio vào video tại vị trí chỉ định. Chạy GPU NVIDIA CUDA 12.4.

## Kiến trúc

```
PythonProject/
├── assets/icons/                  ← 17 Material Design icons (PNG 48x48, white)
├── core/                          ← Business logic layer
│   ├── __init__.py
│   ├── audio_generator.py         ← Vieneu TTS: gen audio, adjust speed, voice clone
│   ├── audio_player.py            ← pygame.mixer: play/stop preview trong app
│   └── video_merger.py            ← ffmpeg: ghép audio vào video tại timestamp
├── gui/                           ← UI layer (tkinter)
│   ├── __init__.py
│   ├── app.py                     ← MainApp: Tk root + Notebook 3 tabs, gọi apply_theme()
│   ├── tab_gen_audio.py           ← Tab 1: nhập text + chọn giọng + tốc độ + clone → gen .mp3
│   ├── tab_merge_audio.py         ← Tab 2: chọn video → preview popup → ghép
│   ├── video_player/              ← Package preview popup
│   │   ├── __init__.py             ← Export VideoPlayerWindow
│   │   ├── window.py               ← UI orchestration (layout + events)
│   │   ├── player.py               ← VideoPlayer: OpenCV capture, play/pause/seek
│   │   ├── segments.py             ← SegmentManager: add/remove/edit/drag + preview playback
│   │   └── timeline.py             ← TimelineRenderer: thumbnails, playhead, segment bars
│   ├── video_player_window.py     ← Backward-compat re-export
│   ├── tab_voice_samples.py       ← Tab 3: danh sách giọng mẫu + phát thử 3 tốc độ
│   ├── theme.py                   ← Design tokens: COLORS (dark), FONTS, SPACING, SEGMENT_COLORS
│   ├── style.py                   ← apply_theme(): ttk.Style(clam) dark palette
│   ├── icons.py                   ← Icons class load Material Design PNG từ assets/icons/
│   └── tooltip.py                 ← add_tooltip(widget, text): tooltip sau 400ms hover
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
- `chain_merge(video_path, segments, output_path, on_done, on_error)` → Multi-segment merge
- `build_filter(video_path, segments, vid_dur)` → Tạo filter_complex string
- Dùng filter_complex: volume=0 + adelay + amix

### gui/app.py
- 820x680, center màn hình, dark theme (#0F1117)
- 3 tabs: "Tạo âm thanh" | "Ghép vào video" | "Nghe giọng mẫu"
- Singleton: AudioPlayer, AudioGenerator, VideoMerger
- Gọi `apply_theme()` từ gui/style.py

### gui/theme.py
- COLORS: bg_primary (#0F1117), bg_secondary, accent (#7C6FF7), text_primary, ...
- FONTS: heading, body, small, mono, tab
- SPACING: xs-xl (4→32px)
- SEGMENT_COLORS: 8 màu pastel cho segment bars

### gui/style.py
- `apply_theme(root)`: ttk.Style theme_use("clam")
- Cấu hình: Notebook, Frame (Card), Label (Heading/Secondary), Button (Secondary), Entry, Combobox, Scrollbar, Separator
- dark palette cho tất cả widget

### gui/icons.py
- `Icons.get(name, size=24)` → cached PhotoImage
- Load từ `assets/icons/{name}.png`, resize bằng Pillow.LANCZOS
- Dùng `image=` parameter cho ttk.Button thay `text=`

### gui/tooltip.py
- `add_tooltip(widget, text, delay=400)` → ToolTip instance
- Tạo Toplevel override-redirect khi hover Enter, huỷ khi Leave
- Style: bg #252836, fg #F1F1F3, font Segoe UI 9

### gui/tab_gen_audio.py
- Combobox chọn giọng (10 preset) + Combobox tốc độ (0.8x / 1.0x / 1.25x / 1.5x)
- Voice Cloning: chọn file WAV/MP3 3-5s → `ref_audio` → infer
- ScrolledText nhập text + nút "Tạo âm thanh" (threaded)
- Danh sách file đã gen (Listbox dark) + Phát thử / Dừng / Xóa / Mở thư mục (icon button + tooltip)
- Tự động điều chỉnh tốc độ sau gen nếu chọn speed ≠ 1.0

### gui/tab_merge_audio.py
- File dialog chọn video
- Canvas thumbnail 320x180 (theme border + placeholder text)
- "Xem video" button icon + tooltip → mở VideoPlayerWindow popup

### gui/video_player/window.py
- Toplevel riêng, kích thước động theo tỷ lệ video (mặc định 800x480)
- Canvas video dark, timeline dark (#1A1D27)
- Icon button: play/pause/stop/add/delete/merge + tooltip trên mỗi nút
- Resize được (bind Configure → redraw canvas)
- Play / Pause / Stop
- Click/drag seek trực tiếp trên canvas video (hiện overlay thời gian)
- Timeline thumbnail strip + audio track + playhead
- "+ Thêm audio" mở file dialog, tự động detect duration
- Kéo segment audio trên timeline để di chuyển
- Double-click: sửa start/end, Right-click: context menu xoá/sửa
- Phím Delete: xoá segment đang chọn
- Audio segment playback đồng bộ với video (dùng pygame.mixer.Sound)
- Combobox tốc độ: 0.25x → 2.0x
- Merge button icon + tooltip
- Phím tắt: ← → (1 frame), ↑ ↓ (1s), Space (play/pause), J/K/L
- Tự động phát khi mở (resume sau seek)
- Edit segment dialog (Toplevel dark, entry + button Lưu)

### gui/tab_voice_samples.py
- Gen 11 file mẫu (10 giọng + Trúc Ly với `[cười]`) khi lần đầu chạy
- Mỗi giọng 3 nút icon play → stop: Chậm (0.8x) / Thường (1.0x) / Nhanh (1.25x) + tooltip
- Speed variant cache: `output/samples/.cache/*.mp3`
- `[cười]` emotion cue cho Trúc Ly → giọng sáng hơn

## Dependencies
- vieneu==3.0.9 (v3 Turbo, 48 kHz)
- torch==2.6.0+cu124 (CUDA 12.4)
- imageio-ffmpeg (bundled ffmpeg)
- pygame==2.6.1 (audio playback)
- opencv-python-headless (video frame reading)
- Pillow (icon resize, image handling)
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
- Icons: Material Design white 48x48, cache trong Icons._cache dict
- Tooltip: Toplevel override-redirect, delay 400ms, font Segoe UI 9

## Merge Bugs Fixed (2026-06-29)
1. **amix halving audio**: `amix` default weights `1 1` halves output → thêm `,volume=2` post-mix
2. **atrim missing**: WAV played full duration, not trimmed to `insert_dur` → thêm `atrim=end={insert_dur}`
3. **has_audio=False branch missing atrim**: same fix as above
4. **vid_dur=0 silent failure**: nếu ffmpeg probe fail → `vid_dur=0` → output 0 giây → guard `if vid_dur <= 0: raise`
5. **Segment sort in chain merge**: segments processed in insertion order → corrupt overlap → `sort(key=lambda s: s["start"])`
6. **resume() không reset segments**: sau seek/edit → `_seg_triggered` còn ID cũ → segment không play → thêm `_reset_segments()` trong `resume()` và `_edit_segment.save()`

## UI Styling
- **Theme**: dark (#0F1117 bg), accent tím (#7C6FF7), ttk.Style clam
- **Icons**: 17 Material Design icons white 48x48 từ `assets/icons/`
- **Tooltip**: Toplevel override-redirect sau 400ms hover, bg #252836
- **Rounded corners**: dùng `gui/theme.round_rect()` vẽ canvas bo góc r=8
  - Segment bars trên timeline (r = min 5px)
  - Video canvas placeholder background (r=10)
  - Edit dialog buttons

## Tests
- `tests/test_merge_ffmpeg.py`: standalone ffmpeg merge test (3 test cases, has_audio/no_audio/silent stream)
- `tests/test_all_cases.py`: comprehensive 65 test cases covering:
  - basic has_audio/no_audio
  - edge positions (0, end, middle)
  - WAV shorter/longer than insert_dur
  - chain merge 2-3 segments, overlap
  - real user WAV files (mau_giong_nu_healing.wav, mau_giong_nam_healing.wav)
  - real video-34.mp4 + WAV nữ at 5.5s
  - edit validation rules
  - timeline pixel precision

## Commit History
- `49a1556` — refactor: split video_player_window.py into package, chain_merge in core
- `4b82efc` — feat: theme dark, icons material design, tooltip cho toàn bộ button
- `396cf00` — feat: bo góc segment + video canvas, tab icon
