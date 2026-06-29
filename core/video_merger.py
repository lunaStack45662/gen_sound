import re
import subprocess
from pathlib import Path

import imageio_ffmpeg
from mutagen import File as MutagenFile


class VideoMerger:
    def __init__(self, root=None):
        self._ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    def get_video_info(self, video_path):
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Khong tim thay video: {video_path}")

        r = subprocess.run(
            [self._ffmpeg, "-i", str(video_path), "-hide_banner"],
            capture_output=True, text=True,
        )

        info = {"duration": 0.0, "has_audio": False, "width": 0, "height": 0}
        for line in r.stderr.splitlines():
            if "Duration:" in line:
                t = line.split("Duration:")[1].split(",")[0].strip()
                h, m, s = t.split(":")
                info["duration"] = int(h) * 3600 + int(m) * 60 + float(s)
            m = re.search(r"(\d+)x(\d+)", line)
            if m and "Video:" in line:
                info["width"] = int(m.group(1))
                info["height"] = int(m.group(2))
            if "Audio:" in line:
                info["has_audio"] = True
        return info

    def get_audio_duration(self, audio_path):
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Khong tim thay audio: {audio_path}")
        try:
            mf = MutagenFile(str(audio_path))
            if mf is not None and mf.info.length:
                return mf.info.length
        except Exception:
            pass
        try:
            r = subprocess.run(
                [self._ffmpeg, "-i", str(audio_path), "-hide_banner"],
                capture_output=True, text=True, timeout=15,
            )
            for line in r.stderr.splitlines():
                if "Duration:" in line:
                    t = line.split("Duration:")[1].split(",")[0].strip()
                    h, m, s = t.split(":")
                    return int(h) * 3600 + int(m) * 60 + float(s)
        except Exception:
            pass
        return 0.0

    # ── Chain merge (multi-segment) ──

    def probe_video(self, video_path):
        """Return (has_audio: bool, duration_sec: float)."""
        r = subprocess.run(
            [self._ffmpeg, "-i", str(video_path), "-hide_banner"],
            capture_output=True, text=True,
        )
        has_audio = "Audio:" in r.stderr
        dur = 0.0
        for line in r.stderr.splitlines():
            if "Duration:" in line:
                t = line.split("Duration:")[1].split(",")[0].strip()
                h, m, s = t.split(":")
                dur = int(h) * 3600 + int(m) * 60 + float(s)
        return has_audio, dur

    def build_filter(self, has_audio, start, end, delay_ms, insert_dur, vid_dur):
        """Build ffmpeg filter_complex string for one segment."""
        if has_audio:
            return (
                f"[0:a:0]volume=0:enable='between(t,{start},{end})'[muted];"
                f"[1:a:0]atrim=end={insert_dur}[trimmed];"
                f"[trimmed]adelay={delay_ms}:all=1[delayed];"
                f"[delayed]apad=whole_dur={vid_dur}[padded];"
                f"[muted][padded]amix=inputs=2:duration=first:weights=1 1,volume=2[outa]"
            )
        return (
            f"[1:a:0]atrim=end={insert_dur}[trimmed];"
            f"[trimmed]adelay={delay_ms}:all=1[delayed];"
            f"[delayed]apad=whole_dur={vid_dur}[outa]"
        )

    def chain_merge(self, video_path, segments, output_path, log_path=None,
                    work_dir=None):
        """
        Merge multiple audio segments into video sequentially.

        Args:
            video_path: str or Path to input video
            segments: list of dicts with keys start, end, path
            output_path: str or Path for final merged file
            log_path: optional Path for debug log
            work_dir: optional Path for temp files (default: output_path.parent)

        Returns:
            Path to merged output file

        Raises:
            FileNotFoundError, RuntimeError on failure
        """
        import shutil

        video_path = Path(video_path)
        output_path = Path(output_path)
        work_dir = Path(work_dir or output_path.parent)
        work_dir.mkdir(parents=True, exist_ok=True)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if log_path:
            log_path = Path(log_path)
            log_path.parent.mkdir(parents=True, exist_ok=True)

        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")
        if not segments:
            raise ValueError("No segments to merge")

        def _log(msg):
            if log_path:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(msg + "\n")

        segments = sorted(segments, key=lambda s: s["start"])
        current = str(video_path)

        for i, seg in enumerate(segments):
            part = str(work_dir / f"_part_{i}.mp4")
            delay_ms = int(seg["start"] * 1000)
            insert_dur = seg["end"] - seg["start"]

            has_audio, vid_dur = self.probe_video(current)
            if vid_dur <= 0:
                raise RuntimeError(f"Cannot probe duration from: {current}")

            fc = self.build_filter(has_audio, seg["start"], seg["end"],
                                   delay_ms, insert_dur, vid_dur)

            cmd = [
                self._ffmpeg, "-y", "-hide_banner", "-loglevel", "warning",
                "-i", current, "-i", seg["path"],
                "-filter_complex", fc,
                "-map", "0:v:0", "-map", "[outa]",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-t", str(vid_dur), part,
            ]

            _log(f"=== SEGMENT {i} ===")
            _log(f"start={seg['start']}, end={seg['end']}, insert_dur={insert_dur}")
            _log(f"delay_ms={delay_ms}, vid_dur={vid_dur}, has_audio={has_audio}")
            _log(f"fc={fc}")
            _log(f"cmd={' '.join(str(x) for x in cmd)}")

            result = subprocess.run(cmd, capture_output=True, text=True)
            _log(f"returncode={result.returncode}")
            _log(f"stderr={result.stderr[-500:]}\n")

            if result.returncode != 0:
                raise RuntimeError(
                    f"ffmpeg failed (segment {i}):\n{result.stderr[-300:]}"
                )

            current = part

        shutil.move(current, str(output_path))
        for p in Path(work_dir).glob("_part_*.mp4"):
            p.unlink(missing_ok=True)

        return output_path.resolve()
