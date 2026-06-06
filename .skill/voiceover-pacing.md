---
name: voiceover-pacing
description: >
  Hướng dẫn AI xử lý ngắt nhịp, khoảng dừng tự nhiên trong voiceover tiếng Việt
  khi dùng Vieneu TTS đọc phụ đề SRT cho video chữa lành (healing).
  Khắc phục lỗi 2 câu đọc liên tục không ngắt, giọng đều đều thiếu nhịp điệu.
compatibility: "requires: python3, vieneu, numpy, soundfile, imageio-ffmpeg"
---

# Voiceover Pacing — Ngắt Nhịp Tự Nhiên Cho Voiceover Tiếng Việt

> **Vấn đề**: Strip hết dấu câu (R4) + đặt clip liền nhau → 2 câu đọc liên tục, nghe robot.
> **Mục tiêu**: Giọng chậm rãi, nhịp nhàng, khoảng dừng tự nhiên giữa các câu.

---

## 1. Tổng Quan Pacing

### 1.1. Ba lớp ngắt nhịp

```
Layer 3  INTER-SENTENCE GAP    silence giữa 2 câu SRT     → §3
Layer 2  INTRA-SENTENCE PAUSE  mở rộng vùng nghỉ tại dấu phẩy/liên từ
Layer 1  MICRO PAUSE           mở rộng vùng nghỉ tại trạng ngữ/cụm ý
         ────────────────────────────────────────────────
         TẤT CẢ: TTS 1 LẦN/câu + valley detection        → §2
```

### 1.2. `silence_p` — pause nội bộ TTS

| `silence_p` | Hiệu ứng | Dùng khi |
|-------------|----------|----------|
| 0.00–0.05 | Đọc liên tục | Tin tức |
| **0.06–0.12** | **Tự nhiên** | **Healing — default 0.08** |
| 0.15–0.25 | Chậm rãi | Truyện kể |

### 1.3. Quy tắc cứng

| ID | Quy tắc | Vi phạm → |
|----|---------|-----------|
| **P1** | Phân loại chuyển ý giữa 2 câu trước khi đặt gap | 2 câu liên tục |
| **P2** | Gap tối thiểu giữa 2 câu = **300ms** | Nghe đọc tin |
| **P3** | Sau câu hỏi tu từ (`?`) → gap ≥ **800ms** | Mất suspense |
| **P4** | Câu > 8 từ → micro pause tại valley | Nghe hụt hơi |
| **P5** | Strip dấu TRƯỚC TTS, dùng SRT GỐC phân tích ngắt | TTS chèn pause 0.4s cứng |
| **P6** | Micro pause: 150–350ms, KHÔNG quá 500ms | Ngập ngừng |
| **P7** | Gap không ăn vào clip → truncate tại `next_start` (R9) | Mất từ cuối |
| **P8** | Câu cuối → gap "ending" (≥ 1s) nếu còn chỗ | Kết thúc hụt |
| **P9** | `tts.infer()` đúng **1 lần / câu**, pause bằng valley detection | Timbre lệch, chậm |
| **P10** | Silence chèn VÀO GIỮA vùng nghỉ + fade 10ms | Nghe "cắt dán" |

---

## 2. Pause Trong Câu (Layer 1 + 2)

> ⚠️ **Gọi `tts.infer()` 1 lần/câu** → tìm vùng nghỉ tự nhiên trong audio → chèn silence vào giữa.
> KHÔNG gọi nhiều lần: timbre/prosody không khớp, chậm ×N.

### 2.1. Điểm ngắt tự nhiên (phân tích từ SRT GỐC)

| Dấu hiệu | Ngắt? | Pause |
|----------|-------|-------|
| Dấu phẩy `,` | ✅ SAU từ đó | 280ms |
| Liên từ: nhưng, mà, và, hoặc, rồi… | ✅ TRƯỚC liên từ | 220ms |
| Trạng ngữ đầu câu: "Có khi nào", "Trong đầu"… | ✅ SAU trạng ngữ | 200ms |
| Giữa chủ ngữ + vị ngữ | ❌ KHÔNG | — |

### 2.2. Implementation

```python
import numpy as np

CONJUNCTIONS = {"nhưng", "mà", "và", "hoặc", "hay", "rồi", "nên", "vì", "bởi vì", "tuy", "dù"}
ADVERBIAL_STARTERS = {
    "có khi nào", "trong đầu", "khi đó", "lúc ấy", "bây giờ",
    "thực ra", "thật ra", "có lẽ", "có thể", "rõ ràng",
    "cuối cùng", "đầu tiên", "tóm lại",
}
MICRO_PAUSE = {"comma": 280, "conjunction": 220, "adverbial": 200}


def find_pause_points(original_text: str) -> list[tuple[int, float]]:
    """Phân tích SRT gốc (còn dấu câu) → list[(word_index, pause_sec)]."""
    words = original_text.split()
    pauses = []
    for i, w in enumerate(words):
        w_clean = w.strip(",.;:!?—").lower()
        if w.rstrip().endswith(","):
            pauses.append((i, MICRO_PAUSE["comma"] / 1000))
        elif w_clean in CONJUNCTIONS and i > 0:
            pauses.append((i - 1, MICRO_PAUSE["conjunction"] / 1000))
        elif i <= 2:
            prefix = " ".join(x.strip(",.;:!?—").lower() for x in words[:i+1])
            for starter in ADVERBIAL_STARTERS:
                if prefix.startswith(starter) or prefix == starter:
                    pauses.append((i, MICRO_PAUSE["adverbial"] / 1000))
                    break
    return pauses


def find_natural_pause(audio, center, sr, search_ms=300, window_ms=30):
    """Tìm VÙNG nghỉ tự nhiên (start, end) quanh center — không chỉ 1 điểm."""
    search = int(search_ms * sr / 1000)
    win = int(window_ms * sr / 1000)
    step = win // 4
    lo = max(0, center - search)
    hi = min(len(audio) - win, center + search)
    if hi <= lo:
        return center, center + 1
    energies, positions = [], []
    for s in range(lo, hi, step):
        energies.append(float(np.sum(audio[s:s+win] ** 2)))
        positions.append(s)
    if not energies:
        return center, center + 1
    threshold = max(energies) * 0.15  # < 15% peak = "đang nghỉ"
    best_start, best_end, min_dist = center, center + 1, float("inf")
    i = 0
    while i < len(energies):
        if energies[i] < threshold:
            rs = positions[i]
            j = i
            while j < len(energies) and energies[j] < threshold:
                j += 1
            re = positions[min(j, len(positions)-1)] + win
            if abs((rs + re) / 2 - center) < min_dist:
                min_dist = abs((rs + re) / 2 - center)
                best_start, best_end = rs, re
            i = j
        else:
            i += 1
    return best_start, best_end


def insert_pauses_into_audio(audio, original_text, sr=24000):
    """Mở rộng vùng nghỉ tự nhiên của TTS + fade 10ms tránh click."""
    pauses = find_pause_points(original_text)
    if not pauses:
        return audio
    n_words = max(len(original_text.split()), 1)
    fade_len = int(0.01 * sr)  # 10ms
    result = audio.copy()
    for word_idx, pause_sec in reversed(pauses):  # CUỐI→ĐẦU để không lệch index
        est = int((word_idx + 1) / n_words * len(result))
        vs, ve = find_natural_pause(result, est, sr)
        mid = (vs + ve) // 2
        # Fade-out trước điểm chèn
        fo_s = max(0, mid - fade_len)
        result[fo_s:fo_s + fade_len] *= np.sqrt(np.linspace(1, 0, fade_len))
        # Fade-in sau điểm chèn
        fi_e = min(mid + fade_len, len(result))
        if fi_e > mid:
            result[mid:fi_e] *= np.sqrt(np.linspace(0, 1, fade_len))[:fi_e - mid]
        # Chèn silence VÀO GIỮA vùng nghỉ
        result = np.concatenate([
            result[:mid],
            np.zeros(int(pause_sec * sr), dtype=np.float32),
            result[mid:],
        ])
    return result


def tts_sentence(original_text, tts, voice_data, **kwargs):
    """TTS 1 lần + chèn micro pause. KHÔNG gọi infer() nhiều lần."""
    clean = " ".join(original_text.replace(",", " ").replace(".", " ")
                     .replace("—", " ").replace(";", " ").replace(":", " ").split())
    audio = tts.infer(text=clean, voice=voice_data, **kwargs)
    return insert_pauses_into_audio(audio, original_text)
```

> **Tại sao "mở rộng vùng nghỉ" thay vì chèn silence tại 1 điểm?**
> TTS với `silence_p > 0` đã có micro-pause tự nhiên (50–100ms). Chèn THÊM vào giữa
> → nghe như "giọng nghỉ lâu hơn", không phải "cắt rồi dán silence".

---

## 3. Gap Giữa Các Câu (Layer 3)

Đây là layer **quan trọng nhất** — thiếu = 2 câu liên tục như đọc tin.

### 3.1. Phân loại chuyển ý

| Ngữ cảnh | Gap | Loại |
|----------|-----|------|
| Liệt kê cùng ý | 350ms | `list` |
| Chuyển ý nhẹ | 550ms | `light` |
| Câu hỏi tu từ / "nhưng", "thực ra"… | 900ms | `strong` |
| Câu cuối cùng | 1200ms | `ending` |

```python
GAP_PRESETS = {"strong": 0.9, "light": 0.55, "list": 0.35, "ending": 1.2}

def classify_transition(prev_text, curr_text):
    if prev_text.strip().endswith("?"):
        return "strong"
    strong_markers = {"nhưng", "tuy nhiên", "vấn đề là", "thực ra", "thật ra"}
    if any(curr_text.lower().strip().startswith(m) for m in strong_markers):
        return "strong"
    prev_w, curr_w = set(prev_text.lower().split()), set(curr_text.lower().split())
    if len(prev_w & curr_w) >= 2 and len(prev_text.split()) <= 6:
        return "list"
    return "light"
```

### 3.2. Ghép clips vào master buffer

```python
master = np.zeros(int(MAX_DUR * SR), dtype=np.float32)
for i, (start, audio) in enumerate(clips):
    gap_type = "ending" if i == len(clips)-1 \
               else classify_transition(entries[i-1][2], entries[i][2]) if i > 0 \
               else "light"
    gap_sec = GAP_PRESETS[gap_type]
    offset = int((start + gap_sec) * SR)
    boundary = int((entries[i+1][0] if i+1 < len(entries) else MAX_DUR) * SR)
    end = min(offset + len(audio), boundary, len(master))
    master[offset:end] = audio[:end - offset]
```

---

## 4. Template Hoàn Chỉnh

```python
import os
os.environ["PYTHONIOENCODING"] = "utf-8"   # R1

import re, numpy as np, soundfile as sf
from scipy import signal
from pathlib import Path
from vieneu import Vieneu

# === CONFIG ===
SRT_PATH = Path("input/srt/subtitles-21s.srt")
OUT_WAV  = Path("output/wav/voiceover_21s.wav")
SR, MAX_DUR = 24000, 21.0
VOICE, EMOTION_TAG = "Bích Ngọc (nữ miền Bắc)", "<|emotion_3|>"
TEMPERATURE, SILENCE_P = 0.95, 0.08
GAP_PRESETS = {"strong": 0.9, "light": 0.55, "list": 0.35, "ending": 1.2}
MICRO_PAUSE = {"comma": 280, "conjunction": 220, "adverbial": 200}
CONJUNCTIONS = {"nhưng", "mà", "và", "hoặc", "hay", "rồi", "nên", "vì", "bởi vì", "tuy", "dù"}
ADVERBIAL_STARTERS = {"có khi nào", "trong đầu", "khi đó", "lúc ấy", "bây giờ",
    "thực ra", "thật ra", "có lẽ", "có thể", "rõ ràng", "cuối cùng", "đầu tiên", "tóm lại"}

# === Hàm pacing (copy từ §2.2) ===
def find_pause_points(text): ...      # §2.2
def find_natural_pause(a, c, sr): ... # §2.2
def insert_pauses_into_audio(a, t, sr): ... # §2.2
def tts_sentence(text, tts, vd, **kw): ...  # §2.2
def classify_transition(prev, curr): ...    # §3.1

# === PARSE SRT ===
def parse_srt(p):
    entries = []
    for block in re.split(r"\n\s*\n", p.read_text(encoding="utf-8").strip()):
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if len(lines) < 2: continue
        m = re.match(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})", lines[1])
        if not m: continue
        sh,sm,ss,sms,eh,em,es,ems = map(int, m.groups())
        entries.append((sh*3600+sm*60+ss+sms/1000, eh*3600+em*60+es+ems/1000, " ".join(lines[2:])))
    return entries

# === MAIN ===
tts = Vieneu(emotion="natural")
voice_data = tts.get_preset_voice(dict(tts.list_preset_voices())[VOICE])
entries = parse_srt(SRT_PATH)

# TTS 1 lần/câu + micro pause
clips = []
for s, e, text in entries:
    audio = tts_sentence(text, tts, voice_data,
        temperature=TEMPERATURE, top_k=50, silence_p=SILENCE_P,
        apply_watermark=False, emotion_tag=EMOTION_TAG)
    clips.append((s, audio))

# Ghép với inter-sentence gap (Layer 3)
master = np.zeros(int(MAX_DUR * SR), dtype=np.float32)
for i, (start, audio) in enumerate(clips):
    gap_type = "ending" if i == len(clips)-1 \
               else classify_transition(entries[i-1][2], entries[i][2]) if i > 0 else "light"
    offset = int((start + GAP_PRESETS[gap_type]) * SR)
    boundary = int((entries[i+1][0] if i+1 < len(entries) else MAX_DUR) * SR)
    end = min(offset + len(audio), boundary, len(master))
    master[offset:end] = audio[:end - offset]

# EQ + normalize + crossfade
sos_hp = signal.butter(4, 80, btype="highpass", fs=SR, output="sos")
master = signal.sosfilt(sos_hp, master)
peak = np.max(np.abs(master))
master = master * (0.88 / peak) if peak > 0 else master
fade = int(0.04 * SR)
for i in range(1, len(clips)):
    b = int(clips[i][0] * SR)
    if b < fade or b + fade > len(master): continue
    t = np.linspace(0, np.pi / 2, fade)
    master[b-fade:b] *= np.cos(t)
    master[b:b+fade] *= np.sin(t)

# Export
OUT_WAV.parent.mkdir(parents=True, exist_ok=True)
sf.write(OUT_WAV, master, SR, subtype="PCM_16")
print(f"[OK] {OUT_WAV}  ({len(master)/SR:.2f}s)")
```

---

## 5. Troubleshooting

### 5.1. Chẩn đoán nhanh

| Triệu chứng | Fix |
|-------------|-----|
| 2 câu liên tục không ngừng | Thêm `classify_transition()` + GAP_PRESETS (§3) |
| Câu dài hụt hơi | Dùng `insert_pauses_into_audio()` + valley (§2) |
| Ngắt quá nhiều, ngập ngừng | Giảm gap, chỉ giữ comma + conjunction |
| Mất từ cuối câu | `resolve_overflow()` bên dưới |
| Giọng 2 đoạn không khớp | TTS 1 lần/câu (P9) |
| Nghe "cắt dán" | Fade 10ms + chèn VÀO GIỮA vùng nghỉ (P10) |
| Pause dấu phẩy cứng 0.4s | Strip dấu TRƯỚC TTS (P5) |

### 5.2. Xử lý overflow (gap + audio > slot)

```python
def resolve_overflow(audio, gap_sec, slot_sec, sr=24000):
    audio_sec = len(audio) / sr
    if audio_sec + gap_sec <= slot_sec:
        return gap_sec
    new_gap = max(slot_sec - audio_sec, 0.2)
    return new_gap if new_gap >= 0.2 else 0.0
```

Thứ tự ưu tiên: giảm gap → tăng `silence_p` → giảm micro pause → bỏ gap.

### 5.3. Tuning theo mood

| Mood | Điều chỉnh |
|------|-----------|
| Suy tư, trầm lắng | gap ×1.3, SILENCE_P = 0.10 |
| Năng động | gap ×0.7, SILENCE_P = 0.06 |
| Kể chuyện | Mặc định |

---

## 6. Ghép Vào Video (Mux) + Checklist

### 6.1. Mux voiceover → video

```python
import subprocess, wave
from pathlib import Path
import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()   # R5

def get_video_duration(path):
    r = subprocess.run([FFMPEG, "-i", str(path), "-hide_banner"],
                       capture_output=True, text=True)
    for line in r.stderr.splitlines():
        if "Duration:" in line:
            t = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = t.split(":")
            return int(h)*3600 + int(m)*60 + float(s)
    raise RuntimeError("Không parse được video duration")

def mux_voiceover(video_in, wav_in, video_out):
    v_dur = get_video_duration(video_in)
    video_out.parent.mkdir(parents=True, exist_ok=True)
    if video_out.exists(): video_out.unlink()
    cmd = [
        FFMPEG, "-y", "-hide_banner", "-loglevel", "warning",
        "-i", str(video_in), "-i", str(wav_in),
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "copy",              # R8
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",  # R10
        "-af", f"apad=pad_dur={v_dur:.3f},atrim=0:{v_dur:.3f},asetpts=PTS-STARTPTS",
        "-shortest", "-movflags", "+faststart", str(video_out),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(r.returncode)
    print(f"[OK] {video_out}  ({video_out.stat().st_size/1024**2:.2f} MB)")
```

### 6.2. Mux có ambient bed (tuỳ chọn)

```python
def mux_with_ambient(video_in, voiceover_wav, ambient_wav, video_out, ambient_db=-18.0):
    v_dur = get_video_duration(video_in)
    cmd = [
        FFMPEG, "-y", "-hide_banner", "-loglevel", "warning",
        "-i", str(video_in), "-i", str(voiceover_wav), "-i", str(ambient_wav),
        "-map", "0:v:0",
        "-filter_complex",
        f"[2:a]volume={ambient_db}dB[amb];"
        f"[1:a][amb]amix=inputs=2:duration=first:dropout_transition=2,"
        f"apad=pad_dur={v_dur:.3f},atrim=0:{v_dur:.3f},asetpts=PTS-STARTPTS[mixed]",
        "-map", "[mixed]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
        "-movflags", "+faststart", str(video_out),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(r.returncode)
```

### 6.3. Paths chuẩn

```python
VIDEO_IN    = Path("input/video/extended-horse-21s-fixed.mp4")
WAV_IN      = Path("output/wav/voiceover_21s.wav")
AMBIENT_WAV = Path("output/wav/ambient_calm.wav")   # optional
VIDEO_OUT   = Path("output/video/extended-horse-21s-with-voiceover.mp4")
```

### 6.4. Checklist

**Voiceover WAV:**
- [ ] Mỗi cặp câu có gap ≥ 300ms
- [ ] Câu hỏi tu từ có gap ≥ 800ms
- [ ] Không truncate mất từ cuối
- [ ] Micro pause tại valley + fade 10ms (P9, P10)
- [ ] `tts.infer()` gọi 1 lần/câu
- [ ] QA test pass 15/15

**Mux Video:**
- [ ] `imageio_ffmpeg.get_ffmpeg_exe()` (R5)
- [ ] `-c:v copy` (R8), AAC 192k/44.1kHz/stereo (R10)
- [ ] Audio pad/trim khớp video duration
- [ ] Nghe thử: voice khớp hình, không trễ
