import tkinter as tk
from pathlib import Path
from tkinter import ttk

import cv2
from PIL import Image, ImageTk


class VideoPlayerWindow:
    INIT_W = 800
    INIT_H = 480
    TIMELINE_H = 60
    N_THUMBS = 20

    def __init__(self, parent, video_path, on_close=None):
        self._on_close_cb = on_close

        self.cap = cv2.VideoCapture(str(video_path))
        if not self.cap.isOpened():
            self.cap.release()
            if on_close:
                on_close()
            return

        self.window = tk.Toplevel(parent)
        self.window.title(f"Video Preview - {Path(video_path).name}")
        self.window.minsize(500, 350)

        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        if self.fps <= 0:
            self.fps = 30
        self.duration_sec = self.total_frames / self.fps

        self._vw = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self._vh = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if self._vw <= 0 or self._vh <= 0:
            self._vw, self._vh = 640, 360

        aspect = self._vw / self._vh
        init_w = min(self.INIT_W, self._vw)
        init_h = int(init_w / aspect)
        if init_h > self.INIT_H:
            init_h = self.INIT_H
            init_w = int(init_h * aspect)

        self._canvas_w = init_w
        self._canvas_h = init_h
        self._timeline_thumbs = []
        self._current_sec = 0.0
        self._dragging = False
        self._was_playing = False
        self._photo = None

        self.playing = False
        self._after_id = None
        self.speed = 1.0

        self._build_ui()
        self._generate_thumbnails()
        self._bind_events()
        self.show_frame(0)
        self._draw_timeline()
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)
        self.window.bind("<Configure>", self._on_resize)
        self.toggle_play()

    def _build_ui(self):
        self.canvas = tk.Canvas(
            self.window, width=self._canvas_w, height=self._canvas_h,
            bg="black", highlightthickness=1, highlightbackground="#888",
            cursor="hand2",
        )
        self.canvas.pack(padx=10, pady=(10, 2), fill="both", expand=True)

        self.timeline_canvas = tk.Canvas(
            self.window, height=self.TIMELINE_H, bg="#e0e0e0",
            highlightthickness=0, cursor="hand2",
        )
        self.timeline_canvas.pack(fill="x", padx=10, pady=(2, 5))

        ctrl = ttk.Frame(self.window)
        ctrl.pack(fill="x", padx=10, pady=(0, 10))

        self.play_btn = ttk.Button(
            ctrl, text="▶ Phát", command=self.toggle_play, width=12,
        )
        self.play_btn.pack(side="left")

        self.time_label = ttk.Label(ctrl, text="0:00.0 / 0:00.0", width=16)
        self.time_label.pack(side="left", padx=(8, 0))

        self.nudge_b = ttk.Button(
            ctrl, text="◀◀", width=4, command=lambda: self._nudge_sec(-0.5),
        )
        self.nudge_b.pack(side="left", padx=(6, 1))
        self.nudge_f = ttk.Button(
            ctrl, text="▶▶", width=4, command=lambda: self._nudge_sec(0.5),
        )
        self.nudge_f.pack(side="left", padx=(1, 0))

        ttk.Separator(ctrl, orient="vertical").pack(side="right", fill="y", padx=(6, 6))
        self.speed_var = tk.DoubleVar(value=1.0)
        speed_combo = ttk.Combobox(
            ctrl, textvariable=self.speed_var, width=5, state="readonly",
            values=[0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0],
        )
        speed_combo.pack(side="right")
        ttk.Label(ctrl, text="Tốc độ:").pack(side="right", padx=(0, 3))
        speed_combo.bind("<<ComboboxSelected>>", self._on_speed_change)
        ttk.Button(ctrl, text="⏹ Stop", command=self.stop).pack(side="right", padx=(0, 0))

        self._seek_overlay = self.canvas.create_text(
            0, 0, text="", fill="#fff", font=("", 11, "bold"),
            anchor="center", state="hidden", tags="overlay",
        )

    def _bind_events(self):
        self.canvas.tag_bind("overlay", "<Button-1>", lambda e: None)
        self.canvas.bind("<Button-1>", self._canvas_press)
        self.canvas.bind("<B1-Motion>", self._canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._canvas_release)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.timeline_canvas.bind("<Button-1>", self._timeline_press)
        self.timeline_canvas.bind("<B1-Motion>", self._timeline_drag)
        self.timeline_canvas.bind("<ButtonRelease-1>", self._timeline_release)
        self.window.bind("<Left>", lambda e: self._nudge_frame(-1))
        self.window.bind("<Right>", lambda e: self._nudge_frame(1))
        self.window.bind("<Up>", lambda e: self._nudge_sec(-1))
        self.window.bind("<Down>", lambda e: self._nudge_sec(1))
        self.window.bind("<space>", lambda e: self.toggle_play())
        self.window.bind("j", lambda e: self._nudge_sec(-1))
        self.window.bind("k", lambda e: self.toggle_play())
        self.window.bind("l", lambda e: self._nudge_sec(1))

    # ── Thumbnails ─────────────────────────────────────

    def _generate_thumbnails(self):
        if self.duration_sec <= 0:
            return
        self._timeline_thumbs.clear()
        for i in range(self.N_THUMBS):
            sec = (i / self.N_THUMBS) * self.duration_sec
            idx = int(sec * self.fps)
            idx = max(0, min(idx, self.total_frames - 1))
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                thumb = cv2.resize(frame, (60, 34), interpolation=cv2.INTER_AREA)
                self._timeline_thumbs.append(ImageTk.PhotoImage(Image.fromarray(thumb)))
            else:
                self._timeline_thumbs.append(None)

    def _draw_timeline(self):
        self.timeline_canvas.delete("all")
        cw = self.timeline_canvas.winfo_width()
        if cw < 10:
            cw = self.window.winfo_width() - 20 or 600
        self._tl_w = cw

        n = max(len(self._timeline_thumbs), 1)
        tw = cw / n
        for i, photo in enumerate(self._timeline_thumbs):
            if photo:
                x = int(i * tw) + int((tw - 60) / 2)
                y = (self.TIMELINE_H - 34) // 2
                self.timeline_canvas.create_image(x, y, anchor="nw", image=photo)

        self._draw_playhead()

    def _draw_playhead(self):
        self.timeline_canvas.delete("playhead")
        cw = max(self._tl_w, 10)
        frac = self._current_sec / self.duration_sec if self.duration_sec > 0 else 0
        x = int(frac * cw)
        self.timeline_canvas.create_line(
            x, 0, x, self.TIMELINE_H, fill="red", width=2, tags="playhead",
        )
        rh = 6
        self.timeline_canvas.create_oval(
            x - rh, self.TIMELINE_H - rh * 2,
            x + rh, self.TIMELINE_H,
            fill="red", outline="", tags="playhead",
        )

    # ── Frame display ─────────────────────────────────

    def show_frame(self, seconds):
        if self.cap is None:
            return
        seconds = max(0, min(seconds, self.duration_sec))
        self._current_sec = seconds
        idx = int(seconds * self.fps)
        idx = max(0, min(idx, self.total_frames - 1))
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = self.cap.read()
        if not ret:
            return
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w = frame.shape[:2]
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 10 or ch < 10:
            return
        scale = min(cw / w, ch / h)
        nw, nh = int(w * scale), int(h * scale)
        frame = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_LINEAR)
        self._photo = ImageTk.PhotoImage(Image.fromarray(frame))
        self.canvas.delete("frame")
        x = (cw - nw) // 2
        y = (ch - nh) // 2
        self.canvas.create_image(x, y, anchor="nw", image=self._photo, tags="frame")
        self.time_label.config(
            text=f"{self._fmt(seconds)} / {self._fmt(self.duration_sec)}"
        )
        self._draw_playhead()

    # ── Seek via canvas ───────────────────────────────

    def _x_to_sec(self, x, w):
        if w < 10:
            return 0
        return max(0, min(x / w, 1)) * self.duration_sec

    def _canvas_press(self, event):
        self._dragging = True
        self._was_playing = self.playing
        if self.playing:
            self.pause()
        self._do_seek(event.x, self.canvas.winfo_width())

    def _canvas_drag(self, event):
        if self._dragging:
            self._do_seek(event.x, self.canvas.winfo_width())

    def _canvas_release(self, event):
        self._dragging = False
        self.canvas.itemconfig("overlay", state="hidden")
        if self._was_playing:
            self.resume()

    def _do_seek(self, x, w):
        seconds = self._x_to_sec(x, w)
        self.show_frame(seconds)
        cw = self.canvas.winfo_width()
        self.canvas.coords("overlay", cw - 70, 20)
        self.canvas.itemconfig(
            "overlay", text=self._fmt(seconds), state="normal",
        )

    # ── Seek via timeline ─────────────────────────────

    def _timeline_press(self, event):
        self._dragging = True
        self._was_playing = self.playing
        if self.playing:
            self.pause()
        self._timeline_seek(event.x)

    def _timeline_drag(self, event):
        if self._dragging:
            self._timeline_seek(event.x)

    def _timeline_release(self, event):
        self._dragging = False
        if self._was_playing:
            self.resume()

    def _timeline_seek(self, x):
        self.show_frame(self._x_to_sec(x, self._tl_w))

    # ── Playback ──────────────────────────────────────

    def toggle_play(self):
        if self.playing:
            self.pause()
        else:
            self.resume()

    def pause(self):
        self.playing = False
        if self._after_id:
            self.canvas.after_cancel(self._after_id)
            self._after_id = None
        self.play_btn.config(text="▶ Phát")

    def resume(self):
        self.playing = True
        self.play_btn.config(text="⏸ Tạm dừng")
        self._play_loop()

    def stop(self):
        self.pause()
        self.show_frame(0)

    def _play_loop(self):
        if not self.playing or self.cap is None:
            return
        cur = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
        if cur >= self.total_frames:
            self.pause()
            self._current_sec = self.duration_sec
            self._draw_playhead()
            return
        self.show_frame(cur / self.fps)
        delay = max(16, int(round(33 / self.speed)))
        self._after_id = self.canvas.after(delay, self._play_loop)

    def _on_speed_change(self, event=None):
        self.speed = self.speed_var.get()
        if self.playing:
            self.pause()
            self.resume()

    # ── Nudge ─────────────────────────────────────────

    def _nudge_frame(self, direction):
        cur = int(self._current_sec * self.fps)
        new = max(0, min(cur + direction, self.total_frames - 1))
        self.show_frame(new / self.fps)

    def _nudge_sec(self, direction):
        self.show_frame(max(0, min(self._current_sec + direction, self.duration_sec)))

    def _on_mousewheel(self, event):
        self._nudge_frame(event.delta // 120)

    # ── Resize ────────────────────────────────────────

    def _on_resize(self, event):
        if event.widget != self.window or self.cap is None:
            return
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        if cw >= 10 and ch >= 10:
            self.show_frame(self._current_sec)
            self._draw_timeline()

    # ── Cleanup ───────────────────────────────────────

    def _on_close(self):
        self.pause()
        if self._after_id:
            self.canvas.after_cancel(self._after_id)
            self._after_id = None
        if self.cap:
            self.cap.release()
            self.cap = None
        self._timeline_thumbs.clear()
        if self._photo:
            del self._photo
            self._photo = None
        if self._on_close_cb:
            self._on_close_cb()
        self.window.destroy()

    @staticmethod
    def _fmt(sec):
        m, s = divmod(int(sec), 60)
        return f"{m}:{s:02d}.{int((sec - int(sec)) * 10)}"
