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
