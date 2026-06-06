"""
Ghep am thanh voiceover_21s.wav vao video 21s.

Chien luoc:
  - Keep video stream (h264 416x752 24fps), re-encode khong can thiet (copy).
  - Replace audio track bang voiceover_21s.wav (resample 24kHz -> 44.1kHz de match video).
  - Pad audio len dung 21.04s neu thieu (silence), trim neu thua.
  - Encode AAC 192kbps stereo de giu parity voi audio goc.
  - Luu output o outputs/extended-horse-21s-with-voiceover.mp4.
"""
import subprocess
import wave
from pathlib import Path

import imageio_ffmpeg
from soundfile import SoundFile

VIDEO_IN = Path("extended-horse-21s-fixed.mp4")
WAV_IN = Path("outputs/voiceover_21s.wav")
VIDEO_OUT = Path("outputs/extended-horse-21s-with-voiceover.mp4")

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / w.getframerate()


def video_duration(path: Path) -> float:
    """Parse Duration tu ffmpeg probe (chinh xac den ms)."""
    r = subprocess.run(
        [FFMPEG, "-i", str(path), "-hide_banner"],
        capture_output=True, text=True,
    )
    for line in r.stderr.splitlines():
        if "Duration:" in line:
            t = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = t.split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    raise RuntimeError("Khong parse duoc duration video")


def main():
    if not VIDEO_IN.exists():
        raise FileNotFoundError(VIDEO_IN)
    if not WAV_IN.exists():
        raise FileNotFoundError(WAV_IN)

    v_dur = video_duration(VIDEO_IN)
    a_dur = wav_duration(WAV_IN)
    print(f"Video:  {VIDEO_IN.name}  dur={v_dur:.3f}s")
    print(f"Audio:  {WAV_IN.name}    dur={a_dur:.3f}s")
    delta = v_dur - a_dur
    if abs(delta) < 0.01:
        print("   (lengths match, khong can pad/trim)")
    elif delta > 0:
        print(f"   audio ngan hon video {delta*1000:.0f}ms -> se PAD SILENCE cuoi")
    else:
        print(f"   audio dai hon video {-delta*1000:.0f}ms -> se TRIM cuoi")

    with SoundFile(str(WAV_IN)) as sf:
        sr_in = sf.samplerate
        ch_in = sf.channels
    print(f"WAV format: {ch_in}ch @ {sr_in}Hz")

    if VIDEO_OUT.exists():
        VIDEO_OUT.unlink()

    cmd = [
        FFMPEG, "-y", "-hide_banner", "-loglevel", "warning",
        "-i", str(VIDEO_IN),
        "-i", str(WAV_IN),
        "-map", "0:v:0",          # video stream tu input 0
        "-map", "1:a:0",          # audio stream tu input 1
        "-c:v", "copy",            # khong re-encode video (giu chat luong, nhanh)
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "44100",            # match audio goc cua video
        "-ac", "2",                # stereo (giong audio goc)
        "-af", "apad=pad_dur={:.3f},atrim=0:{:.3f},asetpts=PTS-STARTPTS".format(v_dur, v_dur),
        "-shortest",               # dung tai stream ngan hon (an toan)
        "-movflags", "+faststart", # cho phep play ngay khi download
        str(VIDEO_OUT),
    ]
    print(f"\n>> {subprocess.list2cmdline(cmd)}\n")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("STDERR:", r.stderr[-2000:])
        raise SystemExit(r.returncode)
    if r.stderr.strip():
        print(r.stderr)

    size_mb = VIDEO_OUT.stat().st_size / 1024 ** 2
    print(f"\n[OK] {VIDEO_OUT}  ({size_mb:.2f} MB)")

    # Verify output
    print("\n--- Verify output ---")
    r2 = subprocess.run(
        [FFMPEG, "-i", str(VIDEO_OUT), "-hide_banner"],
        capture_output=True, text=True,
    )
    for line in r2.stderr.splitlines():
        if "Duration" in line or "Stream #0" in line:
            print(" ", line.strip())


if __name__ == "__main__":
    main()
