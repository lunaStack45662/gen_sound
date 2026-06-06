"""
Mix voiceover + background music (BGM) → video.
Kỹ thuật: EQ carving + sidechain ducking + volume balance.
Đảm bảo giọng đọc nổi bật, nhạc nền hỗ trợ không đánh nhau.

Cách dùng:
    python adding_audio_to_video/mix_audio.py --bgm duong/dan/nhac_nen.mp3

Hoặc dùng như module:
    from mix_audio import mix_and_mux
    mix_and_mux("input/video/clip.mp4", "output/wav/voiceover.wav", "bgm.mp3", "output/video/final.mp4")
"""

import argparse
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal as sig
import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

# ──────────────────── Constants ────────────────────
SR = 24000          # voiceover sample rate
BGM_TARGET_DB = -18 # BGM volume relative to voiceover (dB)
EQ_LOW = 300        # EQ carve low frequency (Hz)
EQ_HIGH = 3000      # EQ carve high frequency (Hz)
EQ_REDUCE_DB = -4   # how much to cut mids on BGM (dB)
DUCK_THRESHOLD = 0.015  # voice RMS above this → duck BGM
DUCK_DEPTH_DB = -6  # extra duck when voice present (dB)
ATTACK_MS = 150     # duck attack time (ms)
RELEASE_MS = 800    # duck release time (ms)
FADE_OUT_SEC = 3.0  # BGM fade out at end (seconds)


# ═══════════════════════════════════════════════════
# 1. ANALYZE — Kiểm tra thông số file audio
# ═══════════════════════════════════════════════════

def analyze_audio(path):
    """Đọc và phân tích file audio. Trả về dict thông số."""
    info = sf.info(str(path))
    audio, sr = sf.read(str(path), dtype="float64")

    # Convert stereo → mono để phân tích
    if audio.ndim == 2:
        mono = audio.mean(axis=1)
    else:
        mono = audio

    peak = np.max(np.abs(mono))
    rms = np.sqrt(np.mean(mono ** 2))
    duration = len(mono) / sr

    # Tần số chiếm ưu thế (FFT đơn giản)
    fft = np.abs(np.fft.rfft(mono[:sr * 3]))  # 3 giây đầu
    freqs = np.fft.rfftfreq(min(sr * 3, len(mono)), 1 / sr)
    top_freq_idx = np.argsort(fft)[-5:]  # 5 đỉnh tần số
    top_freqs = sorted(freqs[top_freq_idx])

    result = {
        "path": str(path),
        "duration": duration,
        "sample_rate": sr,
        "channels": info.channels,
        "peak": peak,
        "peak_db": 20 * np.log10(peak) if peak > 0 else -np.inf,
        "rms": rms,
        "rms_db": 20 * np.log10(rms) if rms > 0 else -np.inf,
        "top_frequencies": [f"{f:.0f}Hz" for f in top_freqs],
        "is_suitable": True,
        "warnings": [],
    }

    # Kiểm tra có hợp làm BGM không
    if duration < 10:
        result["warnings"].append("⚠️ Nhạc quá ngắn (<10s), sẽ phải loop")
    if peak < 0.01:
        result["warnings"].append("⚠️ Nhạc quá nhỏ, gần như silence")
        result["is_suitable"] = False
    if rms > 0.3:
        result["warnings"].append("⚠️ Nhạc quá to/dynamic, cần nén thêm")

    # Kiểm tra tần số có tranh với giọng đọc không
    mid_energy = np.sum(fft[(freqs >= EQ_LOW) & (freqs <= EQ_HIGH)])
    total_energy = np.sum(fft)
    mid_ratio = mid_energy / total_energy if total_energy > 0 else 0
    if mid_ratio > 0.5:
        result["warnings"].append(f"⚠️ Nhạc nhiều mid ({mid_ratio:.0%}) → cần EQ carve mạnh")

    return result


def print_analysis(info, label="Audio"):
    """In thông số audio ra console."""
    print(f"\n{'='*50}")
    print(f"  {label}: {Path(info['path']).name}")
    print(f"{'='*50}")
    print(f"  Duration:    {info['duration']:.2f}s")
    print(f"  Sample rate: {info['sample_rate']}Hz")
    print(f"  Channels:    {info['channels']}")
    print(f"  Peak:        {info['peak']:.4f} ({info['peak_db']:.1f} dB)")
    print(f"  RMS:         {info['rms']:.4f} ({info['rms_db']:.1f} dB)")
    print(f"  Top freqs:   {', '.join(info['top_frequencies'])}")
    for w in info["warnings"]:
        print(f"  {w}")
    print()


# ═══════════════════════════════════════════════════
# 2. PROCESS BGM — EQ carve + volume balance
# ═══════════════════════════════════════════════════

def _ensure_mono(audio):
    """Sterereo → mono."""
    if audio.ndim == 2:
        return audio.mean(axis=1)
    return audio


def _resample(audio, sr_from, sr_to):
    """Resample audio nếu sample rate khác voiceover."""
    if sr_from == sr_to:
        return audio
    ratio = sr_to / sr_from
    n_samples = int(len(audio) * ratio)
    return sig.resample(audio, n_samples)


def _trim_or_loop(audio, target_samples):
    """Cắt ngắn hoặc loop nhạc nền cho khớp duration voiceover."""
    n = len(audio)
    if n >= target_samples:
        return audio[:target_samples]
    # Loop
    repeats = (target_samples // n) + 1
    looped = np.tile(audio, repeats)
    return looped[:target_samples]


def _eq_carve_mid(audio, sr, low=EQ_LOW, high=EQ_HIGH, reduce_db=EQ_REDUCE_DB):
    """
    EQ khoét vùng mid (300Hz-3kHz) trên nhạc nền.
    Giọng đọc con người nằm ở vùng này → nhường chỗ.
    Dùng band-stop filter (notch rộng).
    """
    nyq = sr / 2
    # Band-stop filter: cắt từ low đến high
    low_n = low / nyq
    high_n = high / nyq

    # Đảm bảo tần số hợp lệ
    low_n = max(0.001, min(low_n, 0.999))
    high_n = max(0.001, min(high_n, 0.999))

    if low_n >= high_n:
        return audio

    # Thiết kế bandstop Butterworth filter bậc 4
    b, a = sig.butter(4, [low_n, high_n], btype="bandstop")
    filtered = sig.filtfilt(b, a, audio)

    # Blend: mix giữa filtered (vùng mid bị cắt) và gốc
    # Giảm reduce_db ở vùng mid
    gain = 10 ** (reduce_db / 20)  # -4dB → 0.63
    result = audio + (filtered - audio) * (1 - gain)
    return result


def _adjust_volume(audio, voiceover_peak, target_db=BGM_TARGET_DB):
    """
    Chỉnh volume BGM sao cho nhỏ hơn voiceover target_db.
    Ví dụ: voiceover peak = 0.88, target = -18dB → BGM peak ≈ 0.11
    """
    current_peak = np.max(np.abs(audio))
    if current_peak == 0:
        return audio
    target_peak = voiceover_peak * (10 ** (target_db / 20))
    scale = target_peak / current_peak
    return audio * scale


def process_bgm(bgm_path, voiceover_audio, sr=SR):
    """
    Xử lý nhạc nền: đọc → mono → resample → trim/loop → EQ carve → chỉnh volume.
    Trả về BGM đã xử lý, sẵn sàng để duck + mix.
    """
    bgm, bgm_sr = sf.read(str(bgm_path), dtype="float64")
    bgm = _ensure_mono(bgm)
    bgm = _resample(bgm, bgm_sr, sr)
    bgm = _trim_or_loop(bgm, len(voiceover_audio))
    bgm = _eq_carve_mid(bgm, sr)

    voiceover_peak = np.max(np.abs(voiceover_audio))
    bgm = _adjust_volume(bgm, voiceover_peak)

    print(f"  ✓ BGM processed: {len(bgm)/sr:.2f}s, EQ carve {EQ_LOW}-{EQ_HIGH}Hz, volume {BGM_TARGET_DB}dB")
    return bgm


# ═══════════════════════════════════════════════════
# 3. SIDECHAIN DUCKING — Nhạc tự "né" giọng đọc
# ═══════════════════════════════════════════════════

def _compute_envelope(audio, sr, window_ms=50):
    """Tính RMS envelope của audio (dùng window trượt)."""
    window = int(sr * window_ms / 1000)
    if window < 1:
        window = 1
    # Pad để giữ nguyên kích thước
    padded = np.pad(audio, (window // 2, window // 2), mode="reflect")
    # Rolling RMS
    cumsum = np.cumsum(padded ** 2)
    cumsum = np.insert(cumsum, 0, 0)
    rms_sq = (cumsum[window:] - cumsum[:-window]) / window
    return np.sqrt(np.maximum(rms_sq, 0))[:len(audio)]


def _smooth_gain(gain_curve, sr, attack_ms=ATTACK_MS, release_ms=RELEASE_MS):
    """
    Làm mượt gain curve: attack nhanh, release chậm.
    Tránh thay đổi volume đột ngột → nghe "pump".
    """
    attack_samples = int(sr * attack_ms / 1000)
    release_samples = int(sr * release_ms / 1000)

    smoothed = np.copy(gain_curve)
    # Forward pass (attack)
    for i in range(1, len(smoothed)):
        if smoothed[i] < smoothed[i - 1]:
            # Đang giảm → attack nhanh
            alpha = 1 - np.exp(-1 / max(attack_samples, 1))
            smoothed[i] = smoothed[i - 1] + alpha * (smoothed[i] - smoothed[i - 1])
    # Backward pass (release)
    for i in range(len(smoothed) - 2, -1, -1):
        if smoothed[i] < smoothed[i + 1]:
            # Đang tăng → release chậm
            alpha = 1 - np.exp(-1 / max(release_samples, 1))
            smoothed[i] = smoothed[i + 1] + alpha * (smoothed[i] - smoothed[i + 1])

    return smoothed


def sidechain_duck(bgm, voiceover_audio, sr=SR):
    """
    Sidechain ducking TỈ LỆ:
    - Giọng đọc to → nhạc giảm nhiều (nhưng KHÔNG tắt hẳn)
    - Giọng đọc nhỏ → nhạc giảm ít
    - Im lặng → nhạc nổi lên đầy đủ
    → Nghe mượt, không bị "lag" như on/off.
    """
    envelope = _compute_envelope(voiceover_audio, sr)

    # Duck tỉ lệ theo cường độ giọng đọc
    # envelope to → duck sâu, envelope nhỏ → duck nhẹ
    # KHÔNG bao giờ tắt hẳn (gain_min = 0.3 = khoảng -10dB)
    gain_min = 10 ** (DUCK_DEPTH_DB / 20)  # -6dB → 0.5 (sàn, không tắt)

    # Normalize envelope về 0-1 (so với peak giọng đọc)
    vo_peak = np.max(envelope)
    if vo_peak > 0:
        norm_env = np.clip(envelope / vo_peak, 0, 1)
    else:
        norm_env = np.zeros_like(envelope)

    # Gain curve: 1.0 khi im → giảm TỈ LỆ theo giọng → không dưới gain_min
    # Dùng sqrt để duck nhẹ hơn ở giọng nhỏ, sâu hơn ở giọng to
    duck_amount = np.sqrt(norm_env)  # 0→0, 0.5→0.7, 1.0→1.0
    gain_curve = 1.0 - duck_amount * (1.0 - gain_min)

    # Smooth: attack 200ms (giảm từ từ), release 1000ms (hồi từ từ)
    gain_curve = _smooth_gain(gain_curve, sr, attack_ms=200, release_ms=1000)

    # Áp dụng gain vào BGM
    ducked = bgm * gain_curve

    avg_gain = np.mean(gain_curve)
    min_gain = np.min(gain_curve)
    n_total = len(voiceover_audio) / sr
    print(f"  ✓ Sidechain duck TỈ LỆ: avg gain={avg_gain:.2f}, min={min_gain:.2f} (không tắt)")
    print(f"    Giọng to → nhạc giảm ~{(1-gain_min)*100:.0f}%  |  Giọng nhỏ → giảm ít")
    return ducked


# ═══════════════════════════════════════════════════
# 4. FADE OUT — Nhạc mờ dần cuối video
# ═══════════════════════════════════════════════════

def _apply_fadeout(audio, sr, fade_sec=FADE_OUT_SEC):
    """Fade out tuyến tính ở cuối audio."""
    fade_samples = int(sr * fade_sec)
    if fade_samples > len(audio):
        fade_samples = len(audio)
    fade = np.linspace(1.0, 0.0, fade_samples)
    # Sqrt fade cho mượt hơn linear
    fade = np.sqrt(fade)
    audio[-fade_samples:] *= fade
    print(f"  ✓ Fade out: {fade_sec}s cuối")
    return audio


# ═══════════════════════════════════════════════════
# 5. MIX — Trộn voiceover + BGM đã xử lý
# ═══════════════════════════════════════════════════

def mix_voiceover_bgm(voiceover_audio, bgm_ducked, sr=SR):
    """
    Trộn voiceover + BGM đã duck → 1 file WAV mono.
    Normalize để không clipping.
    """
    mixed = voiceover_audio + bgm_ducked

    # Normalize: đảm bảo peak ≤ 0.95
    peak = np.max(np.abs(mixed))
    if peak > 0.95:
        mixed = mixed * (0.95 / peak)
        print(f"  ✓ Normalize: peak {peak:.3f} → 0.950")

    # Fade out cuối
    mixed = _apply_fadeout(mixed, sr)

    return mixed


# ═══════════════════════════════════════════════════
# 6. VERIFY — Kiểm tra mix có ổn không
# ═══════════════════════════════════════════════════

def verify_mix(mixed_audio, voiceover_audio, sr=SR):
    """
    Kiểm tra chất lượng mix:
    - Voice nổi bật hơn BGM ở vùng có giọng
    - BGM lấp đầy khoảng lặng
    - Không clipping
    """
    print(f"\n{'='*50}")
    print(f"  Verify Mix")
    print(f"{'='*50}")

    checks = []

    # 1. Không clipping
    peak = np.max(np.abs(mixed_audio))
    ok_clip = peak < 0.99
    checks.append(("No clipping", ok_clip, f"peak={peak:.4f}"))

    # 2. Có audio (không phải silence)
    rms = np.sqrt(np.mean(mixed_audio ** 2))
    ok_rms = rms > 0.01
    checks.append(("Has audio", ok_rms, f"rms={rms:.4f}"))

    # 3. Voice-to-music ratio ở vùng có giọng
    envelope = _compute_envelope(voiceover_audio, sr)
    voice_mask = envelope > DUCK_THRESHOLD

    if np.any(voice_mask):
        # So sánh năng lượng voiceover vs mixed ở vùng giọng
        vo_energy = np.sqrt(np.mean(voiceover_audio[voice_mask] ** 2))
        mx_energy = np.sqrt(np.mean(mixed_audio[voice_mask] ** 2))
        # BGM thêm bao nhiêu vào vùng giọng
        bgm_contribution = (mx_energy - vo_energy) / vo_energy if vo_energy > 0 else 0
        ok_voice = bgm_contribution < 0.3  # BGM không quá 30% ở vùng giọng
        checks.append(("Voice dominant", ok_voice,
                        f"BGM adds {bgm_contribution:.0%} to voice regions"))

    # 4. BGM fills gaps
    silence_mask = envelope < DUCK_THRESHOLD * 0.5
    if np.any(silence_mask):
        mx_silence_rms = np.sqrt(np.mean(mixed_audio[silence_mask] ** 2))
        ok_fill = mx_silence_rms > 0.005  # Có nhạc ở gap
        checks.append(("BGM fills gaps", ok_fill,
                        f"gap rms={mx_silence_rms:.4f}"))

    # 5. Fade out cuối
    last_3s = mixed_audio[-int(sr * 3):]
    first_3s = mixed_audio[:int(sr * 3)]
    end_rms = np.sqrt(np.mean(last_3s ** 2))
    start_rms = np.sqrt(np.mean(first_3s ** 2))
    ok_fade = end_rms < start_rms * 0.5  # Cuối nhỏ hơn đầu
    checks.append(("Fade out end", ok_fade,
                    f"end_rms={end_rms:.4f} vs start_rms={start_rms:.4f}"))

    # Print results
    passed = 0
    for name, ok, detail in checks:
        status = "✅" if ok else "❌"
        print(f"  {status}  {name}: {detail}")
        if ok:
            passed += 1

    print(f"\n  Kết quả: {passed}/{len(checks)} passed")
    print(f"{'='*50}")
    return passed == len(checks)


# ═══════════════════════════════════════════════════
# 7. MUX VÀO VIDEO
# ═══════════════════════════════════════════════════

def _video_duration(path):
    """Lấy duration video từ ffmpeg probe."""
    r = subprocess.run(
        [FFMPEG, "-i", str(path), "-hide_banner"],
        capture_output=True, text=True,
    )
    for line in r.stderr.splitlines():
        if "Duration:" in line:
            t = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = t.split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    raise RuntimeError("Không parse được duration video")


def mux_to_video(video_in, mixed_wav, video_out):
    """Ghép audio đã mix vào video. Copy video, encode audio AAC."""
    v_dur = _video_duration(video_in)

    video_out = Path(video_out)
    video_out.parent.mkdir(parents=True, exist_ok=True)
    if video_out.exists():
        video_out.unlink()

    cmd = [
        FFMPEG, "-y", "-hide_banner", "-loglevel", "warning",
        "-i", str(video_in),
        "-i", str(mixed_wav),
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",                           # R8: không re-encode video
        "-c:a", "aac", "-b:a", "192k",
        "-ar", "44100", "-ac", "2",                # R10: AAC 192k, 44.1kHz, stereo
        "-af", f"apad=pad_dur={v_dur:.3f},atrim=0:{v_dur:.3f},asetpts=PTS-STARTPTS",
        "-shortest", "-movflags", "+faststart",
        str(video_out),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("STDERR:", r.stderr[-2000:])
        raise SystemExit(r.returncode)

    size_mb = video_out.stat().st_size / 1024 ** 2
    print(f"\n[OK] {video_out}  ({size_mb:.2f} MB)")


# ═══════════════════════════════════════════════════
# 8. PIPELINE CHÍNH
# ═══════════════════════════════════════════════════

def mix_and_mux(video_in, voiceover_path, bgm_path, video_out, bgm_db=None):
    """
    Full pipeline:
    1. Đọc voiceover
    2. Analyze BGM
    3. Process BGM (EQ + volume)
    4. Sidechain duck
    5. Mix voiceover + BGM
    6. Verify
    7. Mux vào video
    """
    global BGM_TARGET_DB
    if bgm_db is not None:
        BGM_TARGET_DB = bgm_db

    video_in = Path(video_in)
    voiceover_path = Path(voiceover_path)
    bgm_path = Path(bgm_path)
    video_out = Path(video_out)

    print("🎵 Step 1: Đọc voiceover...")
    voiceover_audio, vo_sr = sf.read(str(voiceover_path), dtype="float64")
    voiceover_audio = _ensure_mono(voiceover_audio)
    vo_info = analyze_audio(voiceover_path)
    print_analysis(vo_info, "Voiceover")

    print("🎶 Step 2: Analyze nhạc nền...")
    bgm_info = analyze_audio(bgm_path)
    print_analysis(bgm_info, "Background Music")
    if not bgm_info["is_suitable"]:
        print("⚠️ Nhạc nền không phù hợp, nhưng vẫn thử mix...")

    print("🔧 Step 3: Xử lý nhạc nền (EQ + volume)...")
    bgm_processed = process_bgm(bgm_path, voiceover_audio, vo_sr)

    print("🔊 Step 4: Sidechain ducking...")
    bgm_ducked = sidechain_duck(bgm_processed, voiceover_audio, vo_sr)

    print("🎼 Step 5: Trộn voiceover + BGM...")
    mixed = mix_voiceover_bgm(voiceover_audio, bgm_ducked, vo_sr)

    # Lưu file WAV đã mix
    mixed_wav = voiceover_path.parent / "voiceover_with_bgm.wav"
    sf.write(str(mixed_wav), mixed, vo_sr)
    print(f"  ✓ Saved: {mixed_wav} ({len(mixed)/vo_sr:.2f}s)")

    print("🔍 Step 6: Verify mix...")
    verify_mix(mixed, voiceover_audio, vo_sr)

    print("🎬 Step 7: Ghép vào video...")
    mux_to_video(video_in, mixed_wav, video_out)

    print("\n🎉 Xong! Video cuối:", video_out)
    return video_out


# ═══════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Mix voiceover + BGM → video")
    parser.add_argument("--bgm", required=True, help="Đường dẫn file nhạc nền")
    parser.add_argument("--video", default="input/video/extended-horse-21s-fixed.mp4",
                        help="Đường dẫn video gốc")
    parser.add_argument("--voiceover", default="outputs/voiceover_21s.wav",
                        help="Đường dẫn voiceover WAV")
    parser.add_argument("--output", default="outputs/extended-horse-21s-with-voiceover-bgm.mp4",
                        help="Đường dẫn video output")
    parser.add_argument("--bgm-db", type=float, default=-18,
                        help="Volume BGM so với voiceover (dB, mặc định -18)")
    args = parser.parse_args()

    mix_and_mux(args.video, args.voiceover, args.bgm, args.output, args.bgm_db)


if __name__ == "__main__":
    main()
