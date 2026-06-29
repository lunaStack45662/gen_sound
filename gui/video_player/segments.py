"""Audio segment data management + preview playback."""
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import pygame

from .timeline import COLORS


class SegmentManager:
    def __init__(self, duration_sec, merger=None):
        self.duration_sec = duration_sec
        self._merger = merger
        self._segments = []
        self._seg_id = 0
        self._selected_seg = None
        self._seg_sounds = {}
        self._seg_playing = set()
        self._seg_triggered = set()

        # UI callbacks (set by window after creating widgets)
        self.on_update_label = None
        self.on_draw_timeline = None

    @property
    def segments(self):
        return self._segments

    @property
    def selected_id(self):
        return self._selected_seg

    def get_by_id(self, sid):
        return next((s for s in self._segments if s["id"] == sid), None)

    def find_at(self, x, tl_w):
        """Find segment at pixel x on timeline. Returns seg or None."""
        if self.duration_sec <= 0:
            return None
        cw = max(tl_w, 10)
        sec = self._x_to_sec(x, cw)
        for seg in reversed(self._segments):
            if seg["start"] <= sec <= seg["end"]:
                return seg
        return None

    def _x_to_sec(self, x, w):
        if w < 10 or self.duration_sec <= 0:
            return 0
        return max(0, min(x / w, 1)) * self.duration_sec

    def add(self, path, speed=1.0):
        """Add audio segment. Returns seg dict or None on failure."""
        if self.duration_sec <= 0:
            return None
        dur = self._get_audio_duration(path)
        if dur <= 0:
            return None
        last_end = max((s["end"] for s in self._segments), default=0)
        self._seg_id += 1
        seg = {
            "id": self._seg_id,
            "path": path,
            "name": Path(path).name,
            "start": last_end,
            "end": min(last_end + dur, self.duration_sec),
            "color": COLORS[self._seg_id % len(COLORS)],
        }
        self._segments.append(seg)
        self._seg_sounds[seg["id"]] = self._load_sound(path)
        self._selected_seg = seg["id"]
        return seg

    def remove(self, sid):
        if sid in self._seg_sounds:
            try:
                self._seg_sounds[sid].stop()
            except Exception:
                pass
            del self._seg_sounds[sid]
        self._segments = [s for s in self._segments if s["id"] != sid]
        self._seg_playing.discard(sid)
        self._seg_triggered.discard(sid)
        if self._selected_seg == sid:
            self._selected_seg = None

    def select(self, sid):
        self._selected_seg = sid

    def _load_sound(self, path):
        try:
            return pygame.mixer.Sound(str(path))
        except Exception:
            return None

    def _get_audio_duration(self, path):
        if self._merger:
            try:
                return self._merger.get_audio_duration(path)
            except Exception:
                pass
        try:
            from mutagen import File as MutagenFile
            mf = MutagenFile(str(path))
            if mf is not None and mf.info.length:
                return mf.info.length
        except Exception:
            pass
        try:
            import subprocess, imageio_ffmpeg
            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
            r = subprocess.run(
                [ffmpeg, "-i", str(path), "-hide_banner"],
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

    def edit(self, seg, start, end):
        """Update segment times. Returns True if valid."""
        if start >= end or start < 0 or end > self.duration_sec:
            return False
        seg["start"] = start
        seg["end"] = end
        return True

    def move(self, seg, new_start):
        """Move segment to new start position (via drag)."""
        dur = seg["end"] - seg["start"]
        new_end = new_start + dur
        if new_start >= 0 and new_end <= self.duration_sec and new_start < new_end:
            seg["start"] = new_start
            seg["end"] = new_end
            return True
        return False

    def update_preview(self, seconds):
        """Called during playback to trigger/stop segment audio."""
        for seg in self._segments:
            sid = seg["id"]
            if sid in self._seg_triggered:
                continue
            if seg["start"] <= seconds < seg["end"]:
                sound = self._seg_sounds.get(sid)
                if sound:
                    try:
                        sound.play()
                    except Exception:
                        pass
                    self._seg_playing.add(sid)
                self._seg_triggered.add(sid)

        expired = []
        for sid in self._seg_playing:
            seg = self.get_by_id(sid)
            if seg and seconds >= seg["end"]:
                sound = self._seg_sounds.get(sid)
                if sound:
                    try:
                        sound.stop()
                    except Exception:
                        pass
                expired.append(sid)
        for sid in expired:
            self._seg_playing.discard(sid)

    def stop_all_preview(self):
        for sid in list(self._seg_playing):
            sound = self._seg_sounds.get(sid)
            if sound:
                try:
                    sound.stop()
                except Exception:
                    pass
        self._seg_playing.clear()

    def reset_preview(self):
        self.stop_all_preview()
        self._seg_triggered.clear()

    def get_merge_tuples(self):
        """Return sorted list of segment dicts for merging."""
        return sorted(self._segments, key=lambda s: s["start"])
