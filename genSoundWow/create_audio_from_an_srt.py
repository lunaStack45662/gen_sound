"""
Gen audio từ file SRT - phiên bản GIỌNG SẮC (sharp/crisp):
  - Voice: Bích Ngọc (nữ miền Bắc) — articulation sắc nét, phù hợp voiceover video ngắn
  - Emotion: storytelling
  - KHÔNG time-stretch (tránh artifacts phase-vocoder gây ồm)
  - EQ post-processing: high-shelf +5dB @ 2.5kHz + presence boost @ 5kHz
  - Light de-essing (high-pass nhẹ từ 80Hz để bỏ rumble)
  - Output: 1 file WAV 21s, sample rate 24kHz, mono
"""

import re
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal
from vieneu import Vieneu

# ---------- Config ----------
SRT_PATH = Path("subtitles-21s.srt")
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)
OUTPUT_WAV = OUTPUT_DIR / "voiceover_21s.wav"

VOICE_NAME = "Bích Ngọc (nữ miền Bắc)"   # giọng nữ Bắc, sắc, articulation rõ
EMOTION = "natural"                  # init mode (chỉ map "natural" -> emotion_0); emotion thật truyền qua emotion_tag
EMOTION_TAG = "<|emotion_3|>"        # biểu cảm cân bằng, dao động pitch ~42Hz, mượt, HNR 4.46dB
SR = 24000
MAX_DURATION = 20.5
SILENCE_PAD_MS = 80                  # chừa chút hơi giữa các câu cho tự nhiên
MAX_SPEED_RATIO = 1.15               # chỉ nén khi bắt buộc (tránh méo)
TEMPERATURE = 0.95
TOP_K = 50
SILENCE_P = 0.08                     # pause probability -> it nhat de audio lien mach (TNS chen pause 0.4s giua cau co dau phay se tao cam giac 'lag')

# EQ (đơn vị: dB)
HIGH_SHELF_GAIN_DB = 4.0             # +4dB trên 2.5kHz -> giọng sáng, bén
HIGH_SHELF_FREQ = 2500.0
PRESENCE_PEAK_DB = 2.5               # +2.5dB quanh 5kHz -> articulation crisp
PRESENCE_FREQ = 5000.0
PRESENCE_Q = 0.7
HPF_CUTOFF = 80.0                    # cắt dưới 80Hz -> bỏ rumble
TARGET_PEAK = 0.88                   # chuẩn hoá đỉnh


# ---------- 1. Parse SRT ----------
def parse_srt(path: Path):
    """Trả về list[(start_sec, end_sec, text)]"""
    content = path.read_text(encoding="utf-8")
    blocks = re.split(r"\n\s*\n", content.strip())
    entries = []
    for block in blocks:
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if len(lines) < 2:
            continue
        m = re.match(
            r"(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})",
            lines[1],
        )
        if not m:
            continue
        sh, sm, ss, sms, eh, em, es, ems = map(int, m.groups())
        start = sh * 3600 + sm * 60 + ss + sms / 1000
        end = eh * 3600 + em * 60 + es + ems / 1000
        text = " ".join(lines[2:])
        entries.append((start, end, text))
    return entries


# ---------- 2. Time-stretch (TẮT — tránh phase-vocoder làm đổi giọng) ----------
def fit_to_slot(audio: np.ndarray, slot_sec: float,
                max_speed_ratio: float = MAX_SPEED_RATIO) -> np.ndarray:
    """Không time-stretch: trả về audio gốc để giữ đúng timbre.
    Phần placement sẽ xử lý overflow (câu dài tràn vào gap câu sau).
    """
    return audio


# ---------- 3. EQ giúp giọng SẮC ----------
def sharpen_audio(audio: np.ndarray) -> np.ndarray:
    """
    High-pass bỏ rumble + high-shelf sáng + presence peak làm articulation bén.
    """
    x = audio.astype(np.float32).copy()

    # (a) High-pass 80Hz bỏ rumble
    sos_hp = signal.butter(4, HPF_CUTOFF, btype="highpass", fs=SR, output="sos")
    x = signal.sosfilt(sos_hp, x)

    # (b) High-shelf: +HIGH_SHELF_GAIN_DB từ HIGH_SHELF_FREQ trở lên
    A = 10 ** (HIGH_SHELF_GAIN_DB / 40.0)   # biên độ sqrt
    w0 = 2 * np.pi * HIGH_SHELF_FREQ / SR
    cos_w0 = np.cos(w0)
    sin_w0 = np.sin(w0)
    S = 1.0
    alpha = sin_w0 / 2 * np.sqrt((A + 1 / A) * (1 / S - 1) + 2)
    # High-shelf coefficients (Audio EQ Cookbook)
    b0 = A * ((A + 1) + (A - 1) * cos_w0 + 2 * np.sqrt(A) * alpha)
    b1 = -2 * A * ((A - 1) + (A + 1) * cos_w0)
    b2 = A * ((A + 1) + (A - 1) * cos_w0 - 2 * np.sqrt(A) * alpha)
    a0 = (A + 1) - (A - 1) * cos_w0 + 2 * np.sqrt(A) * alpha
    a1 = 2 * ((A - 1) - (A + 1) * cos_w0)
    a2 = (A + 1) - (A - 1) * cos_w0 - 2 * np.sqrt(A) * alpha
    b = np.array([b0, b1, b2]) / a0
    a = np.array([1.0, a1 / a0, a2 / a0])
    x = signal.lfilter(b, a, x)

    # (c) Peaking EQ quanh 5kHz -> "presence" giúp articulation bén
    w0 = 2 * np.pi * PRESENCE_FREQ / SR
    cos_w0 = np.cos(w0)
    sin_w0 = np.sin(w0)
    A_p = 10 ** (PRESENCE_PEAK_DB / 20.0)
    alpha = sin_w0 / (2 * PRESENCE_Q)
    b0 = 1 + alpha * A_p
    b1 = -2 * cos_w0
    b2 = 1 - alpha * A_p
    a0 = 1 + alpha / A_p
    a1 = -2 * cos_w0
    a2 = 1 - alpha / A_p
    b = np.array([b0, b1, b2]) / a0
    a = np.array([1.0, a1 / a0, a2 / a0])
    x = signal.lfilter(b, a, x)

    return x.astype(np.float32)


# ---------- 4. Main ----------
def main():
    print(f"[1/4] Đọc SRT: {SRT_PATH}")
    entries = parse_srt(SRT_PATH)
    for i, (s, e, t) in enumerate(entries, 1):
        print(f"   #{i}: {s:5.2f}s -> {e:5.2f}s  |  {t}")
    assert entries, "SRT rỗng / sai định dạng"

    print(f"\n[2/4] Khởi tạo vieneu TTS (init emotion='{EMOTION}', emotion_tag='{EMOTION_TAG}', voice='{VOICE_NAME}')")
    tts = Vieneu(emotion=EMOTION)

    voices = dict(tts.list_preset_voices())
    voice_id = voices.get(VOICE_NAME)
    if voice_id is None:
        raise RuntimeError(f"Không tìm thấy voice '{VOICE_NAME}'. Có: {list(voices)}")
    voice_data = tts.get_preset_voice(voice_id)
    print(f"   ✓ Voice loaded: {VOICE_NAME}")

    clips = []
    for idx, (start, end, text) in enumerate(entries, 1):
        slot = end - start
        print(f"\n   ▶ Câu {idx}/{len(entries)}: \"{text}\"")
        print(f"     slot={slot:.2f}s")

        # Bo dau phay/period trong text (SRT giu nguyen) de TTS khong chen pause 0.4s
        tts_text = text.replace(",", " ").replace(".", " ").replace("—", " ")
        tts_text = " ".join(tts_text.split())  # collapse multiple spaces
        print(f"     tts_text=\"{tts_text}\"")

        audio = tts.infer(
            text=tts_text,
            voice=voice_data,
            temperature=TEMPERATURE,
            top_k=TOP_K,
            silence_p=SILENCE_P,
            apply_watermark=False,
            emotion_tag=EMOTION_TAG,
        )
        raw_dur = len(audio) / SR
        print(f"     raw duration: {raw_dur:.2f}s")

        fitted = fit_to_slot(audio, slot)
        if abs(len(fitted) / SR - raw_dur) > 0.01:
            print(f"     stretched -> {len(fitted)/SR:.2f}s")
        else:
            print(f"     (no stretch needed)")

        clips.append((start, fitted))

    # ---------- 5. Ghép theo timing ----------
    print(f"\n[3/4] Ghép audio theo timing SRT, tổng duration = {MAX_DURATION}s")
    total_samples = int(MAX_DURATION * SR)
    master = np.zeros(total_samples, dtype=np.float32)
    pad_samples = int(SILENCE_PAD_MS * SR / 1000)

    for i, (start, audio) in enumerate(clips):
        # tìm end của slot hiện tại + start của slot kế
        end = entries[i][1]
        next_start = entries[i + 1][0] if i + 1 < len(entries) else 21.0

        start_sample = int(start * SR)
        offset = start_sample
        if start > 0.05 and (start_sample - pad_samples) >= int(next_start * SR) - SR // 2:
            offset = max(0, start_sample - pad_samples)
        # Cap tại next_start (không buffer) để câu trước nối liền câu sau, không khoảng lặng
        boundary_sample = int(next_start * SR)
        max_end = min(offset + len(audio), boundary_sample, total_samples)
        audio = audio[: max_end - offset]
        master[offset:offset + len(audio)] = audio
        overflow = len(audio) / SR - (end - start)
        tag = " [OVERFLOW]" if overflow > 0.01 else ""
        print(f"   • place @ {offset/SR:5.2f}s -> {(offset+len(audio))/SR:5.2f}s "
              f"(len={len(audio)/SR:.2f}s, slot={end-start:.2f}s, "
              f"overflow={overflow:+.2f}s){tag}")

    # ---------- 6. EQ sharpen toàn bộ ----------
    print(f"\n[4/5] EQ sharpen (HPF {HPF_CUTOFF}Hz + high-shelf "
          f"+{HIGH_SHELF_GAIN_DB}dB @{HIGH_SHELF_FREQ}Hz + presence "
          f"+{PRESENCE_PEAK_DB}dB @{PRESENCE_FREQ}Hz)")
    master = sharpen_audio(master)

    # ---------- 7. Normalize đỉnh + crossfade ----------
    peak = float(np.max(np.abs(master)))
    if peak > 0:
        master = master * (TARGET_PEAK / peak)
        print(f"   ✓ Normalize: peak {peak:.3f} -> {TARGET_PEAK:.3f}")

    fade_samples = int(0.04 * SR)
    for i in range(1, len(clips)):
        boundary = int(clips[i][0] * SR)
        if boundary < fade_samples or boundary + fade_samples > total_samples:
            continue
        t = np.linspace(0, np.pi / 2, fade_samples)
        fade_out = np.cos(t)
        fade_in = np.sin(t)
        master[boundary - fade_samples: boundary] *= fade_out
        master[boundary: boundary + fade_samples] *= fade_in

    # ---------- 8. Ghi file ----------
    print(f"\n[5/5] Xuất WAV -> {OUTPUT_WAV}")
    sf.write(OUTPUT_WAV, master, SR, subtype="PCM_16")
    duration = len(master) / SR
    print(f"   ✓ {OUTPUT_WAV}  ({duration:.2f}s, {SR}Hz, mono)")
    print(f"   ✓ Kích thước: {OUTPUT_WAV.stat().st_size/1024:.1f} KB")


if __name__ == "__main__":
    main()
