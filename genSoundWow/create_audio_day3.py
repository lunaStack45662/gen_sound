"""
Gen voiceover day-3 từ subtitle.txt (định dạng SRT) + áp dụng R1-R11 + P1-P10.

Input:  input/day-3/subtitle.txt (SRT format, 8 cues, 17s)
Output: output/day-3/voiceover_17s.wav  +  subtitles-17s.srt (refined)

R1:  PYTHONIOENCODING=utf-8
R2:  emotion_tag="<|emotion_3|>"
R3:  KHÔNG time-stretch
R4:  strip dấu câu
R6:  temperature=0.95, silence_p=0.08
R9:  truncate tại next_start
R11: resolve_overflow — ưu tiên giảm gap

P1:  classify_transition
P2:  gap >= 300ms
P3:  sau "?" gap >= 800ms
P5:  strip dấu TRƯỚC TTS
P7:  truncate tại next_start
P8:  câu cuối gap "ending"
P9:  tts.infer() 1 lần / cue
P10: silence chèn VÀO GIỮA valley + fade 10ms
"""
import os
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

import re
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal
from vieneu import Vieneu

# === CONFIG ===
DAY = 3
SUBTITLE_TXT = Path(f"input/day-{DAY}/subtitle.txt")
OUT_DIR      = Path(f"output/day-{DAY}")
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_WAV      = OUT_DIR / f"voiceover_17s.wav"
OUT_SRT      = OUT_DIR / "subtitles-17s.srt"
OUT_DEBUG    = OUT_DIR / "_voiceover_debug.json"

VIDEO_DUR    = 17.0
SR           = 24000
VOICE_NAME   = "Bích Ngọc (nữ miền Bắc)"
EMOTION_INIT = "natural"
EMOTION_TAG  = "<|emotion_3|>"
TEMPERATURE  = 0.95
TOP_K        = 50
SILENCE_P    = 0.08

# EQ
HPF_CUTOFF         = 80.0
HIGH_SHELF_GAIN_DB = 4.0
HIGH_SHELF_FREQ    = 2500.0
PRESENCE_PEAK_DB   = 2.5
PRESENCE_FREQ      = 5000.0
PRESENCE_Q         = 0.7
TARGET_PEAK        = 0.88

# Pacing
GAP_PRESETS  = {"strong": 0.9, "light": 0.55, "list": 0.35, "ending": 1.2}
MIN_GAP      = 0.30
QUESTION_GAP = 0.80
MICRO_PAUSE  = {"comma": 280, "conjunction": 220, "adverbial": 200}

CONJUNCTIONS = {"nhưng", "mà", "và", "hoặc", "hay", "rồi", "nên", "vì",
                "bởi vì", "tuy", "dù", "thì", "là"}
ADVERBIAL_STARTERS = {
    "có khi nào", "có những", "trong đầu", "khi đó", "lúc ấy", "bây giờ",
    "thực ra", "thật ra", "có lẻ", "có thể", "rõ ràng",
    "cuối cùng", "đầu tiên", "tóm lại", "không phải", "và đó",
}
STRONG_MARKERS = {"nhưng", "tuy nhiên", "vấn đề là", "thực ra", "thật ra",
                  "không phải", "mà vì"}


# ---------- 1. Parse SRT ----------
def parse_srt(p: Path) -> list[tuple[float, float, str]]:
    """Trả về list[(start_sec, end_sec, text)]."""
    entries = []
    for block in re.split(r"\n\s*\n", p.read_text(encoding="utf-8").strip()):
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


# ---------- 2. Strip dấu câu (R4) ----------
def strip_punct(t: str) -> str:
    return " ".join(t.replace(",", " ")
                     .replace(".", " ")
                     .replace("—", " ")
                     .replace(";", " ")
                     .replace(":", " ")
                     .replace("?", " ")
                     .replace("!", " ")
                     .split())


# ---------- 3. Pacing: micro pause detection ----------
def find_pause_points(original_text: str) -> list[tuple[int, float]]:
    """Phân tích SRT gốc (còn dấu câu) -> list[(word_index, pause_sec)]."""
    words = original_text.split()
    pauses = []
    for i, w in enumerate(words):
        w_clean = w.strip(",.;:!?—\u2014").lower()
        if w.rstrip().endswith(",") or w.rstrip().endswith("—") or w.rstrip().endswith("\u2014"):
            pauses.append((i, MICRO_PAUSE["comma"] / 1000))
        elif w_clean in CONJUNCTIONS and i > 0:
            pauses.append((i - 1, MICRO_PAUSE["conjunction"] / 1000))
        elif i <= 2:
            prefix = " ".join(x.strip(",.;:!?—\u2014").lower()
                              for x in words[:i+1])
            for starter in ADVERBIAL_STARTERS:
                if prefix.startswith(starter) or prefix == starter:
                    pauses.append((i, MICRO_PAUSE["adverbial"] / 1000))
                    break
    return pauses


def find_natural_pause(audio, center, sr, search_ms=300, window_ms=30):
    search = int(search_ms * sr / 1000)
    win = int(window_ms * sr / 1000)
    step = max(1, win // 4)
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
    threshold = max(energies) * 0.15
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


def insert_pauses_into_audio(audio, original_text, sr=SR):
    pauses = find_pause_points(original_text)
    if not pauses:
        return audio
    n_words = max(len(original_text.split()), 1)
    fade_len = int(0.01 * sr)
    result = audio.copy()
    for word_idx, pause_sec in reversed(pauses):
        est = int((word_idx + 1) / n_words * len(result))
        vs, ve = find_natural_pause(result, est, sr)
        mid = (vs + ve) // 2
        fo_s = max(0, mid - fade_len)
        result[fo_s:fo_s + fade_len] *= np.sqrt(np.linspace(1, 0, fade_len))
        fi_e = min(mid + fade_len, len(result))
        if fi_e > mid:
            result[mid:fi_e] *= np.sqrt(np.linspace(0, 1, fade_len))[:fi_e - mid]
        result = np.concatenate([
            result[:mid],
            np.zeros(int(pause_sec * sr), dtype=np.float32),
            result[mid:],
        ])
    return result


def tts_sentence(original_text, tts, voice_data, **kwargs) -> np.ndarray:
    clean = strip_punct(original_text)
    audio = tts.infer(text=clean, voice=voice_data, **kwargs)
    return insert_pauses_into_audio(audio, original_text)


# ---------- 4. Transition classification (P1) ----------
def classify_transition(prev_text: str, curr_text: str) -> str:
    if prev_text.strip().endswith("?"):
        return "strong"
    if any(curr_text.lower().strip().startswith(m) for m in STRONG_MARKERS):
        return "strong"
    prev_w = set(prev_text.lower().split())
    curr_w = set(curr_text.lower().split())
    if len(prev_w & curr_w) >= 2 and len(prev_text.split()) <= 6:
        return "list"
    return "light"


# ---------- 5. EQ sharpen ----------
def sharpen_audio(audio: np.ndarray) -> np.ndarray:
    x = audio.astype(np.float32).copy()
    sos_hp = signal.butter(4, HPF_CUTOFF, btype="highpass", fs=SR, output="sos")
    x = signal.sosfilt(sos_hp, x)
    A = 10 ** (HIGH_SHELF_GAIN_DB / 40.0)
    w0 = 2 * np.pi * HIGH_SHELF_FREQ / SR
    cos_w0, sin_w0 = np.cos(w0), np.sin(w0)
    S = 1.0
    alpha = sin_w0 / 2 * np.sqrt((A + 1/A) * (1/S - 1) + 2)
    b0 = A * ((A+1) + (A-1)*cos_w0 + 2*np.sqrt(A)*alpha)
    b1 = -2*A*((A-1) + (A+1)*cos_w0)
    b2 = A * ((A+1) + (A-1)*cos_w0 - 2*np.sqrt(A)*alpha)
    a0 = (A+1) - (A-1)*cos_w0 + 2*np.sqrt(A)*alpha
    a1 = 2*((A-1) - (A+1)*cos_w0)
    a2 = (A+1) - (A-1)*cos_w0 - 2*np.sqrt(A)*alpha
    b = np.array([b0, b1, b2]) / a0
    a = np.array([1.0, a1/a0, a2/a0])
    x = signal.lfilter(b, a, x)

    w0 = 2 * np.pi * PRESENCE_FREQ / SR
    cos_w0, sin_w0 = np.cos(w0), np.sin(w0)
    A_p = 10 ** (PRESENCE_PEAK_DB / 20.0)
    alpha = sin_w0 / (2 * PRESENCE_Q)
    b0 = 1 + alpha*A_p
    b1 = -2*cos_w0
    b2 = 1 - alpha*A_p
    a0 = 1 + alpha/A_p
    a1 = -2*cos_w0
    a2 = 1 - alpha/A_p
    b = np.array([b0, b1, b2]) / a0
    a = np.array([1.0, a1/a0, a2/a0])
    x = signal.lfilter(b, a, x)
    return x.astype(np.float32)


# ---------- 6. SRT writer ----------
def fmt_srt_time(t: float) -> str:
    if t < 0: t = 0.0
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    ms = int(round((t - int(t)) * 1000))
    if ms == 1000:
        s += 1; ms = 0
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(entries: list[tuple[float, float, str]], path: Path):
    with open(path, "w", encoding="utf-8") as f:
        for i, (s, e, text) in enumerate(entries, 1):
            f.write(f"{i}\n{fmt_srt_time(s)} --> {fmt_srt_time(e)}\n{text}\n\n")


# ---------- 7. MAIN ----------
def main():
    print(f"[1/6] Đọc SRT: {SUBTITLE_TXT}")
    entries = parse_srt(SUBTITLE_TXT)
    assert entries, "SRT rỗng / sai format"
    print(f"   ✓ {len(entries)} cues:")
    for i, (s, e, t) in enumerate(entries, 1):
        print(f"     #{i:2d}  {s:5.2f}s -> {e:5.2f}s  (slot {e-s:.2f}s)  |  {t}")

    print(f"\n[2/6] Khởi tạo Vieneu (voice='{VOICE_NAME}', emotion_tag='{EMOTION_TAG}')")
    tts = Vieneu(emotion=EMOTION_INIT)
    voice_data = tts.get_preset_voice(dict(tts.list_preset_voices())[VOICE_NAME])

    # ---- PASS 1: TTS + đo raw duration ----
    print(f"\n[3/6] PASS 1: TTS từng cue, đo raw duration")
    infer_kwargs = dict(
        temperature=TEMPERATURE, top_k=TOP_K, silence_p=SILENCE_P,
        apply_watermark=False, emotion_tag=EMOTION_TAG,
    )
    raw_durs: list[float] = []
    audios: list[np.ndarray] = []
    for i, (s, e, text) in enumerate(entries, 1):
        slot = e - s
        print(f"   ▶ Cue {i}/{len(entries)} (slot {slot:.2f}s): \"{text[:60]}{'...' if len(text)>60 else ''}\"")
        audio = tts_sentence(text, tts, voice_data, **infer_kwargs)
        dur = len(audio) / SR
        raw_durs.append(dur)
        audios.append(audio)
        print(f"     raw={dur:.2f}s  slot={slot:.2f}s  overflow={dur-slot:+.2f}s")

    # ---- PASS 2: Respect SRT timing (user-designed slots) ----
    # User yêu cầu: giữ SRT nguyên, truncate tại next_start (R9)
    # Audio dài hơn slot → cắt phần tràn; slot thừa → yên (do master = zeros)
    print(f"\n[4/6] PASS 2: Dùng SRT timing gốc (gap = start[i+1] - end[i])")
    srt_entries = []
    for i, (s, e, text) in enumerate(entries):
        srt_entries.append((s, e, text))
        gap = (entries[i+1][0] - e) if i+1 < len(entries) else (VIDEO_DUR - e)
        print(f"   • #{i+1:2d}  slot={s:5.2f}s->{e:5.2f}s  (gap {gap:.2f}s)  raw={raw_durs[i]:.2f}s  | {text[:55]}{'...' if len(text)>55 else ''}")
    print(f"   ⚠️ Cue overflow sẽ bị truncate tại next_start (R9). Cue nằm ngoài {VIDEO_DUR}s bị bỏ.")

    write_srt(srt_entries, OUT_SRT)
    print(f"   ✓ SRT -> {OUT_SRT}")

    # ---- PASS 3: Ghép master buffer ----
    print(f"\n[5/6] PASS 3: Ghép master (R3, R9)")
    total_samples = int(VIDEO_DUR * SR)
    master = np.zeros(total_samples, dtype=np.float32)
    for i, ((s, e, text), audio) in enumerate(zip(srt_entries, audios)):
        offset = int(s * SR)
        next_start = srt_entries[i+1][0] if i+1 < len(srt_entries) else VIDEO_DUR
        boundary = int(next_start * SR)
        end_sample = min(offset + len(audio), boundary, total_samples)
        truncated = len(audio) - (end_sample - offset)
        if truncated > 0:
            print(f"   • #{i+1:2d}  truncated {truncated} samples ({truncated/SR*1000:.0f}ms)")
        master[offset:end_sample] = audio[:end_sample - offset]

    # EQ + normalize
    print(f"\n[6/6] EQ + normalize + crossfade + export")
    master = sharpen_audio(master)
    peak = float(np.max(np.abs(master)))
    if peak > 0:
        master = master * (TARGET_PEAK / peak)
    print(f"   ✓ Normalize: peak {peak:.3f} -> {TARGET_PEAK:.3f}")

    fade = int(0.04 * SR)
    for i in range(1, len(srt_entries)):
        b = int(srt_entries[i][0] * SR)
        if b < fade or b + fade > total_samples:
            continue
        t = np.linspace(0, np.pi/2, fade)
        master[b-fade:b] *= np.cos(t)
        master[b:b+fade] *= np.sin(t)

    sf.write(OUT_WAV, master, SR, subtype="PCM_16")
    print(f"   ✓ WAV -> {OUT_WAV}  ({len(master)/SR:.2f}s, {SR}Hz)")

    dbg = {
        "day": DAY,
        "video_dur": VIDEO_DUR,
        "n_clips": len(entries),
        "clips": [
            {"i": i+1, "text": text,
             "raw_dur": round(raw_durs[i], 3),
             "start": round(s, 3), "end": round(e, 3)}
            for i, (s, e, text) in enumerate(srt_entries)
        ],
    }
    OUT_DEBUG.write_text(json.dumps(dbg, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"   ✓ Debug -> {OUT_DEBUG}")


if __name__ == "__main__":
    main()
