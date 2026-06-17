"""
Cắt (trim) video từ timecode start đến end.
Dùng ffmpeg -c copy → không re-encode, giữ nguyên chất lượng.

Cách dùng:
    python video_editor/trim_video.py --input input/video-edit/clip.mp4 ^
        --start 00:01:30 --end 00:02:45 --output output/video-edit/trimmed.mp4

    # Dùng duration thay vì end:
    python video_editor/trim_video.py --input input/video-edit/clip.mp4 ^
        --start 00:01:30 --duration 75 --output output/video-edit/trimmed.mp4

    # Re-encode (chậm hơn nhưng chính xác đến từng frame):
    python video_editor/trim_video.py --input clip.mp4 --start 00:01:30.500 ^
        --end 00:02:45.250 --output trimmed.mp4 --reencode
"""

import argparse
import subprocess
from pathlib import Path

import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def _parse_timecode(tc: str) -> float:
    parts = tc.split(":")
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    else:
        return float(parts[0])


def _format_timecode(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds - h * 3600 - m * 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def _video_info(path: Path) -> dict:
    r = subprocess.run(
        [FFMPEG, "-i", str(path), "-hide_banner"],
        capture_output=True, text=True,
    )
    info = {"duration": 0.0, "video_codec": "unknown", "audio_codec": "unknown"}
    for line in r.stderr.splitlines():
        if "Duration:" in line:
            t = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = t.split(":")
            info["duration"] = int(h) * 3600 + int(m) * 60 + float(s)
        if "Stream #0:0" in line and "Video:" in line:
            parts = line.split("Video:")[1].split(",")[0].strip()
            info["video_codec"] = parts.split()[0] if parts else "unknown"
        if "Stream #0:1" in line and "Audio:" in line:
            parts = line.split("Audio:")[1].split(",")[0].strip()
            info["audio_codec"] = parts.split()[0] if parts else "unknown"
    return info


def trim_video(
    input_path: Path,
    output_path: Path,
    start: float = 0.0,
    end: float | None = None,
    duration: float | None = None,
    reencode: bool = False,
):
    if not input_path.exists():
        raise FileNotFoundError(f"Khong tim thay video: {input_path}")

    info = _video_info(input_path)
    v_dur = info["duration"]
    print(f"Video:  {input_path.name}  dur={v_dur:.3f}s")
    print(f"  Codec: video={info['video_codec']}, audio={info['audio_codec']}")

    if end is None and duration is not None:
        end = start + duration
    if end is None:
        end = v_dur
    if start >= end:
        raise ValueError(f"start ({start:.3f}s) >= end ({end:.3f}s)")
    if start > v_dur:
        raise ValueError(f"start ({start:.3f}s) > video duration ({v_dur:.3f}s)")
    end = min(end, v_dur)

    print(f"  Trim:  {_format_timecode(start)} → {_format_timecode(end)}  ({end - start:.3f}s)")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()

    duration = end - start

    if reencode:
        cmd = [
            FFMPEG, "-y", "-hide_banner", "-loglevel", "warning",
            "-i", str(input_path),
            "-ss", _format_timecode(start),
            "-to", _format_timecode(end),
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
            "-movflags", "+faststart",
            str(output_path),
        ]
    else:
        cmd = [
            FFMPEG, "-y", "-hide_banner", "-loglevel", "warning",
            "-i", str(input_path),
            "-ss", _format_timecode(start),
            "-t", f"{duration:.3f}",
            "-c:v", "copy",
            "-c:a", "copy",
            "-avoid_negative_ts", "make_zero",
            "-movflags", "+faststart",
            str(output_path),
        ]

    print(f"\n>> {' '.join(cmd)}\n")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("STDERR:", r.stderr[-2000:])
        raise SystemExit(r.returncode)
    if r.stderr.strip():
        print(r.stderr)

    size_mb = output_path.stat().st_size / 1024 ** 2
    print(f"\n[OK] {output_path}  ({size_mb:.2f} MB)")

    r2 = subprocess.run(
        [FFMPEG, "-i", str(output_path), "-hide_banner"],
        capture_output=True, text=True,
    )
    for line in r2.stderr.splitlines():
        if "Duration" in line or "Stream #0" in line:
            print(" ", line.strip())


def main():
    parser = argparse.ArgumentParser(description="Cat (trim) video tu start den end")
    parser.add_argument("--input", "-i", required=True, help="Duong dan video goc")
    parser.add_argument("--output", "-o", default=None, help="Duong dan video output")
    parser.add_argument("--start", "-s", default="00:00:00", help="Timecode bat dau (mac dinh 00:00:00)")
    parser.add_argument("--end", "-e", default=None, help="Timecode ket thuc")
    parser.add_argument("--duration", "-d", type=float, default=None, help="Do dai can cat (giay)")
    parser.add_argument("--reencode", action="store_true", help="Re-encode thay vi copy (chinh xac hon)")
    args = parser.parse_args()

    input_path = Path(args.input)
    if args.output is None:
        stem = input_path.stem
        output_path = Path("output/video-edit") / f"{stem}_trimmed{input_path.suffix}"
    else:
        output_path = Path(args.output)

    trim_video(
        input_path=input_path,
        output_path=output_path,
        start=_parse_timecode(args.start),
        end=_parse_timecode(args.end) if args.end else None,
        duration=args.duration,
        reencode=args.reencode,
    )


if __name__ == "__main__":
    main()
