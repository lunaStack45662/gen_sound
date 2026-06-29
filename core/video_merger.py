import re
import subprocess
import threading
from pathlib import Path

import imageio_ffmpeg


class VideoMerger:
    def __init__(self):
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

        r = subprocess.run(
            [self._ffmpeg, "-i", str(audio_path), "-hide_banner"],
            capture_output=True, text=True,
        )
        for line in r.stderr.splitlines():
            if "Duration:" in line:
                t = line.split("Duration:")[1].split(",")[0].strip()
                h, m, s = t.split(":")
                return int(h) * 3600 + int(m) * 60 + float(s)
        return 0.0

    def merge(self, video_path, audio_path, start_sec, end_sec, output_path,
              on_done=None, on_error=None):
        thread = threading.Thread(
            target=self._merge_worker,
            args=(video_path, audio_path, start_sec, end_sec, output_path,
                  on_done, on_error),
            daemon=True,
        )
        thread.start()
        return thread

    def _merge_worker(self, video_path, audio_path, start_sec, end_sec,
                      output_path, on_done, on_error):
        try:
            result = self._do_merge(
                video_path, audio_path, start_sec, end_sec, output_path
            )
            if on_done:
                on_done(str(result))
        except Exception as e:
            if on_error:
                on_error(str(e))

    def _do_merge(self, video_path, audio_path, start_sec, end_sec, output_path):
        video_path = Path(video_path)
        audio_path = Path(audio_path)

        if not video_path.exists():
            raise FileNotFoundError(f"Khong tim thay video: {video_path}")
        if not audio_path.exists():
            raise FileNotFoundError(f"Khong tim thay audio: {audio_path}")

        vinfo = self.get_video_info(video_path)
        audio_dur = self.get_audio_duration(audio_path)
        vid_dur = vinfo["duration"]

        if start_sec < 0:
            raise ValueError("start khong duoc am")
        if start_sec >= end_sec:
            raise ValueError("start phai nho hon end")
        if start_sec >= vid_dur:
            raise ValueError(f"start ({start_sec}s) vuot qua duration video ({vid_dur:.2f}s)")

        insert_dur = min(end_sec - start_sec, audio_dur)
        delay_ms = int(start_sec * 1000)

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.exists():
            output_path.unlink()

        if vinfo["has_audio"]:
            filter_complex = (
                f"[0:a:0]volume=0:enable='between(t,{start_sec},{start_sec + insert_dur})'[muted];"
                f"[1:a:0]adelay={delay_ms}:all=1[delayed];"
                f"[muted][delayed]amix=inputs=2:duration=first[outa]"
            )
            cmd = [
                self._ffmpeg, "-y", "-hide_banner", "-loglevel", "warning",
                "-i", str(video_path),
                "-i", str(audio_path),
                "-filter_complex", filter_complex,
                "-map", "0:v:0",
                "-map", "[outa]",
                "-c:v", "copy",
                "-c:a", "aac", "-b:a", "192k",
                "-shortest",
                str(output_path),
            ]
        else:
            filter_complex = (
                f"[1:a:0]adelay={delay_ms}:all=1[delayed];"
                f"[delayed]apad=whole_dur={vid_dur}[outa]"
            )
            cmd = [
                self._ffmpeg, "-y", "-hide_banner", "-loglevel", "warning",
                "-i", str(video_path),
                "-i", str(audio_path),
                "-filter_complex", filter_complex,
                "-map", "0:v:0",
                "-map", "[outa]",
                "-c:v", "copy",
                "-c:a", "aac", "-b:a", "192k",
                "-shortest",
                str(output_path),
            ]

        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(
                f"ffmpeg that bai (ma {r.returncode}):\n{r.stderr[-2000:]}"
            )

        return output_path
