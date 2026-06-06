"""
Test file voiceover_21s.wav vừa generate:
  1. File tồn tại, đúng format
  2. Duration ~ 21s (±0.1s)
  3. Sample rate = 24000 Hz
  4. Mono, không stereo
  5. Không clipping (peak < 1.0, |max| <= 0.95 sau normalize)
  6. Có audio thực sự (RMS > 0.001) - không phải silence toàn bộ
  7. SRT alignment: vùng silence trước câu #2 (~3.0-3.2s) phải yên
  8. Export 1 đoạn mẫu 5s đầu để nghe thử
"""

import sys
import wave
from pathlib import Path

import numpy as np
import soundfile as sf

WAV_PATH = Path("outputs/voiceover_21s.wav")
SAMPLE_OUT = Path("outputs/sample_5s_preview.wav")
SRT_PATH = Path("subtitles-21s.srt")

failures = []
passes = []


def check(name: str, ok: bool, detail: str = ""):
    (passes if ok else failures).append((name, detail))
    icon = "✅" if ok else "❌"
    print(f"  {icon}  {name}" + (f"  — {detail}" if detail else ""))


# ---------- 1. File tồn tại ----------
print("\n=== 1. File tồn tại ===")
exists = WAV_PATH.exists()
check("file exists", exists, str(WAV_PATH))
if not exists:
    sys.exit(1)

# ---------- 2. Đọc metadata ----------
print("\n=== 2. Format & Metadata ===")
data, sr = sf.read(WAV_PATH, always_2d=False)
check("sample rate = 24000Hz", sr == 24000, f"got {sr}Hz")
duration = len(data) / sr
check("duration ≈ 21s", abs(duration - 21.0) < 0.1, f"{duration:.3f}s")
check("mono (1D array)", data.ndim == 1, f"ndim={data.ndim}")
check("dtype float in [-1,1]", data.dtype.kind == "f", f"dtype={data.dtype}")
check("size > 0", len(data) > 0, f"{len(data)} samples")

# ---------- 3. Audio chất lượng ----------
print("\n=== 3. Audio chất lượng ===")
peak = float(np.max(np.abs(data)))
rms = float(np.sqrt(np.mean(data.astype(np.float64) ** 2)))
check("no clipping (peak < 0.99)", peak < 0.99, f"peak={peak:.4f}")
check("has audible content (RMS > 0.005)", rms > 0.005, f"rms={rms:.4f}")
check("peak in expected range [0.5, 0.99]", 0.5 < peak < 0.99, f"peak={peak:.4f}")

# ---------- 4. SRT alignment ----------
print("\n=== 4. SRT alignment (silence giữa các câu) ===")
# Vùng giữa câu 1 (kết thúc ~3.0s) và câu 2 (bắt đầu ~3.2s) -> 3.0-3.2s nên yên
# Tương tự các gap khác: 7.0-7.2s, 10.0-10.2s, 12.5-12.7s, 17.0-17.2s
gaps = [(2.95, 3.20), (6.95, 7.20), (10.00, 10.20), (12.45, 12.70), (16.95, 17.20)]
for s, e in gaps:
    a, b = int(s * sr), int(e * sr)
    seg = data[a:b]
    if len(seg) == 0:
        check(f"silence {s}-{e}s", False, "empty segment")
        continue
    seg_rms = float(np.sqrt(np.mean(seg.astype(np.float64) ** 2)))
    # Nên yên (RMS < 0.01) - cho phép nhỏ vì head-pad
    check(f"silence {s:.2f}-{e:.2f}s (rms<0.01)", seg_rms < 0.01, f"rms={seg_rms:.4f}")

# Vùng có lời (giữa câu 1) phải có audio
speech_window = (0.5, 2.5)
a, b = int(speech_window[0] * sr), int(speech_window[1] * sr)
speech_seg = data[a:b]
speech_rms = float(np.sqrt(np.mean(speech_seg.astype(np.float64) ** 2)))
check(f"speech 0.5-2.5s has audio (rms>0.01)", speech_rms > 0.01, f"rms={speech_rms:.4f}")

# ---------- 5. Tổng kết ----------
print("\n" + "=" * 50)
print(f"  PASS: {len(passes)}/{len(passes) + len(failures)}")
if failures:
    print(f"  FAIL: {len(failures)}")
    for n, d in failures:
        print(f"    - {n}: {d}")
    sys.exit(1)
print("  🎉 Tất cả test PASSED!")

# ---------- 6. Xuất đoạn mẫu 5s đầu ----------
print(f"\n=== 6. Trích đoạn mẫu 5s đầu -> {SAMPLE_OUT} ===")
preview = data[: 5 * sr]
sf.write(SAMPLE_OUT, preview, sr, subtype="PCM_16")
print(f"  ✓ {SAMPLE_OUT}  (5.00s, {sr}Hz)")
