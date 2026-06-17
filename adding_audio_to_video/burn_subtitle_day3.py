"""
Burn subtitle (Netflix top) + replace audio = voiceover day-3.

Input:
  - input/day-3/grok-65c245ab-4298-4bde-88b7-019ab623f225.mp4  (720x1264, 17s, 24fps, has audio)
  - output/day-3/voiceover_17s.wav
  - output/day-3/subtitles-17s.srt

Output:
  - output/day-3/grok-day3-with-subtitle.mp4
    + audio REPLACED bằng voiceover
    + subtitle burned ở TOP (~13% từ trên), 1 dòng, override
    + white text + black border (3px), no background box
    + font Segoe UI Bold ~38px cho width 720
    + AAC 192k / 44.1kHz / stereo (R10)
    + -movflags +faststart

Phong cách Netflix top:
  - Vị trí: top-center, ~180-200px từ top (~15% từ trên trên 1264 cao)
  - Mỗi cue: 1 dòng, dòng mới thay thế dòng cũ (override)
  - White text + black border 3px
  - Không có background box
  - Text align: center

ASS file dùng cho ffmpeg subtitles filter:
  - PlayResX=720, PlayResY=1264
  - Style: Segoe UI, 38px, white, black outline 3, Alignment=7 (top-center)
  - MarginV=180 (cách top 180px)
"""
import os
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

import re
import subprocess
from pathlib import Path

import imageio_ffmpeg

DAY = 3
VIDEO_IN  = Path(f"input/day-{DAY}/grok-65c245ab-4298-4bde-88b7-019ab623f225.mp4")
WAV_IN    = Path(f"output/day-{DAY}/voiceover_17s.wav")
SRT_IN    = Path(f"output/day-{DAY}/subtitles-17s.srt")
OUT_DIR   = Path(f"output/day-{DAY}")
ASS_FILE  = OUT_DIR / "subtitles-netflix.ass"
VIDEO_OUT = OUT_DIR / "grok-day3-with-subtitle.mp4"

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

VIDEO_W = 720
VIDEO_H = 1264
FONT    = "Segoe UI"
FONT_SIZE = 38
MARGIN_V  = 180    # ~14% từ top
OUTLINE_PX = 3     # black border


# ---------- 1. Parse SRT ----------
def parse_srt(p: Path) -> list[tuple[float, float, str]]:
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


def fmt_ass_time(t: float) -> str:
    """ASS format: H:MM:SS.cc (centiseconds, 2 chữ số)."""
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    cs = int(round((t - int(t)) * 100))
    if cs == 100:
        s += 1; cs = 0
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


def escape_ass_text(s: str) -> str:
    """Escape ký tự đặc biệt ASS: \\ { }"""
    return s.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def write_ass(entries: list[tuple[float, float, str]], path: Path):
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {VIDEO_W}
PlayResY: {VIDEO_H}
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{FONT},{FONT_SIZE},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,{OUTLINE_PX},0,7,20,20,{MARGIN_V},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    body = ""
    for s, e, text in entries:
        body += f"Dialogue: 0,{fmt_ass_time(s)},{fmt_ass_time(e)},Default,,0,0,0,,{escape_ass_text(text)}\n"
    path.write_text(header + body, encoding="utf-8")


def video_duration(path: Path) -> float:
    r = subprocess.run([FFMPEG, "-i", str(path), "-hide_banner"],
                       capture_output=True, text=True)
    for line in r.stderr.splitlines():
        if "Duration:" in line:
            t = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = t.split(":")
            return int(h)*3600 + int(m)*60 + float(s)
    raise RuntimeError("Không parse được video duration")


def main():
    print(f"[1/4] Parse SRT: {SRT_IN}")
    entries = parse_srt(SRT_IN)
    assert entries, "SRT rỗng"
    for i, (s, e, t) in enumerate(entries, 1):
        print(f"   #{i}  {s:.2f}s -> {e:.2f}s  | {t[:60]}{'...' if len(t)>60 else ''}")

    print(f"\n[2/4] Ghi ASS file: {ASS_FILE}")
    write_ass(entries, ASS_FILE)
    print(f"   ✓ ASS saved (PlayRes={VIDEO_W}x{VIDEO_H}, font={FONT} {FONT_SIZE}px, "
          f"top={MARGIN_V}px, outline={OUTLINE_PX}px)")

    # Verify font
    print(f"\n[3/4] Verify font: {FONT}")
    import os as _os
    font_path = Path("C:/Windows/Fonts") / f"{FONT}.ttf"
    if not font_path.exists():
        font_path = Path("C:/Windows/Fonts") / f"{FONT.lower()}.ttf"
    if font_path.exists():
        print(f"   ✓ Font found: {font_path}")
    else:
        print(f"   ⚠️ Font not found at {font_path}, ASS sẽ fallback font hệ thống")

    print(f"\n[4/4] ffmpeg: burn sub + replace audio")
    v_dur = video_duration(VIDEO_IN)
    print(f"   Video: {VIDEO_IN.name}  dur={v_dur:.3f}s")
    print(f"   Audio: {WAV_IN.name}")
    print(f"   ASS:   {ASS_FILE.name}")

    # Lưu ý: PHẢI re-encode video vì burn sub (R8 chỉ apply khi chỉ mux audio)
    # Encode: libx264 CRF 18 (chất lượng cao, gần lossless) + AAC 192k stereo
    cmd = [
        FFMPEG, "-y", "-hide_banner", "-loglevel", "warning",
        "-i", str(VIDEO_IN),
        "-i", str(WAV_IN),
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-vf", f"ass={ASS_FILE.as_posix()}",
        "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",  # R10
        "-af", f"apad=pad_dur={v_dur:.3f},atrim=0:{v_dur:.3f},asetpts=PTS-STARTPTS",
        "-shortest",
        "-movflags", "+faststart",
        str(VIDEO_OUT),
    ]
    print(f"\n>> {subprocess.list2cmdline(cmd)[:200]}...")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("STDERR:", r.stderr[-2000:])
        raise SystemExit(r.returncode)
    if r.stderr.strip():
        print(r.stderr)

    size_mb = VIDEO_OUT.stat().st_size / 1024**2
    print(f"\n[OK] {VIDEO_OUT}  ({size_mb:.2f} MB)")

    # Verify output
    print("\n--- Verify output ---")
    r2 = subprocess.run([FFMPEG, "-i", str(VIDEO_OUT), "-hide_banner"],
                        capture_output=True, text=True)
    for line in r2.stderr.splitlines():
        if "Duration" in line or "Stream #0" in line:
            print(" ", line.strip())


if __name__ == "__main__":
    main()
