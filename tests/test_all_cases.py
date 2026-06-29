"""
Comprehensive merge test: all edge cases, chain merge, overlap, WAV sizing.
"""
import subprocess, sys, os
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / "_test_output"
OUT.mkdir(exist_ok=True)

sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

FFMPEG = None
def get_ffmpeg():
    global FFMPEG
    if FFMPEG is None:
        import imageio_ffmpeg
        FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
    return FFMPEG

def probe(path):
    r = subprocess.run([get_ffmpeg(), "-i", str(path), "-hide_banner"],
                       capture_output=True, text=True)
    has_audio = "Audio:" in r.stderr
    vid_dur = 0.0
    for line in r.stderr.splitlines():
        if "Duration:" in line:
            t = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = t.split(":")
            vid_dur = int(h) * 3600 + int(m) * 60 + float(s)
    return has_audio, vid_dur

def analyze(path, points):
    """Check audio at multiple time positions. Returns list of (desc, ok, meanVol)."""
    results = []
    for sec, desc in points:
        r = subprocess.run([
            get_ffmpeg(), "-y", "-hide_banner",
            "-ss", str(sec), "-i", str(path),
            "-t", "0.3", "-af", "volumedetect",
            "-f", "null", "NUL",
        ], capture_output=True, text=True)
        mean_vol = None
        for line in r.stderr.splitlines():
            if "mean_volume" in line:
                mean_vol = float(line.split("mean_volume:")[1].strip().split()[0])
        has = mean_vol is not None and mean_vol > -80 if mean_vol is not None else False
        results.append((desc, has, mean_vol))
    return results

def make_video(path, duration, has_audio=True, freq=440):
    ff = get_ffmpeg()
    src = [ff, "-y", "-hide_banner", "-loglevel", "error",
           "-f", "lavfi", "-i", f"color=c=blue:size=640x480:d={duration}"]
    if has_audio:
        src += ["-f", "lavfi", "-i", f"sine=frequency={freq}:duration={duration}:sample_rate=44100"]
        src += ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                "-c:a", "aac", "-b:a", "128k", "-shortest"]
    else:
        src += ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "28", "-an"]
    src += ["-pix_fmt", "yuv420p", str(path)]
    r = subprocess.run(src, capture_output=True, text=True)
    assert r.returncode == 0, f"mkvideo error: {r.stderr[-200:]}"

def make_wav(path, duration, freq=880, sample_rate=44100):
    ff = get_ffmpeg()
    r = subprocess.run([
        ff, "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", f"sine=frequency={freq}:duration={duration}:sample_rate={sample_rate}",
        "-ac", "1", str(path),
    ], capture_output=True, text=True)
    assert r.returncode == 0, f"wav error: {r.stderr[-200:]}"

def run_merge_has_audio(video_path, wav_path, out_path, start, end):
    """has_audio=True branch (video has audio)."""
    ff = get_ffmpeg()
    has_audio, vid_dur = probe(video_path)
    assert has_audio, "video must have audio"
    insert_dur = end - start
    delay_ms = int(start * 1000)
    fc = (
        f"[0:a:0]volume=0:enable='between(t,{start},{end})'[muted];"
        f"[1:a:0]atrim=end={insert_dur}[trimmed];"
        f"[trimmed]adelay={delay_ms}:all=1[delayed];"
        f"[delayed]apad=whole_dur={vid_dur}[padded];"
        f"[muted][padded]amix=inputs=2:duration=first:weights=1 1,volume=2[outa]"
    )
    cmd = [ff, "-y", "-hide_banner", "-loglevel", "warning",
           "-i", str(video_path), "-i", str(wav_path),
           "-filter_complex", fc,
           "-map", "0:v:0", "-map", "[outa]",
           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
           "-t", str(vid_dur), str(out_path)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, f"merge error: {r.stderr[-300:]}"
    return vid_dur

def run_merge_no_audio(video_path, wav_path, out_path, start, end):
    """has_audio=False branch (video without audio)."""
    ff = get_ffmpeg()
    _, vid_dur = probe(video_path)
    insert_dur = end - start
    delay_ms = int(start * 1000)
    fc = (
        f"[1:a:0]atrim=end={insert_dur}[trimmed];"
        f"[trimmed]adelay={delay_ms}:all=1[delayed];"
        f"[delayed]apad=whole_dur={vid_dur}[outa]"
    )
    cmd = [ff, "-y", "-hide_banner", "-loglevel", "warning",
           "-i", str(video_path), "-i", str(wav_path),
           "-filter_complex", fc,
           "-map", "0:v:0", "-map", "[outa]",
           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
           "-t", str(vid_dur), str(out_path)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, f"merge no_audio error: {r.stderr[-300:]}"

def run_chain_merge(video_path, segments, out_path):
    """Chain merge like _do_merge: multiple segments one by one."""
    ff = get_ffmpeg()
    current = str(video_path)
    for i, (start, end, wav_path) in enumerate(segments):
        part = str(OUT / f"chain_part_{i}.mp4")
        has_audio, vid_dur = probe(current)
        insert_dur = end - start
        delay_ms = int(start * 1000)
        if has_audio:
            fc = (
                f"[0:a:0]volume=0:enable='between(t,{start},{end})'[muted];"
                f"[1:a:0]atrim=end={insert_dur}[trimmed];"
                f"[trimmed]adelay={delay_ms}:all=1[delayed];"
                f"[delayed]apad=whole_dur={vid_dur}[padded];"
                f"[muted][padded]amix=inputs=2:duration=first:weights=1 1,volume=2[outa]"
            )
        else:
            fc = (
                f"[1:a:0]atrim=end={insert_dur}[trimmed];"
                f"[trimmed]adelay={delay_ms}:all=1[delayed];"
                f"[delayed]apad=whole_dur={vid_dur}[outa]"
            )
        cmd = [ff, "-y", "-hide_banner", "-loglevel", "warning",
               "-i", current, "-i", str(wav_path),
               "-filter_complex", fc,
               "-map", "0:v:0", "-map", "[outa]",
               "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
               "-t", str(vid_dur), part]
        r = subprocess.run(cmd, capture_output=True, text=True)
        assert r.returncode == 0, f"chain {i} error: {r.stderr[-300:]}"
        current = part

    import shutil
    shutil.move(current, str(out_path))
    for p in OUT.glob("chain_part_*.mp4"):
        p.unlink(missing_ok=True)

PASS = 0
FAIL = 0
def check(name, ok):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}")

# ── Test cases ──

def test_basic_has_audio():
    print("\n--- Basic: has_audio=True ---")
    v = OUT / "t_basic_v.mp4"
    w = OUT / "t_basic_w.wav"
    o = OUT / "t_basic_out.mp4"
    make_video(v, 12.0, has_audio=True, freq=440)
    make_wav(w, 8.0, freq=880)
    run_merge_has_audio(v, w, o, 2.0, 5.0)
    res = analyze(o, [(0.5, "before"), (3.0, "inside"), (6.0, "after")])
    for desc, has, vol in res:
        check(f"audio {desc} (mean={vol}dB)", has == True)

def test_basic_no_audio():
    print("\n--- Basic: has_audio=False ---")
    v = OUT / "t_basic_noa_v.mp4"
    w = OUT / "t_basic_noa_w.wav"
    o = OUT / "t_basic_noa_out.mp4"
    make_video(v, 10.0, has_audio=False)
    make_wav(w, 4.0, freq=660)
    run_merge_no_audio(v, w, o, 3.0, 6.0)
    res = analyze(o, [(1.0, "before (silent)"), (4.0, "inside"), (7.5, "after (silent)")])
    for desc, has, vol in res:
        check(f"audio {desc} (mean={vol}dB)",
              (has if "inside" in desc else not has))

def test_position_zero():
    print("\n--- Edge: segment at position 0 ---")
    v = OUT / "t_zero_v.mp4"
    w = OUT / "t_zero_w.wav"
    o = OUT / "t_zero_out.mp4"
    make_video(v, 8.0, has_audio=False)
    make_wav(w, 3.0, freq=440)
    run_merge_no_audio(v, w, o, 0.0, 3.0)
    res = analyze(o, [(0.1, "at 0 (should play)"), (2.0, "middle"), (4.0, "after (silent)")])
    for desc, has, vol in res:
        check(f"audio {desc} (mean={vol}dB)",
              (has if "silent" not in desc else not has))

def test_position_end():
    print("\n--- Edge: segment at video end ---")
    v = OUT / "t_end_v.mp4"
    w = OUT / "t_end_w.wav"
    o = OUT / "t_end_out.mp4"
    make_video(v, 6.0, has_audio=False)
    make_wav(w, 2.0, freq=550)
    run_merge_no_audio(v, w, o, 4.0, 6.0)
    res = analyze(o, [(2.0, "before (silent)"), (4.5, "inside"), (5.9, "near end")])
    for desc, has, vol in res:
        check(f"audio {desc} (mean={vol}dB)",
              (has if "silent" not in desc else not has))

def test_wav_shorter_than_insert():
    print("\n--- Edge: WAV 2s, insert 4s (atrim pad -> WAV only 2s, then silence) ---")
    v = OUT / "t_shortwav_v.mp4"
    w = OUT / "t_shortwav_w.wav"
    o = OUT / "t_shortwav_out.mp4"
    make_video(v, 10.0, has_audio=False)
    make_wav(w, 2.0, freq=770)
    run_merge_no_audio(v, w, o, 3.0, 7.0)
    res = analyze(o, [
        (3.1, "segment_start"),
        (4.5, "mid_segment"),
        (5.1, "after_wav_end"),  # atrim keeps 2s of WAV, then silence
        (7.5, "after_segment_end"),
    ])
    for desc, has, vol in res:
        expect_audio = desc in ("segment_start", "mid_segment")
        check(f"audio {desc} (mean={vol}dB)", has == expect_audio)

def test_wav_longer_than_insert():
    print("\n--- Edge: WAV 6s, insert 2s (atrim cuts to 2s) ---")
    v = OUT / "t_longwav_v.mp4"
    w = OUT / "t_longwav_w.wav"
    o = OUT / "t_longwav_out.mp4"
    make_video(v, 10.0, has_audio=True, freq=300)
    make_wav(w, 6.0, freq=990)
    run_merge_has_audio(v, w, o, 4.0, 6.0)
    res = analyze(o, [
        (2.0, "before segment (original 300Hz)"),
        (4.1, "segment start (990Hz inserted, 300Hz muted)"),
        (4.5, "segment mid (990Hz)"),
        (5.9, "segment end (990Hz)"),
        (6.5, "after segment end (original 300Hz, WAV cut)"),
    ])
    for desc, has, vol in res:
        check(f"audio {desc} (mean={vol}dB)", has)

def test_chain_2segments():
    print("\n--- Chain: 2 non-overlapping segments ---")
    v = OUT / "t_chain2_v.mp4"
    w1 = OUT / "t_chain2_w1.wav"
    w2 = OUT / "t_chain2_w2.wav"
    o = OUT / "t_chain2_out.mp4"
    make_video(v, 12.0, has_audio=True, freq=400)
    make_wav(w1, 2.0, freq=600)
    make_wav(w2, 2.0, freq=800)
    run_chain_merge(v, [(1.0, 3.0, w1), (7.0, 9.0, w2)], o)
    res = analyze(o, [
        (0.5, "before first (400Hz)"),
        (2.0, "first segment (600Hz)"),
        (4.0, "between (400Hz)"),
        (8.0, "second segment (800Hz)"),
        (10.0, "after second (400Hz)"),
    ])
    for desc, has, vol in res:
        check(f"audio {desc} (mean={vol}dB)", has)

def test_chain_overlap():
    print("\n--- Chain: 2 overlapping segments ---")
    v = OUT / "t_chainov_v.mp4"
    w1 = OUT / "t_chainov_w1.wav"
    w2 = OUT / "t_chainov_w2.wav"
    o = OUT / "t_chainov_out.mp4"
    make_video(v, 10.0, has_audio=True, freq=350)
    make_wav(w1, 4.0, freq=700)
    make_wav(w2, 4.0, freq=900)
    # sorted by start: S1 at 2-6, S2 at 4-8
    run_chain_merge(v, [(2.0, 6.0, w1), (4.0, 8.0, w2)], o)
    res = analyze(o, [
        (1.0, "before overlap (350Hz)"),
        (3.0, "only S1 (700Hz)"),
        (5.0, "overlap S1+S2"),
        (7.0, "only S2 (900Hz)"),
        (9.0, "after both (350Hz)"),
    ])
    for desc, has, vol in res:
        check(f"audio {desc} (mean={vol}dB)", has)

def test_chain_3segments():
    print("\n--- Chain: 3 segments ---")
    v = OUT / "t_chain3_v.mp4"
    o = OUT / "t_chain3_out.mp4"
    make_video(v, 15.0, has_audio=False)
    wavs = []
    segs = []
    for i, (s, e, freq) in enumerate([(1, 3, 500), (5, 7, 600), (9, 11, 700)]):
        wp = OUT / f"t_chain3_w{i}.wav"
        make_wav(wp, e-s, freq=freq)
        wavs.append(wp)
        segs.append((s, e, wp))
    run_chain_merge(v, segs, o)
    res = analyze(o, [
        (0.0, "before all (silent)"),
        (2.0, "segment1 (500Hz)"),
        (4.0, "between1-2 (silent)"),
        (6.0, "segment2 (600Hz)"),
        (8.0, "between2-3 (silent)"),
        (10.0, "segment3 (700Hz)"),
        (12.0, "after all (silent)"),
    ])
    for desc, has, vol in res:
        check(f"audio {desc} (mean={vol}dB)",
              (has if "silent" not in desc else not has))

def test_real_user_wav():
    """Test with user's actual WAV files (if available)."""
    print("\n--- Real file: test with user's WAV ---")
    user_wavs = [
        Path("filewov/mau_giong_nu_healing.wav"),
        Path("filewov/mau_giong_nam_healing.wav"),
    ]
    found = [p for p in user_wavs if p.exists()]
    if not found:
        print("  SKIP  user WAV not found")
        return True

    for wav_path in found:
        print(f"  Using: {wav_path}")
        v = OUT / f"t_real_{wav_path.stem}_v.mp4"
        o = OUT / f"t_real_{wav_path.stem}_out.mp4"
        make_video(v, 15.0, has_audio=False)
        dur_r = subprocess.run([get_ffmpeg(), "-i", str(wav_path), "-hide_banner"],
                               capture_output=True, text=True)
        wav_dur = 0.0
        for line in dur_r.stderr.splitlines():
            if "Duration:" in line:
                t = line.split("Duration:")[1].split(",")[0].strip()
                h, m, s = t.split(":")
                wav_dur = int(h) * 3600 + int(m) * 60 + float(s)
        print(f"    WAV duration: {wav_dur:.2f}s")
        if wav_dur <= 0:
            print("  SKIP  cannot detect WAV duration")
            continue

        start, end = 5.5, min(5.5 + wav_dur, 14.0)
        run_merge_no_audio(v, wav_path, o, start, end)
        check_pts = [
            (2.0, "before"),
            (start + 0.1, "at_start"),
            ((start + end) / 2, "middle"),
            (end - 0.1, "at_end"),
            (end + 0.5, "after"),
        ]
        expect_audio_tags = {"at_start", "middle", "at_end"}
        res = analyze(o, check_pts)
        for desc, has, vol in res:
            check(f"  {wav_path.stem} {desc} (mean={vol}dB)",
                  has == (desc in expect_audio_tags))

def test_real_video34():
    """Test with user's video-34.mp4 (if available)."""
    print("\n--- Real file: video-34.mp4 + user WAV ---")
    base = HERE.parent
    video_path = base / "filewov/video-34.mp4"
    wav_path = base / "filewov/mau_giong_nu_healing.wav"
    if not video_path.exists() or not wav_path.exists():
        print(f"  SKIP  files not found: {video_path}, {wav_path}")
        return True

    _, vid_dur = probe(video_path)
    print(f"  Video: {video_path.name}, duration={vid_dur:.2f}s")

    dur_r = subprocess.run([get_ffmpeg(), "-i", str(wav_path), "-hide_banner"],
                           capture_output=True, text=True)
    wav_dur = 0.0
    for line in dur_r.stderr.splitlines():
        if "Duration:" in line:
            t = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = t.split(":")
            wav_dur = int(h) * 3600 + int(m) * 60 + float(s)
    print(f"  WAV: {wav_path.name}, duration={wav_dur:.2f}s")

    o = OUT / "t_video34_merged.mp4"
    # has_audio=True branch (video-34 has silent audio stream)
    start, end = 5.5, min(5.5 + wav_dur, vid_dur - 0.5)
    insert_dur = end - start

    has_audio, _ = probe(video_path)
    print(f"  has_audio={has_audio}")

    ff = get_ffmpeg()
    delay_ms = int(start * 1000)
    fc = (
        f"[0:a:0]volume=0:enable='between(t,{start},{end})'[muted];"
        f"[1:a:0]atrim=end={insert_dur}[trimmed];"
        f"[trimmed]adelay={delay_ms}:all=1[delayed];"
        f"[delayed]apad=whole_dur={vid_dur}[padded];"
        f"[muted][padded]amix=inputs=2:duration=first:weights=1 1,volume=2[outa]"
    )
    cmd = [ff, "-y", "-hide_banner", "-loglevel", "warning",
           "-i", str(video_path), "-i", str(wav_path),
           "-filter_complex", fc,
           "-map", "0:v:0", "-map", "[outa]",
           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
           "-t", str(vid_dur), str(o)]
    print(f"  cmd: {cmd}")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  FAIL merge rc={r.returncode}: {r.stderr[-500:]}")
        return False
    print(f"  Merge OK")

    res = analyze(o, [
        (2.0, "before_segment"),
        (start + 0.3, "segment_start"),
        ((start + end) / 2, "mid_segment"),
        (end - 0.2, "segment_end"),
        (end + 0.5, "after_segment"),
        (vid_dur - 0.5, "near_end"),
    ])
    expect_audio_tags = {"segment_start", "mid_segment", "segment_end"}
    for desc, has, vol in res:
        expect_audio = desc in expect_audio_tags
        check(f"  {desc} (mean={vol}dB)", has == expect_audio)

# ── Tests for GUI editing correctness ──

def test_edit_save_validation():
    """Validate _edit_segment logic (no UI)."""
    print("\n--- Edit: validation rules ---")
    dur = 60.0

    # Simulate a segment
    seg = {"start": 0.0, "end": 8.0}

    cases = [
        (5.5, 8.5, True,   "valid start < end"),
        (8.5, 5.5, False,  "start > end invalid"),
        (5.5, 5.5, False,  "start == end invalid"),
        (-1, 5.0, False,   "negative start invalid"),
        (55.0, 65.0, False,"end > duration invalid"),
        (0.0, 60.0, True,  "edge: end == duration valid"),
        (0.0, 8.0, True,   "unchanged valid"),
    ]
    for s, e, exp, desc in cases:
        seg["start"], seg["end"] = 0.0, 8.0
        ok = (s >= 0 and e <= dur and s < e)
        check(f"  {desc} (s={s}, e={e}) -> {'OK' if ok else 'FAIL'}",
              ok == exp)

def test_timeline_position_resolution():
    """Verify pixel-to-second mapping matches segment positions."""
    print("\n--- Timeline: pixel-to-second resolution ---")
    cw = 800
    dur = 60.0

    # _x_to_sec: max(0, min(x/w, 1)) * dur
    def x_to_sec(x): return max(0, min(x / cw, 1)) * dur

    # _draw_timeline: sx = int((seg["start"] / dur) * cw)
    def start_px(s): return int((s / dur) * cw)

    # _seg_at: sec = x_to_sec(x); seg["start"] <= sec <= seg["end"]
    def seg_at(x, seg_start, seg_end):
        sec = x_to_sec(x)
        return seg_start <= sec <= seg_end

    # Test: segment at 5.5s, drawn at pixel 73
    px = start_px(5.5)
    check(f"  5.5s -> pixel {px} (expected 73)", px == 73)

    # Click at pixel 73 -> sec should be >= 5.5
    clickable = seg_at(73, 5.5, 8.5)
    # 73/800*60 = 5.475 < 5.5 -> NOT clickable
    check(f"  pixel 73 selects segment at 5.5s -> {clickable}", clickable == False)

    # Click at pixel 74 -> sec should be >= 5.5
    clickable = seg_at(74, 5.5, 8.5)
    check(f"  pixel 74 selects segment at 5.5s -> {clickable}", clickable == True)

    # Drag delta calculation
    def drag_delta(x1, x2):
        return ((x2 - x1) / cw) * dur

    # Drag from px 73 to px 146 -> delta = (146-73)/800*60 = 5.475s
    delta = drag_delta(73, 146)
    check(f"  drag 73->146: delta={delta:.3f}s (expected ~5.475s)",
          abs(delta - 5.475) < 0.01)


# ── Run ──

if __name__ == "__main__":
    tests = [
        ("basic_has_audio", test_basic_has_audio),
        ("basic_no_audio", test_basic_no_audio),
        ("position_zero", test_position_zero),
        ("position_end", test_position_end),
        ("wav_shorter_than_insert", test_wav_shorter_than_insert),
        ("wav_longer_than_insert", test_wav_longer_than_insert),
        ("chain_2segments", test_chain_2segments),
        ("chain_overlap", test_chain_overlap),
        ("chain_3segments", test_chain_3segments),
        ("real_user_wav", test_real_user_wav),
        ("real_video34", test_real_video34),
        ("edit_validation", test_edit_save_validation),
        ("timeline_resolution", test_timeline_position_resolution),
    ]

    for name, fn in tests:
        try:
            fn()
        except Exception as e:
            import traceback
            print(f"  FAIL  {name}: {e}")
            traceback.print_exc()
            FAIL += 1

    print(f"\n{'='*50}")
    print(f"PASS={PASS}  FAIL={FAIL}")
    print(f"{'='*50}")
    sys.exit(0 if FAIL == 0 else 1)
