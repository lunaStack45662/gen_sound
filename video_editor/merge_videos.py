"""
Ghep nhieu video file (cung codec/resolution/fps) thanh 1 video duy nhat.
Mac dinh dung concat demuxer → khong re-encode, giu nguyen chat luong.

Cach dung:
    python video_editor/merge_videos.py --input clip1.mp4 clip2.mp4 clip3.mp4 ^
        --output output/video-edit/merged.mp4

    # Dung file list:
    python video_editor/merge_videos.py --list files.txt --output merged.mp4

    # Re-encode neu can dong nhat codec:
    python video_editor/merge_videos.py --input clip1.mp4 clip2.mp4 --reencode
"""

import argparse
import subprocess
import tempfile
from pathlib import Path

import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def _get_stream_info(path: Path) -> dict:
    r = subprocess.run(
        [FFMPEG, "-i", str(path), "-hide_banner"],
        capture_output=True, text=True,
    )
    info = {
        "duration": 0.0,
        "video_codec": "unknown",
        "width": 0,
        "height": 0,
        "fps": 0,
        "audio_codec": "unknown",
        "audio_sr": 0,
        "audio_ch": 0,
    }
    import re
    for line in r.stderr.splitlines():
        if "Duration:" in line:
            t = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = t.split(":")
            info["duration"] = int(h) * 3600 + int(m) * 60 + float(s)
        if "Stream #0:0" in line and "Video:" in line:
            vs = line.split("Video:")[1]
            info["video_codec"] = vs.split(",")[0].strip()
            res_match = re.search(r",\s*(\d+)x(\d+)", line)
            if res_match:
                info["width"] = int(res_match.group(1))
                info["height"] = int(res_match.group(2))
            fps_match = re.search(r"(\d+(?:\.\d+)?)\s*fps", line)
            if fps_match:
                info["fps"] = float(fps_match.group(1))
        if "Stream #0:1" in line and "Audio:" in line:
            audio_part = line.split("Audio:")[1]
            info["audio_codec"] = audio_part.split(",")[0].strip()
            sr_match = re.search(r"(\d+)\s*Hz", line)
            if sr_match:
                info["audio_sr"] = int(sr_match.group(1))
            ch_match = re.search(r"(\d+)\s*ch(annel)?s?", line)
            if ch_match:
                info["audio_ch"] = int(ch_match.group(1))
            elif "stereo" in line:
                info["audio_ch"] = 2
            elif "mono" in line:
                info["audio_ch"] = 1
    return info


def _check_compatibility(files: list[Path]) -> list[str]:
    warnings = []
    ref = None
    for f in files:
        info = _get_stream_info(f)
        if ref is None:
            ref = info
            continue
        if info.get("video_codec") and ref.get("video_codec") and info["video_codec"] != ref["video_codec"]:
            warnings.append(f"  ⚠ Codec khac: {f.name} ({info['video_codec']}) != {ref['video_codec']}")
        if info.get("width") and ref.get("width") and (info["width"] != ref["width"] or info["height"] != ref["height"]):
            warnings.append(f"  ⚠ Resolution khac: {f.name} ({info['width']}x{info['height']}) != ({ref['width']}x{ref['height']})")
        if info.get("fps") and ref.get("fps") and abs(info["fps"] - ref["fps"]) > 0.1:
            warnings.append(f"  ⚠ FPS khac: {f.name} ({info['fps']}) != {ref['fps']}")
    return warnings


def merge_videos(
    input_paths: list[Path],
    output_path: Path,
    reencode: bool = False,
):
    if not input_paths:
        raise ValueError("Khong co file video nao de ghep")
    for p in input_paths:
        if not p.exists():
            raise FileNotFoundError(f"Khong tim thay: {p}")

    print(f"Ghep {len(input_paths)} video:")
    for p in input_paths:
        sz = p.stat().st_size / 1024 ** 2
        print(f"  [{sz:.1f} MB] {p.name}")

    warnings = _check_compatibility(input_paths)
    if warnings:
        print("\nKiem tra tuong thich:")
        for w in warnings:
            print(w)
        print()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()

    if reencode:
        _merge_concat_filter(input_paths, output_path)
    else:
        _merge_concat_demuxer(input_paths, output_path)

    size_mb = output_path.stat().st_size / 1024 ** 2
    print(f"\n[OK] {output_path}  ({size_mb:.2f} MB)")

    r2 = subprocess.run(
        [FFMPEG, "-i", str(output_path), "-hide_banner"],
        capture_output=True, text=True,
    )
    for line in r2.stderr.splitlines():
        if "Duration" in line or "Stream #0" in line:
            print(" ", line.strip())


def _merge_concat_demuxer(input_paths: list[Path], output_path: Path):
    """Ghep bang concat demuxer — khong re-encode, yeu cau cung codec."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        file_list = Path(f.name)
        for p in input_paths:
            abs_p = p.resolve()
            f.write(f"file '{abs_p}'\n")

    try:
        cmd = [
            FFMPEG, "-y", "-hide_banner", "-loglevel", "warning",
            "-f", "concat", "-safe", "0",
            "-i", str(file_list),
            "-c", "copy",
            "-movflags", "+faststart",
            str(output_path),
        ]
        print(f">> {' '.join(cmd)}")
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print("STDERR:", r.stderr[-2000:])
            raise SystemExit(r.returncode)
        if r.stderr.strip():
            print(r.stderr)
    finally:
        file_list.unlink(missing_ok=True)


def _merge_concat_filter(input_paths: list[Path], output_path: Path):
    """Ghep bang filter_complex concat — scale/fps dong nhat truoc khi ghep."""
    infos = [_get_stream_info(p) for p in input_paths]

    max_w = max(i["width"] for i in infos if i["width"] > 0)
    max_h = max(i["height"] for i in infos if i["height"] > 0)
    max_fps = max(i["fps"] for i in infos if i["fps"] > 0)
    max_sr = max(i["audio_sr"] for i in infos if i["audio_sr"] > 0)
    if max_sr == 0:
        max_sr = 44100

    print(f"  Scale: {max_w}x{max_h}, FPS: {max_fps}, Audio: {max_sr}Hz\n")

    inputs = []
    for p in input_paths:
        inputs.extend(["-i", str(p)])

    n = len(input_paths)
    filter_parts = []
    for i in range(n):
        filter_parts.append(f"[{i}:v:0]scale={max_w}:{max_h}:force_original_aspect_ratio=decrease,pad={max_w}:{max_h}:(ow-iw)/2:(oh-ih)/2,fps={max_fps}[v{i}];")
        filter_parts.append(f"[{i}:a:0]aresample={max_sr},aformat=sample_rates={max_sr}:channel_layouts=stereo[a{i}];")

    concat_input = "".join(f"[v{i}][a{i}]" for i in range(n))
    filter_parts.append(f"{concat_input}concat=n={n}:v=1:a=1[outv][outa]")

    filter_str = " ".join(filter_parts)

    cmd = [
        FFMPEG, "-y", "-hide_banner", "-loglevel", "warning",
        *inputs,
        "-filter_complex", filter_str,
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k", "-ar", str(max_sr), "-ac", "2",
        "-movflags", "+faststart",
        str(output_path),
    ]
    print(f">> {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("STDERR:", r.stderr[-2000:])
        raise SystemExit(r.returncode)
    if r.stderr.strip():
        print(r.stderr)


def main():
    parser = argparse.ArgumentParser(description="Ghep nhieu video thanh 1 file")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--input", "-i", nargs="+", help="Danh sach video input")
    group.add_argument("--list", "-l", help="File text chua danh sach video (1 dong/file)")
    parser.add_argument("--output", "-o", required=True, help="Duong dan video output")
    parser.add_argument("--reencode", action="store_true", help="Re-encode de dong nhat codec")
    args = parser.parse_args()

    if args.list:
        list_path = Path(args.list)
        if not list_path.exists():
            raise FileNotFoundError(list_path)
        input_paths = [
            Path(line.strip())
            for line in list_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
    else:
        input_paths = [Path(p) for p in args.input]

    merge_videos(
        input_paths=input_paths,
        output_path=Path(args.output),
        reencode=args.reencode,
    )


if __name__ == "__main__":
    main()
