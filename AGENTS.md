# AGENTS.md

Solo Python sandbox for a **Vietnamese "healing video" audio pipeline**:
SRT → Vieneu TTS voiceover WAV → mux into MP4 (+ optional ambient bed).

## Canonical spec — read first

`.skill/` is the single source of truth for all AI skills:
- `.skill/healing-audio-gen.md` — voiceover pipeline + ambient audio gen
  (11 hard rules `R1`–`R11`, emotion-tag benchmarks, mux params)
- `.skill/voiceover-pacing.md` — word rhythm & pacing for Vietnamese TTS
  (3-layer pause system, valley detection, inter-sentence gaps)

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

- `genSoundWow/create_audio_from_an_srt.py` — **production voiceover pipeline**
  (SRT → 21 s WAV). Reference implementation of R2/R3/R4/R9.
  **Note:** chưa có pacing — cần áp dụng `.skill/voiceover-pacing.md` (P1–P10)
  để thêm ngắt nhịp tự nhiên (valley detection + inter-sentence gap).
- `genSoundWow/test_voiceover.py` — QA checks for the generated WAV
  (sample rate, duration, peak/RMS, silence-in-gap alignment). Run after
  every voiceover regen.
- `adding_audio_to_video/adding_audio_to_video.py` — ffmpeg mux
  (`-c:v copy`, aac 192 k, 44.1 kHz, stereo; R8/R10).
  Mux cũng được document trong `.skill/voiceover-pacing.md` §6
  (`mux_voiceover()` + `mux_with_ambient()`).
- `main.py` — **throwaway scratch** for poking the Vieneu API. Not an
  entrypoint; line 5 references `list_preset_voices` without parens, ignore.
- `input/srt/`, `input/video/` — source assets.
- `output/wav/`, `output/video/` — intended sinks (currently empty).
- `voices.txt` — captured stdout of a one-off voice-listing run, not data.
- `m? t? video` (mojibake filename, CP-1252 content) — Vietnamese voice-direction
  notes for the demo clip. Leave the filename alone.

## Path gotcha (will bite on first run)

The scripts hard-code paths **relative to cwd**, and they don't match the
repo layout:

| Script expects (cwd-relative)              | Repo actually stores               |
| ------------------------------------------ | ---------------------------------- |
| `subtitles-21s.srt`                        | `input/srt/subtitles-21s.srt`      |
| `extended-horse-21s-fixed.mp4`             | `input/video/extended-horse-21s-fixed.mp4` |
| `outputs/voiceover_21s.wav`                | `output/wav/...` (note: `output`, not `outputs`) |
| `outputs/extended-horse-21s-with-voiceover.mp4` | `output/video/...`            |

Either edit the `Path(...)` constants, or stage a working dir that mirrors
what each script expects, or run with a custom cwd. **Don't silently
"refactor" all three scripts** — confirm with the user which layout wins.

## Working rules for agents

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

### Mux audio vào video (`.skill/voiceover-pacing.md` §6)

- Dùng `mux_voiceover(video_in, wav_in, video_out)` cho voiceover thuần.
- Dùng `mux_with_ambient(...)` nếu có nhạc nền drone/pink noise.
- LUÔN: `-c:v copy` (R8), AAC 192k / 44.1kHz / stereo (R10),
  pad/trim khớp duration video.
