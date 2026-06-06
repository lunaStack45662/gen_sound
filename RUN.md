# Hướng Dẫn Chạy Project

## Quy Trình 3 Bước

```
SRT ──[1]──→ voiceover.wav ──[2]──→ QA ──[3]──→ video.mp4 (có tiếng)
```

---

## Chuẩn Bị (chỉ làm 1 lần)

```powershell
# 1. Mở PowerShell trong thư mục project
cd d:\codePython\PythonProject

# 2. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 3. Set UTF-8 cho Python (bắt buộc khi in tiếng Việt)
$env:PYTHONIOENCODING = "utf-8"
```

---

## Bước 1: Sinh Voiceover Từ SRT

**Script:** `genSoundWow/create_audio_from_an_srt.py`

Script đọc file `subtitles-21s.srt` → gọi Vieneu TTS đọc từng câu → ghép lại thành 1 file WAV ~21s.

> ⚠️ **Lỗi path:** Script tìm file SRT ở thư mục hiện tại, nhưng file nằm trong `input/srt/`.
> Cần copy file trước khi chạy, hoặc sửa path trong script.

**Cách 1 — Copy file (nhanh, không sửa code):**
```powershell
# Copy file SRT ra thư mục gốc (nơi script tìm)
Copy-Item "input\srt\subtitles-21s.srt" -Destination "subtitles-21s.srt"

# Chạy script từ thư mục gốc
python genSoundWow\create_audio_from_an_srt.py
```

**Cách 2 — Sửa path trong script:**
```python
# genSoundWow/create_audio_from_an_srt.py — dòng 20
SRT_PATH = Path("../input/srt/subtitles-21s.srt")   # thay vì "subtitles-21s.srt"
OUTPUT_DIR = Path("../output/wav")                    # thay vì "outputs"
```

**Output:** `outputs/voiceover_21s.wav` (hoặc `output/wav/voiceover_21s.wav` nếu sửa path)

---

## Bước 2: Kiểm Tra Chất Lượng (QA)

**Script:** `genSoundWow/test_voiceover.py`

Chạy 15 bài test: sample rate, duration, clipping, silence alignment...

```powershell
# Cũng cần file SRT ở thư mục gốc (đã copy ở Bước 1)
python genSoundWow\test_voiceover.py
```

**Kết quả tốt:** Tất cả 15 checks đều PASS ✓

```
[PASS] File exists: outputs/voiceover_21s.wav
[PASS] Duration: 21.04s
[PASS] Sample rate: 24000
...
Results: 15 passed, 0 failed ✅
```

**Nếu có FAIL:** Xem phần Troubleshooting bên dưới.

---

## Bước 3: Ghép Audio Vào Video

**Script:** `adding_audio_to_video/adding_audio_to_video.py`

Ghép file voiceover WAV vào video MP4 bằng ffmpeg (copy video, encode audio AAC 192k).

> ⚠️ **Lỗi path:** Script tìm `extended-horse-21s-fixed.mp4` ở thư mục gốc.

```powershell
# Copy file video ra thư mục gốc
Copy-Item "input\video\extended-horse-21s-fixed.mp4" -Destination "extended-horse-21s-fixed.mp4"

# Chạy script
python adding_audio_to_video\adding_audio_to_video.py
```

**Output:** `outputs/extended-horse-21s-with-voiceover.mp4`

---

## Chạy Nhanh (tất cả 3 bước)

Nếu đã copy cả 2 file input ra thư mục gốc:

```powershell
$env:PYTHONIOENCODING = "utf-8"

# Bước 1: Sinh voiceover
python genSoundWow\create_audio_from_an_srt.py

# Bước 2: QA test
python genSoundWow\test_voiceover.py

# Bước 3: Ghép vào video
python adding_audio_to_video\adding_audio_to_video.py
```

---

## Troubleshooting

| Lỗi | Nguyên nhân | Cách sửa |
|-----|-------------|----------|
| `FileNotFoundError: subtitles-21s.srt` | Script tìm file SRT ở thư mục gốc | `Copy-Item "input\srt\subtitles-21s.srt" .` |
| `FileNotFoundError: extended-horse-21s-fixed.mp4` | Script tìm video ở thư mục gốc | `Copy-Item "input\video\extended-horse-21s-fixed.mp4" .` |
| `UnicodeEncodeError: 'charmap'` | Chưa set UTF-8 | `$env:PYTHONIOENCODING = "utf-8"` |
| `ModuleNotFoundError: No module named 'vieneu'` | Chưa activate venv | `.\.venv\Scripts\Activate.ps1` |
| QA test FAIL: duration | Voiceover quá dài/ngắn | Kiểm tra `MAX_DURATION` trong script |
| QA test FAIL: clipping | Âm thanh bị vỡ | Giảm `TARGET_PEAK` (mặc định 0.88) |
| `ffmpeg: command not found` | ffmpeg không trong PATH | Script dùng `imageio_ffmpeg.get_ffmpeg_exe()` — không cần cài ffmpeg riêng |

---

## Cấu Hình Mặc Định

| Tham số | Giá trị | Ghi chú |
|---------|---------|---------|
| Voice | `Bích Ngọc (nữ miền Bắc)` | Giọng nữ Bắc, sắc nét |
| Emotion tag | `<\|emotion_3\|>` | Cân bằng, pitch ~42Hz |
| Temperature | `0.95` | Dao động pitch tự nhiên |
| silence_p | `0.08` | It khoảng lặng trong audio |
| Sample rate | `24000` Hz | Mono |
| Video audio | AAC 192kbps, 44.1kHz, stereo | Sau khi mux |

---

## Cấu Trúc Thư Mục

```
PythonProject/
├── genSoundWow/
│   ├── create_audio_from_an_srt.py   ← [Bước 1] Sinh voiceover
│   └── test_voiceover.py             ← [Bước 2] QA test
├── adding_audio_to_video/
│   └── adding_audio_to_video.py      ← [Bước 3] Ghép audio → video
├── input/
│   ├── srt/subtitles-21s.srt         ← File phụ đề
│   └── video/extended-horse-21s-fixed.mp4  ← Video gốc
├── output/
│   ├── wav/                          ← Voiceover WAV
│   └── video/                        ← Video đã ghép audio
├── .skill/
│   ├── healing-audio-gen.md          ← Rules R1–R11
│   └── voiceover-pacing.md           ← Pacing P1–P10
├── .venv/                            ← Virtual environment
└── main.py                           ← Scratch file (không dùng)
```
