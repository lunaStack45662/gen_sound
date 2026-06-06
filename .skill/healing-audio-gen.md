---
name: healing-audio-gen
description: >
  Sinh audio cho video chữa lành (healing psychology) bằng tiếng Việt:
  (1) Voiceover từ file .srt với TTS Vieneu, (2) Âm nền drone/pink noise/binaural.
  Skill này document toàn bộ bugs đã gặp và fix từ production pipeline 21s voiceover.
  Thư viện bắt buộc: vieneu, wave, soundfile, imageio_ffmpeg, numpy — optional: scipy, librosa.
compatibility: "requires: python3, vieneu, soundfile, imageio-ffmpeg, numpy — optional: scipy, librosa"
---

# Healing Audio Gen Skill

Sinh audio chất lượng cao phục vụ **video chữa lành tiếng Việt**, gồm 2 luồng chính:
- **Voiceover** từ phụ đề `.srt` (dùng Vieneu TTS)
- **Âm nền** drone/pink noise/binaural beats

> Triết lý: Video chữa lành cần **sự thuần khiết** — không artifact, không "lag", giọng đồng nhất.

---

## 1. Yêu Cầu Bắt Buộc (Hard Requirements)

> ⚠️ Các yêu cầu này rút ra từ bugs đã fix trong production. **Bỏ qua = output hỏng.**

| ID | Yêu cầu | Nếu vi phạm |
|----|---------|-------------|
| **R1** | Trên Windows, **LUÔN set `PYTHONIOENCODING=utf-8`** trước khi chạy script có in tiếng Việt | UnicodeEncodeError cp1252 |
| **R2** | Khi dùng Vieneu TTS, **LUÔN pass `emotion_tag` rõ ràng** (`<\|emotion_N\|>`) trong `tts.infer()` | Giọng phẳng vì `emotion="storytelling"` thực ra set `default_emotion=None` |
| **R3** | **KHÔNG** dùng `librosa.effects.time_stretch` cho voiceover — gây phase-vocoder artifact, đổi timbre | Người dùng nghe "giọng khác" từ giây 7+ |
| **R4** | **LUÔN bỏ dấu `,` `.` `—` `;` `:`** trong text truyền cho TTS (giữ nguyên SRT gốc) | TTS chèn pause 0.4s tại dấu phẩy → cảm giác "lag" |
| **R5** | Khi cần ffmpeg, dùng `imageio_ffmpeg.get_ffmpeg_exe()` thay vì gọi `ffmpeg` CLI trực tiếp | `WinError 2` trên Windows không có ffmpeg trong PATH |
| **R6** | Trước khi commit emotion tag, **generate 4-12 sample trên 1 câu** rồi đo `f0_std`, `spectral_flux`, `HNR` để chọn tag tối ưu | Chọn sai tag → giọng quá phẳng hoặc quá kịch tính |
| **R7** | **KHÔNG** dùng Read tool cho file binary (.wav, .mp4) — dùng Python `wave.open()` / `soundfile` | Read tool fail: `Cannot read binary file` |
| **R8** | Khi mux audio vào video, **LUÔN `-c:v copy`** (không re-encode video) | Re-encode chậm + mất chất lượng video |
| **R9** | Truncate audio tại **`next_start`** (không buffer 50ms) để liền mạch giữa 2 câu | Test silence FAIL, có "lag" ở boundary |
| **R10** | Match audio params với video gốc: `-ar 44100 -ac 2 -b:a 192k` | Video output không tương thích player |
| **R11** | Khi ghép audio dài hơn slot, **KHÔNG truncate tại slot_end** (mất nội dung) — chọn 1 trong: truncate tại `next_start`, hoặc split tại dấu phẩy | Mất từ cuối câu |

---

## 2. Quy Trình Tổng Quan

### 2.1. Voiceover từ SRT (workflow chính)

```
SRT file  →  Parse  →  TTS từng câu  →  Strip dấu câu  →  Pre-process text
                                              ↓
                                       Ghép theo timing SRT
                                              ↓
                                       EQ + normalize + crossfade
                                              ↓
                                       voiceover_XXs.wav  →  Mux vào video
```

### 2.2. Âm nền healing (drone/pink noise)

```
Mood + duration  →  Sinh layers (drone, pink, binaural, breath)
                          ↓
                   Mix + fade in/out + normalize
                          ↓
                   background_XXm.wav
```

---

## 3. Voiceover Từ SRT — Implementation Chuẩn

### 3.1. Parse SRT

```python
import re
from pathlib import Path

def parse_srt(path: Path) -> list[tuple[float, float, str]]:
    content = path.read_text(encoding="utf-8")
    entries = []
    for block in re.split(r"\n\s*\n", content.strip()):
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if len(lines) < 2: continue
        m = re.match(
            r"(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})",
            lines[1],
        )
        if not m: continue
        sh, sm, ss, sms, eh, em, es, ems = map(int, m.groups())
        start = sh*3600 + sm*60 + ss + sms/1000
        end   = eh*3600 + em*60 + es + ems/1000
        text  = " ".join(lines[2:])
        entries.append((start, end, text))
    return entries
```

### 3.2. Khởi tạo Vieneu — **ĐÚNG CÁCH**

```python
from vieneu import Vieneu

# ⚠️ R2: "natural" map sang emotion_0, các giá trị khác đều set None
#        → PHẢI pass emotion_tag="<|emotion_N|>" trong infer() thay vì dựa vào emotion="storytelling"
tts = Vieneu(emotion="natural")   # init: chỉ để warmup model
voices = dict(tts.list_preset_voices())
voice_data = tts.get_preset_voice(voices["Bích Ngọc (nữ miền Bắc)"])
```

### 3.3. Sinh audio từng câu — **STRIP DẤU CÂU**

```python
# ⚠️ R4: TTS tự chèn pause 0.4s tại dấu phẩy → strip trước khi gọi TTS
def strip_punct(text: str) -> str:
    return " ".join(text.replace(",", " ")
                       .replace(".", " ")
                       .replace("—", " ")
                       .replace(";", " ")
                       .replace(":", " ")
                       .split())

EMOTION_TAG = "<|emotion_3|>"    # xem §6 để chọn
TEMPERATURE = 0.95
SILENCE_P   = 0.08               # thấp → ít pause tự nhiên

for idx, (start, end, text) in enumerate(entries, 1):
    tts_text = strip_punct(text)
    audio = tts.infer(
        text=tts_text,
        voice=voice_data,
        temperature=TEMPERATURE,
        top_k=50,
        silence_p=SILENCE_P,
        apply_watermark=False,
        emotion_tag=EMOTION_TAG,   # ⚠️ R2: bắt buộc
    )
    clips.append((start, audio))
```

### 3.4. Ghép theo timing — **KHÔNG TIME-STRETCH**

```python
import numpy as np

# ⚠️ R3 + R9: KHÔNG dùng librosa.effects.time_stretch
#              Truncate tại next_start (không buffer)
def fit_to_slot(audio: np.ndarray, slot_sec: float) -> np.ndarray:
    """Không time-stretch: trả về audio gốc để giữ timbre đồng nhất."""
    return audio

total_samples = int(MAX_DURATION * SR)
master = np.zeros(total_samples, dtype=np.float32)

for i, (start, audio) in enumerate(clips):
    next_start = entries[i+1][0] if i+1 < len(entries) else MAX_DURATION
    offset = int(start * SR)
    boundary_sample = int(next_start * SR)   # ⚠️ R9: KHÔNG buffer 50ms
    max_end = min(offset + len(audio), boundary_sample, total_samples)
    audio = audio[: max_end - offset]
    master[offset:offset + len(audio)] = audio
```

### 3.5. EQ sharpen + normalize + crossfade

```python
from scipy import signal

# High-pass 80Hz (bỏ rumble) + high-shelf +4dB @ 2.5kHz + presence +2.5dB @ 5kHz
def sharpen_audio(x, sr=24000):
    sos_hp = signal.butter(4, 80, btype="highpass", fs=sr, output="sos")
    x = signal.sosfilt(sos_hp, x.astype(np.float32))
    # ... high-shelf + peaking EQ coefficients theo Audio EQ Cookbook
    return x

master = sharpen_audio(master)
peak = np.max(np.abs(master))
master = master * (0.88 / peak) if peak > 0 else master

# Crossfade 40ms tại boundary giữa các câu
fade_samples = int(0.04 * SR)
for i in range(1, len(clips)):
    boundary = int(clips[i][0] * SR)
    master[boundary-fade_samples: boundary] *= np.linspace(1, 0, fade_samples)
    master[boundary: boundary+fade_samples] *= np.linspace(0, 1, fade_samples)
```

### 3.6. Export WAV

```python
import soundfile as sf
sf.write("outputs/voiceover_21s.wav", master, 24000, subtype="PCM_16")
```

---

## 4. Mux Audio Vào Video — Implementation Chuẩn

```python
import subprocess
import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()   # ⚠️ R5: lấy binary từ package

cmd = [
    FFMPEG, "-y", "-hide_banner", "-loglevel", "warning",
    "-i", "video_in.mp4",
    "-i", "voiceover.wav",
    "-map", "0:v:0",      # video stream từ input 0
    "-map", "1:a:0",      # audio stream từ input 1
    "-c:v", "copy",       # ⚠️ R8: không re-encode video
    "-c:a", "aac",
    "-b:a", "192k",
    "-ar", "44100",        # ⚠️ R10: match video gốc
    "-ac", "2",
    "-af", f"apad=pad_dur={v_dur:.3f},atrim=0:{v_dur:.3f},asetpts=PTS-STARTPTS",
    "-shortest",
    "-movflags", "+faststart",
    "video_out.mp4",
]
subprocess.run(cmd, check=True)
```

---

## 5. Âm Nền Healing (Drone/Pink Noise/Binaural)

### 5.1. Config theo mood

| Mood | BASE_FREQ | BINAURAL_OFFSET | Noise | Fade out |
|------|-----------|-----------------|-------|----------|
| `calm` | 432 Hz | 8 Hz (alpha) | 0.12 | 3s |
| `sleepy` | 396 Hz | 4 Hz (delta) | 0.08 | 5s |
| `grounding` | 528 Hz | 6 Hz (theta) | 0.15 | 3s |
| `uplifting` | 528 Hz | 10 Hz | 0.10 | 2s |
| `anxiety relief` | 417 Hz | 7 Hz | 0.20 | 4s |

### 5.2. Sinh layers

```python
import numpy as np

SR = 44100
t = np.linspace(0, duration_sec, int(SR * duration_sec))

# Layer 1: Drone (sine + harmonic)
drone = (np.sin(2*np.pi*432*t)*0.3 +
         np.sin(2*np.pi*432*2*t)*0.1)

# Layer 2: Pink noise (1/f noise — tự nhiên hơn white)
white = np.random.randn(len(t))
fft = np.fft.rfft(white)
freqs = np.fft.rfftfreq(len(t), 1/SR); freqs[0] = 1
pink = np.fft.irfft(fft / np.sqrt(freqs), n=len(t))
pink = pink / np.max(np.abs(pink)) * 0.12

# Layer 3: Binaural beats (tai trái vs phải)
left  = np.sin(2*np.pi*200*t)*0.2
right = np.sin(2*np.pi*(200+offset_hz)*t)*0.2

# Layer 4: Breath envelope (1 chu kỳ / 8s)
breath = (np.sin(2*np.pi*(1/8)*t) + 1) / 2
texture = pink * breath * 0.4
```

### 5.3. Mix + envelope + export

```python
# Mix
mono = drone + pink*0.3 + texture*0.25
stereo = np.stack([mono+left, mono+right], axis=1)

# Equal-power fade (sqrt curve — tự nhiên hơn linear)
def fade(audio, sr, fi=2.0, fo=3.0):
    n = len(audio)
    fi_s, fo_s = int(fi*sr), int(fo*sr)
    ic = np.sqrt(np.linspace(0, 1, fi_s))
    oc = np.sqrt(np.linspace(1, 0, fo_s))
    r = audio.copy()
    r[:fi_s] *= ic[:, None]
    r[n-fo_s:] *= oc[:, None]
    return r

stereo = fade(stereo, SR)
peak = np.max(np.abs(stereo))
stereo = stereo * (0.85 / peak) if peak > 0 else stereo

from soundfile import SoundFile
with SoundFile("outputs/healing_5min.wav", "w", SR, 2, "PCM_24") as f:
    f.write(stereo.astype(np.float32))
```

---

## 6. Chọn Emotion Tag Cho Vieneu TTS

Vieneu có 20 emotion tags (`emotion_0` → `emotion_19`) nhưng **không có docs đầy đủ**. Phương pháp chọn:

### 6.1. Test nhanh bằng f0_std + flux + HNR

```python
def analyze(wav_path):
    import librosa, numpy as np
    y, _ = librosa.load(wav_path, sr=24000, mono=True)
    f0, _, _ = librosa.pyin(y, fmin=60, fmax=400, sr=24000,
                              frame_length=2048, hop_length=512)
    f0v = f0[~np.isnan(f0)]
    f0_std = float(np.std(f0v)) if len(f0v) else 0
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=512))
    flux = float(np.mean(np.sqrt(np.sum(np.diff(S, axis=1)**2, axis=0))))
    harm, perc = librosa.effects.hpss(y)
    hnr = float(10*np.log10((np.mean(harm**2)+1e-12)/(np.mean(perc**2)+1e-12)))
    return f0_std, flux, hnr
```

### 6.2. Tiêu chí chọn

| Metric | Ý nghĩa | Mong muốn |
|--------|---------|-----------|
| `f0_std_hz` | dao động pitch (cao = bùng nổ) | **35-50 Hz** cho voiceover cảm xúc |
| `spectral_flux` | tốc độ đổi sắc thái (cao = mượt) | **> 35** |
| `hnr_db` | tỉ số harmonics/noise (cao = sạch) | **> 4 dB** |

### 6.3. Kết quả benchmark (đã test)

| Tag | t=0.95 f0_std | t=1.20 f0_std | Đánh giá |
|-----|---------------|---------------|----------|
| emotion_0 | 28.7 | 32.8 | 😐 phẳng (default) |
| emotion_1 | 34.0 | 62.2 | ⚠️ quá kịch tính ở t=1.2 |
| emotion_2 | 38.9 | 36.8 | trầm, ổn |
| **emotion_3** | **41.7** | 32.7 | ⭐ **cân bằng — recommended** |
| emotion_4 | 33.6 | 40.4 | thiếu bùng |
| emotion_5 | 45.1 | 35.4 | bùng nổ nhưng có thể quá |

**Khuyến nghị mặc định:** `emotion_3` + `temperature=0.95` (an toàn, cân bằng).

---

## 7. Lỗi Thường Gặp & Fix (Production Incidents)

| # | Lỗi | Nguyên nhân | Fix | Yêu cầu |
|---|------|-------------|-----|---------|
| 1 | `UnicodeEncodeError: 'charmap' codec can't encode` | Windows console mặc định cp1252 | `$env:PYTHONIOENCODING="utf-8"` trước khi chạy Python | R1 |
| 2 | Read tool fail trên file .wav | Read chỉ hỗ trợ text | Dùng `wave.open()` + `numpy` để đọc | R7 |
| 3 | Giọng "dè" (phẳng) mặc dù set `emotion="storytelling"` | Vieneu chỉ map `"natural"→emotion_0`, còn lại → `None` | Pass `emotion_tag="<\|emotion_3\|>"` trong `infer()` | R2 |
| 4 | Từ giây 7 trở đi "giọng khác" | `librosa.effects.time_stretch` gây phase-vocoder artifact | Tắt time-stretch, truncate tại `next_start` | R3, R9 |
| 5 | "Lag" / stutter giữa câu 3 | TTS tự chèn pause 0.4s tại dấu `,` | Strip dấu `,` `.` `—` trong text trước khi TTS | R4 |
| 6 | `WinError 2: ffmpeg not found` | ffmpeg không có trong PATH | `pip install imageio-ffmpeg` + dùng `imageio_ffmpeg.get_ffmpeg_exe()` | R5 |
| 7 | 2/15 silence test FAIL ở gap 10-10.2s, 16.95-17.2s | Câu 3, 5 dài hơn slot, tràn vào gap | Strip dấu câu → câu ngắn lại → fit trong slot | R4, R11 |
| 8 | File wav cũ giống hệt file mới (regen không khác) | Vieneu deterministic với cùng text/voice/emotion/temp | Đổi `emotion_tag` hoặc `temperature` để thay đổi giọng | R6 |
| 9 | Audio dài hơn SRT slot → mất từ cuối | Truncate tại `slot_end` | Truncate tại `next_start` HOẶC split tại dấu phẩy | R11 |
| 10 | Giọng quá bùng nổ / quá phẳng | Chọn emotion tag ngẫu nhiên | Generate 4-12 sample + đo f0_std/flux/HNR trước khi commit | R6 |

---

## 8. QA Checklist (Bắt Buộc Trước Khi Giao File)

```python
def qa_wav(filepath, expected_sec, sr=24000):
    import soundfile as sf, numpy as np
    data, file_sr = sf.read(filepath, always_2d=False)
    duration = len(data) / file_sr
    peak = float(np.max(np.abs(data)))
    rms = float(np.sqrt(np.mean(data.astype(np.float64)**2)))
    checks = {
        "sample_rate_ok":   file_sr == sr,
        "duration_ok":      abs(duration - expected_sec) < 0.1,
        "no_clipping":      peak < 0.99,
        "has_audio":        rms > 0.005,
        "peak_in_range":    0.5 < peak < 0.99,
    }
    for k, v in checks.items():
        print(f"  {'OK ' if v else 'FAIL'}  {k}")
    return all(checks.values())

# QA silence giữa các câu (alignment SRT)
def qa_srt_alignment(wav_path, srt_entries, sr=24000):
    import soundfile as sf, numpy as np
    data, _ = sf.read(wav_path)
    for i in range(len(srt_entries) - 1):
        gap_s = srt_entries[i][1] - 0.05
        gap_e = srt_entries[i+1][0] + 0.05
        seg = data[int(gap_s*sr):int(gap_e*sr)]
        if len(seg) == 0: continue
        rms = float(np.sqrt(np.mean(seg.astype(np.float64)**2)))
        status = "OK " if rms < 0.01 else "FAIL"
        print(f"  {status}  silence {gap_s:.2f}-{gap_e:.2f}s (rms={rms:.4f})")
```

**Thresholds chuẩn:**
- Sample rate: 24000 Hz (Vieneu output)
- Duration: ±0.1s so với target
- Peak: < 0.99 (không clip), > 0.5 (sau normalize)
- RMS tổng: > 0.005 (có audio thật)
- Silence giữa câu: rms < 0.01

---

## 9. Template Hoàn Chỉnh — Voiceover 21s

```python
import os
os.environ["PYTHONIOENCODING"] = "utf-8"   # R1

import re
import numpy as np
import soundfile as sf
from scipy import signal
from pathlib import Path
from vieneu import Vieneu

# === CONFIG ===
SRT_PATH = Path("subtitles-21s.srt")
OUT_WAV  = Path("outputs/voiceover_21s.wav")
SR       = 24000
MAX_DUR  = 21.0
VOICE    = "Bích Ngọc (nữ miền Bắc)"
EMOTION_TAG = "<|emotion_3|>"      # R2
TEMPERATURE = 0.95                # R6
SILENCE_P   = 0.08                # R4

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

# === STRIP DẤU CÂU (R4) ===
def strip_punct(t):
    return " ".join(t.replace(",", " ").replace(".", " ")
                     .replace("—", " ").replace(";", " ").replace(":", " ").split())

# === TTS ===
tts = Vieneu(emotion="natural")
voice_data = tts.get_preset_voice(dict(tts.list_preset_voices())[VOICE])

entries = parse_srt(SRT_PATH)
clips = []
for s, e, text in entries:
    audio = tts.infer(
        text=strip_punct(text),       # R4
        voice=voice_data,
        temperature=TEMPERATURE,
        top_k=50,
        silence_p=SILENCE_P,
        apply_watermark=False,
        emotion_tag=EMOTION_TAG,      # R2
    )
    clips.append((s, audio))

# === GHÉP (không time-stretch, R3 + R9) ===
master = np.zeros(int(MAX_DUR * SR), dtype=np.float32)
for i, (start, audio) in enumerate(clips):
    nxt = entries[i+1][0] if i+1 < len(entries) else MAX_DUR
    offset = int(start * SR)
    boundary = int(nxt * SR)          # R9: không buffer
    end = min(offset + len(audio), boundary, len(master))
    master[offset:end] = audio[:end-offset]

# === EQ + NORMALIZE + CROSSFADE ===
sos_hp = signal.butter(4, 80, btype="highpass", fs=SR, output="sos")
master = signal.sosfilt(sos_hp, master)
peak = np.max(np.abs(master))
master = master * (0.88 / peak) if peak > 0 else master
fade = int(0.04 * SR)
for i in range(1, len(clips)):
    b = int(clips[i][0] * SR)
    master[b-fade:b] *= np.linspace(1, 0, fade)
    master[b:b+fade] *= np.linspace(0, 1, fade)

# === EXPORT ===
sf.write(OUT_WAV, master, SR, subtype="PCM_16")
print(f"[OK] {OUT_WAV}  ({len(master)/SR:.2f}s)")
```

---

## 10. Workflow Khuyến Nghị

1. **Trước khi code:** đọc §1 (yêu cầu) + §6 (chọn emotion tag)
2. **Khi code:** dùng template §9 làm skeleton
3. **Sau khi generate:** chạy QA §8 — phải 15/15 pass
4. **Nếu người dùng phàn nàn "giọng dề/lag/khác":** kiểm tra lại R2, R3, R4
5. **Khi mux video:** dùng §4, nhớ R5 + R8 + R10
