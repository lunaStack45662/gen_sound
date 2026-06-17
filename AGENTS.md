# AGENTS.md

Solo Python sandbox for a **Vietnamese "healing video" audio pipeline**:
SRT → Vieneu TTS voiceover WAV → mux into MP4 (+ optional ambient bed).

## Canonical spec — read first

`.skill/` is the single source of truth for all AI skills:
- `.skill/healing-audio-gen.md` — voiceover pipeline + ambient audio gen
  (11 hard rules `R1`–`R11`, emotion-tag benchmarks, mux params)
- `.skill/voiceover-pacing.md` — word rhythm & pacing for Vietnamese TTS
  (3-layer pause system, valley detection, inter-sentence gaps)
- `.skill/audio-mix.md` — mix voiceover + nhạc nền BGM
  (EQ carving, sidechain ducking tỉ lệ, verify 5 checks)

**Do not re-derive these — cite the rule ID when applying it.**

## Environment

- Python **3.14** in `.venv/` (created with virtualenv). Interpreter:
  `.venv\Scripts\python.exe`.
- No `requirements.txt` / `pyproject.toml` exists. Deps are only in the venv:
  `vieneu`, `soundfile`, `imageio-ffmpeg`, `numpy`, `scipy`, `librosa`.
  Do **not** invent a manifest unless asked.
- Shell is **PowerShell on Windows**. Before running any script that prints
  Vietnamese, set `$env:PYTHONIOENCODING="utf-8"` (R1 — else `UnicodeEncodeError`).
- **All files are UTF-8.** When reading/writing text files in Python, always
  pass `encoding="utf-8"`. All skill docs and SRT files are UTF-8 Vietnamese.
- No lint/test/format config and no CI. Don't fabricate commands.
- Use `imageio_ffmpeg.get_ffmpeg_exe()` instead of `ffmpeg` from PATH (R5).

## Layout & entrypoints

### Scripts (shared across all days)

- `genSoundWow/create_audio_from_an_srt.py` — **production voiceover pipeline**
  (SRT → WAV). Reference implementation of R2/R3/R4/R9.
  **Note:** chưa có pacing — cần áp dụng `.skill/voiceover-pacing.md` (P1–P10)
  để thêm ngắt nhịp tự nhiên (valley detection + inter-sentence gap).
- `genSoundWow/test_voiceover.py` — QA checks for the generated WAV.
  Run after every voiceover regen.
- `adding_audio_to_video/adding_audio_to_video.py` — simple ffmpeg mux
  (`-c:v copy`, aac 192 k, 44.1 kHz, stereo; R8/R10). Voiceover only, no BGM.
- `adding_audio_to_video/mix_audio.py` — **advanced mix**: voiceover + BGM
  (EQ carving, sidechain ducking tỉ lệ, verify 5 checks, mux).
  Reference implementation of M1–M8 (`.skill/audio-mix.md`).
- `main.py` — **throwaway scratch** for poking the Vieneu API. Ignore.
- `video_editor/trim_video.py` — **cắt video** (trim) từ timecode start → end.
  `-c copy` (fast) hoặc `--reencode` (chính xác đến frame).
- `video_editor/merge_videos.py` — **ghép nhiều video** (concat).
  concat demuxer (copy, mặc định) hoặc filter_complex (`--reencode`).

### Video-editing directories (riêng biệt với SRT pipeline)

```
input/
├── video-edit/               ← Video nguồn cho trim/merge
│   ├── clip1.mp4
│   ├── clip2.mp4
│   └── ...
└── ... (day-N/ giữ nguyên)

output/
├── video-edit/               ← Kết quả trim/merge
│   ├── clip1_trimmed.mp4
│   ├── merged.mp4
│   └── ...
└── ... (day-N/ giữ nguyên)
```

### Day-based structure

Mỗi ngày làm 1 video → assets tổ chức theo `day-N`:

```
input/
├── day-2/                    ← Ngày 2 (hôm nay)
│   ├── subtitles-21s.srt
│   └── extended_horse_21s.mp4
└── day-3/                    ← Ngày 3 (mai)
    ├── <srt file>
    └── <video file>

output/
├── day-2/                    ← Output ngày 2
│   ├── _log.md               ← Ghi lại nội dung đã làm (tránh trùng)
│   ├── voiceover_21s.wav
│   ├── extended-horse-21s-with-voiceover.mp4
│   └── 0010_day2.txt         ← Caption TikTok + gợi ý nhạc
└── day-3/
    └── ...
```

**Legacy dirs** (deprecated, sẽ xóa dần):
- `input/srt/`, `input/video/` — assets cũ trước day-2.
- `output/wav/`, `output/video/` — output cũ trước day-2.
- `outputs/` — script hardcode dir này (xem Path gotcha).

## Path gotcha (will bite on first run)

Scripts hard-code paths **relative to cwd**, không khớp repo layout:

| Script expects (cwd-relative)              | Repo actually stores               |
| ------------------------------------------ | ---------------------------------- |
| `subtitles-21s.srt`                        | `input/day-2/subtitles-21s.srt`    |
| `extended-horse-21s-fixed.mp4`             | `input/day-2/extended_horse_21s.mp4` |
| `outputs/voiceover_21s.wav`                | `output/day-2/...`                 |
| `outputs/extended-horse-21s-with-voiceover.mp4` | `output/day-2/...`            |

**Workaround hiện tại**: copy input files ra root trước khi chạy script,
rồi copy output vào `output/day-N/`. Cần refactor script để nhận path
argument thay vì hardcode.

## Working rules for agents

### Day-based workflow

- Mỗi ngày làm 1 video → tạo `input/day-N/` và `output/day-N/`.
- **LUÔN tạo `output/day-N/_log.md`** ghi lại: chủ đề, SRT text, video gốc,
  voice config, nhạc nền, caption. Đọc `_log.md` các ngày trước để KHÔNG trùng
  nội dung/chủ đề/nhạc nền.
- Đọc `input/day-N/` để biết assets, đọc `output/day-N/` để biết kết quả.

### Voiceover generation (`.skill/healing-audio-gen.md`)

- Treat §1 (R1–R11) and §6 (emotion-tag benchmarks) as binding.
  Defaults: voice `Bích Ngọc (nữ miền Bắc)`, `emotion_tag="<|emotion_3|>"`,
  `temperature=0.95`, `silence_p=0.08`, SR = 24000.
- Strip `, . — ; :` from SRT text before `tts.infer()` (R4). Keep the
  original punctuation in the SRT file itself.
- Never use `librosa.effects.time_stretch` on voiceover (R3). Truncate at
  `next_start` with no buffer (R9).
- Don't open `.wav` / `.mp4` with the Read tool (R7) — use `soundfile` /
  `wave` / ffmpeg probe.
- Vieneu output is deterministic for the same `(text, voice, emotion_tag,
  temperature)` tuple — change one of those to get a different take (R6).
- After any voiceover change, run `test_voiceover.py`; all 15 checks must
  pass before declaring done.

### Pacing & ngắt nhịp (`.skill/voiceover-pacing.md`)

- **LUÔN áp dụng pacing** khi sinh voiceover — không để 2 câu đọc liên tục.
- Treat §1.3 (P1–P10) as binding. Key rules:
  - `tts.infer()` gọi đúng **1 lần / câu SRT** (P9) — KHÔNG tách clause
    rồi gọi nhiều lần (timbre lệch, chậm).
  - Chèn pause bằng **valley detection**: tìm vùng nghỉ tự nhiên trong audio
    → chèn silence VÀO GIỮA vùng nghỉ + fade 10ms (P10).
  - Gap giữa 2 câu ≥ **300ms** (P2), sau câu hỏi `?` ≥ **800ms** (P3).
  - Phân loại chuyển ý: `strong` / `light` / `list` / `ending` (§3.1).
- Khi audio + gap vượt slot → `resolve_overflow()` (§5.2): giảm gap trước,
  rồi mới giảm micro pause.

### Mux voiceover vào video

- **KHÔNG có nhạc nền** → simple mux: `adding_audio_to_video.py`
  hoặc `voiceover-pacing.md` §6 (`mux_voiceover()`).
- **CÓ nhạc nền** → advanced mix: `mix_audio.py`
  hoặc `audio-mix.md` §2 (`mix_and_mux()`).
- LUÔN: `-c:v copy` (R8), AAC 192k / 44.1kHz / stereo (R10),
  pad/trim khớp duration video.

### Audio Mix — voiceover + nhạc nền (`.skill/audio-mix.md`)

- Treat §1 (M1–M8) as binding. Key rules:
  - Voiceover LUÔN là "ngôi sao", BGM chỉ hỗ trợ (M1).
  - EQ khoét mid 300-3kHz trên BGM → nhường chỗ giọng đọc (M2).
  - Sidechain duck **TỈ LỆ** (không on/off) — nhạc giảm theo giọng,
    KHÔNG tắt hẳn (M3). Attack 200ms + Release 1000ms (M6).
  - BGM volume mặc định -18dB so với voiceover peak (M4).
  - Fade out 3s cuối video (M5), normalize peak ≤ 0.95 (M8).
- Script: `adding_audio_to_video/mix_audio.py`
  (CLI: `--bgm`, `--bgm-db`, `--video`, `--voiceover`, `--output`).
- **Sau khi mix**: chạy `verify_mix()` — phải 5/5 checks pass trước khi giao.
