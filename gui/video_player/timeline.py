"""Timeline rendering: thumbnails, playhead, segment bars."""
from PIL import Image, ImageTk

import cv2

COLORS = ["#ff6b6b", "#4ecdc4", "#45b7d1", "#96ceb4", "#ffeaa7", "#dda0dd", "#98d8c8"]


class TimelineRenderer:
    TIMELINE_H = 75
    N_THUMBS = 20
    SEG_TRACK_Y0 = 35
    SEG_TRACK_Y1 = 72

    def __init__(self, canvas, cap, total_frames, fps, duration_sec):
        self.canvas = canvas
        self._cap = cap
        self.total_frames = total_frames
        self.fps = fps
        self.duration_sec = duration_sec

        self._tl_w = 600
        self._thumbs = []

    def generate_thumbnails(self):
        self._thumbs.clear()
        if self.duration_sec <= 0 or self._cap is None:
            return
        for i in range(self.N_THUMBS):
            sec = (i / self.N_THUMBS) * self.duration_sec
            idx = int(sec * self.fps)
            idx = max(0, min(idx, self.total_frames - 1))
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = self._cap.read()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                thumb = cv2.resize(frame, (60, 34), interpolation=cv2.INTER_AREA)
                self._thumbs.append(ImageTk.PhotoImage(Image.fromarray(thumb)))
            else:
                self._thumbs.append(None)

    def draw(self, segments, current_sec, selected_id=None, window_width=None):
        self.canvas.delete("all")
        cw = self.canvas.winfo_width()
        if cw < 10:
            cw = (window_width or 600) - 20
        self._tl_w = max(cw, 10)

        # Thumbnails track
        self.canvas.create_rectangle(0, 0, cw, 33, fill="#ccc", outline="")
        n = max(len(self._thumbs), 1)
        tw = cw / n
        for i, photo in enumerate(self._thumbs):
            if photo:
                x = int(i * tw) + int((tw - 60) / 2)
                self.canvas.create_image(x, 0, anchor="nw", image=photo)

        # Track background
        y0, y1 = self.SEG_TRACK_Y0, self.SEG_TRACK_Y1
        self.canvas.create_rectangle(0, y0, cw, y1, fill="#2a2a2a", outline="")
        self.canvas.create_text(
            6, (y0 + y1) // 2, text="♪", fill="#888", anchor="w", font=("", 10),
        )

        # Audio segments
        if self.duration_sec > 0:
            for seg in segments:
                sx = int((seg["start"] / self.duration_sec) * cw)
                ex = int((seg["end"] / self.duration_sec) * cw)
                if ex - sx < 6:
                    ex = sx + 6
                color = seg.get("color", "#ff6b6b")
                outline = "#fff" if seg.get("id") == selected_id else "#333"
                width = 2 if seg.get("id") == selected_id else 1
                self.canvas.create_rectangle(
                    sx, y0, ex, y1, fill=color, outline=outline, width=width,
                    tags=f"seg_{seg['id']}",
                )
                mx, my = (sx + ex) // 2, (y0 + y1) // 2
                self.canvas.create_text(
                    mx, my, text=seg["name"], fill="white", font=("", 8),
                    tags=f"seg_{seg['id']}",
                )

        self.draw_playhead(current_sec)

    def draw_playhead(self, current_sec):
        self.canvas.delete("playhead")
        cw = max(self._tl_w, 10)
        frac = current_sec / self.duration_sec if self.duration_sec > 0 else 0
        x = int(frac * cw)
        self.canvas.create_line(
            x, 0, x, self.TIMELINE_H, fill="red", width=2, tags="playhead",
        )

    def x_to_sec(self, x):
        cw = max(self._tl_w, 10)
        if cw < 10 or self.duration_sec <= 0:
            return 0
        return max(0, min(x / cw, 1)) * self.duration_sec

    @property
    def tl_w(self):
        return self._tl_w

    def cleanup(self):
        self._thumbs.clear()
