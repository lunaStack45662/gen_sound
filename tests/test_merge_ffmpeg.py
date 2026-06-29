"""
Standalone ffmpeg merge test (no GUI).
Generate video with 440Hz + WAV 880Hz -> merge -> verify.
"""
import subprocess
import sys
from pathlib import Path

# -- Config --
START_SEC = 5.5
END_SEC = 8.5
INSERT_DUR = END_SEC - START_SEC  # 3.0s
DELAY_MS = int(START_SEC * 1000)  # 5500
VID_DUR = 12.0  # short video for fast test

HERE = Path(__file__).parent
OUT_DIR = HERE / "_test_output"
OUT_DIR.mkdir(exist_ok=True)


def get_ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def make_test_video(ffmpeg: str, path: Path):
    """Create 12s video, 30fps, 640x480, audio 440Hz sine."""
    cmd = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", f"color=c=blue:size=640x480:d={VID_DUR}",
        "-f", "lavfi", "-i", f"sine=frequency=440:duration={VID_DUR}:sample_rate=44100",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        str(path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, f"Video creation error:\n{r.stderr}"
    print(f"  [OK] Create test video: {path.name}")


def make_test_wav(ffmpeg: str, path: Path):
    """Create 8s 880Hz sine WAV."""
    wav_dur = 8.0
    cmd = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", f"sine=frequency=880:duration={wav_dur}:sample_rate=44100",
        "-ac", "1",
        str(path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, f"WAV creation error:\n{r.stderr}"
    print(f"  [OK] Create test WAV: {path.name}")


def run_merge(ffmpeg: str, video_path: Path, wav_path: Path, out_path: Path):
    """Run exact ffmpeg command from _do_merge."""
    # Probe video duration + has_audio
    r = subprocess.run([ffmpeg, "-i", str(video_path), "-hide_banner"],
                       capture_output=True, text=True)
    has_audio = "Audio:" in r.stderr
    vid_dur = 0.0
    for line in r.stderr.splitlines():
        if "Duration:" in line:
            t = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = t.split(":")
            vid_dur = int(h) * 3600 + int(m) * 60 + float(s)
    assert vid_dur > 0, f"Cannot read duration from: {video_path}"

    # has_audio=True branch (video has audio)
    fc = (
        f"[0:a:0]volume=0:enable='between(t,{START_SEC},{END_SEC})'[muted];"
        f"[1:a:0]atrim=end={INSERT_DUR}[trimmed];"
        f"[trimmed]adelay={DELAY_MS}:all=1[delayed];"
        f"[delayed]apad=whole_dur={vid_dur}[padded];"
        f"[muted][padded]amix=inputs=2:duration=first:weights=1 1,volume=2[outa]"
    )
    cmd = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "warning",
        "-i", str(video_path), "-i", str(wav_path),
        "-filter_complex", fc,
        "-map", "0:v:0", "-map", "[outa]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-t", str(vid_dur), str(out_path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, f"Merge error:\n{r.stderr}"
    print(f"  [OK] Merge success: {out_path.name}")
    print(f"       fc={fc}")
    print(f"       has_audio={has_audio}, vid_dur={vid_dur}")


def analyze_output(ffmpeg: str, path: Path):
    """Check audio at various time positions."""
    print(f"\n  -- Analyze: {path.name} --")

    # 1. Overview
    r = subprocess.run([ffmpeg, "-i", str(path), "-hide_banner"],
                       capture_output=True, text=True)
    dur_info = ""
    for line in r.stderr.splitlines():
        if "Duration:" in line:
            dur_info = line.strip()
        if "Audio:" in line:
            dur_info += f" | {line.strip()}"
    print(f"       {dur_info}")

    # 2. Check amplitude at multiple times
    test_points = [
        (0.0, "before segment (0s)"),
        (3.0, "before segment (3s)"),
        (START_SEC + 0.1, "at segment start"),
        (END_SEC - 0.1, "at segment end"),
        (END_SEC + 0.5, "after segment"),
        (VID_DUR - 0.5, "near end"),
    ]

    all_ok = True
    for t, desc in test_points:
        if t >= VID_DUR:
            continue
        r = subprocess.run([
            ffmpeg, "-y", "-hide_banner",
            "-ss", str(t), "-i", str(path),
            "-t", "0.3", "-af", "volumedetect",
            "-f", "null", "NUL",
        ], capture_output=True, text=True)
        mean_vol = "?"
        max_vol = "?"
        for line in r.stderr.splitlines():
            if "mean_volume" in line:
                mean_vol = line.split("mean_volume:")[1].strip().split()[0]
            if "max_volume" in line:
                max_vol = line.split("max_volume:")[1].strip().split()[0]
        has_audio = mean_vol not in ("?", "-inf")
        status = "[OK]" if has_audio else "[SILENT]"
        if not has_audio:
            all_ok = False
        print(f"       {status} {desc}  mean={mean_vol}dB  max={max_vol}dB")

    return all_ok


def test_has_audio_true():
    """Branch: has_audio=True (video with 440Hz)."""
    print("\n=== TEST: has_audio=True ===")
    ffmpeg = get_ffmpeg()
    video = OUT_DIR / "test_video_has_audio.mp4"
    wav = OUT_DIR / "test_wav_880.wav"
    out = OUT_DIR / "test_merged_has_audio.mp4"

    make_test_video(ffmpeg, video)
    make_test_wav(ffmpeg, wav)
    run_merge(ffmpeg, video, wav, out)
    ok = analyze_output(ffmpeg, out)
    print(f"  => {'PASS' if ok else 'FAIL'}\n")
    return ok


def test_has_audio_false():
    """Branch: has_audio=False (no audio)."""
    print("\n=== TEST: has_audio=False ===")
    ffmpeg = get_ffmpeg()
    video = OUT_DIR / "test_video_no_audio.mp4"
    wav = OUT_DIR / "test_wav_880.wav"
    out = OUT_DIR / "test_merged_no_audio.mp4"

    cmd = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", f"color=c=red:size=640x480:d={VID_DUR}",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
        "-an",
        "-pix_fmt", "yuv420p",
        str(video),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, f"Video creation error:\n{r.stderr}"
    print(f"  [OK] Create silent video: {video.name}")

    if not wav.exists():
        make_test_wav(ffmpeg, wav)

    r = subprocess.run([ffmpeg, "-i", str(video), "-hide_banner"],
                       capture_output=True, text=True)
    has_audio = "Audio:" in r.stderr
    vid_dur = 0.0
    for line in r.stderr.splitlines():
        if "Duration:" in line:
            t = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = t.split(":")
            vid_dur = int(h) * 3600 + int(m) * 60 + float(s)
    assert vid_dur > 0

    fc = (
        f"[1:a:0]atrim=end={INSERT_DUR}[trimmed];"
        f"[trimmed]adelay={DELAY_MS}:all=1[delayed];"
        f"[delayed]apad=whole_dur={vid_dur}[outa]"
    )
    cmd = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "warning",
        "-i", str(video), "-i", str(wav),
        "-filter_complex", fc,
        "-map", "0:v:0", "-map", "[outa]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-t", str(vid_dur), str(out),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, f"Merge error no_audio:\n{r.stderr}"
    print(f"  [OK] Merge success: {out.name}")

    ok = analyze_output(ffmpeg, out)
    print(f"  => {'PASS' if ok else 'FAIL'}\n")
    return ok


def test_video_silent_audio_stream():
    """Video has audio stream but silent (like user's video-34.mp4)."""
    print("\n=== TEST: silent audio stream (like video-34) ===")
    ffmpeg = get_ffmpeg()
    video = OUT_DIR / "test_video_silent_audio.mp4"
    wav = OUT_DIR / "test_wav_880.wav"
    out = OUT_DIR / "test_merged_silent_audio.mp4"

    cmd = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", f"color=c=green:size=640x480:d={VID_DUR}",
        "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=mono:d={VID_DUR}",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        "-pix_fmt", "yuv420p",
        str(video),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, f"Video creation error:\n{r.stderr}"
    print(f"  [OK] Create silent-audio video: {video.name}")

    if not wav.exists():
        make_test_wav(ffmpeg, wav)

    r = subprocess.run([ffmpeg, "-i", str(video), "-hide_banner"],
                       capture_output=True, text=True)
    has_audio = "Audio:" in r.stderr
    vid_dur = 0.0
    for line in r.stderr.splitlines():
        if "Duration:" in line:
            t = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = t.split(":")
            vid_dur = int(h) * 3600 + int(m) * 60 + float(s)
    assert vid_dur > 0
    print(f"       has_audio={has_audio}, vid_dur={vid_dur} (must have audio even if silent)")

    fc = (
        f"[0:a:0]volume=0:enable='between(t,{START_SEC},{END_SEC})'[muted];"
        f"[1:a:0]atrim=end={INSERT_DUR}[trimmed];"
        f"[trimmed]adelay={DELAY_MS}:all=1[delayed];"
        f"[delayed]apad=whole_dur={vid_dur}[padded];"
        f"[muted][padded]amix=inputs=2:duration=first:weights=1 1,volume=2[outa]"
    )
    cmd = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "warning",
        "-i", str(video), "-i", str(wav),
        "-filter_complex", fc,
        "-map", "0:v:0", "-map", "[outa]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-t", str(vid_dur), str(out),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, f"Merge error silent_audio:\n{r.stderr}"
    print(f"  [OK] Merge success: {out.name}")

    ok = analyze_output(ffmpeg, out)
    print(f"  => {'PASS' if ok else 'FAIL'}\n")
    return ok


if __name__ == "__main__":
    results = []
    results.append(("has_audio=True", test_has_audio_true()))
    results.append(("has_audio=False", test_has_audio_false()))
    results.append(("silent_audio_stream", test_video_silent_audio_stream()))

    print("=" * 60)
    print("SUMMARY:")
    for name, ok in results:
        print(f"  {'PASS' if ok else 'FAIL'} - {name}")
    print("=" * 60)
    sys.exit(0 if all(r[1] for r in results) else 1)
