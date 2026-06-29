import tkinter as tk
from pathlib import Path
from tkinter import ttk

import cv2
from PIL import Image, ImageTk


class VideoPlayerWindow:
    INIT_W = 800
    INIT_H = 480

    def __init__(self, parent, video_path):
        self.window = tk.Toplevel(parent)
        self.window.title(f"Video Preview - {Path(video_path).name}")
        self.window.minsize(400, 300)

        self.cap = cv2.VideoCapture(str(video_path))
        if not self.cap.isOpened():
            self.window.destroy()
            return
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

        self.playing = False
        self._after_id = None
        self._seeking = False
        self.speed = 1.0

        self._build_ui()
        self.show_frame(0)
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)
        self.window.bind("<Configure>", self._on_resize)
        self.toggle_play()

    def _build_ui(self):
        self.canvas = tk.Canvas(
            self.window, width=self._canvas_w, height=self._canvas_h,
            bg="black", highlightthickness=0,
        )
        self.canvas.pack(padx=10, pady=(10, 5), fill="both", expand=True)

        ctrl = ttk.Frame(self.window)
        ctrl.pack(fill="x", padx=10, pady=(0, 10))

        self.play_btn = ttk.Button(
            ctrl, text="⏸ Tạm dừng", command=self.toggle_play, width=12,
        )
        self.play_btn.pack(side="left")

        self.time_label = ttk.Label(ctrl, text="0:00.0 / 0:00.0", width=16)
        self.time_label.pack(side="left", padx=(10, 0))

        self.scale = ttk.Scale(
            ctrl, from_=0.0, to=self.duration_sec,
            orient="horizontal", command=self._on_seek,
        )
        self.scale.pack(side="left", fill="x", expand=True, padx=(10, 0))

        ttk.Separator(ctrl, orient="vertical").pack(side="right", fill="y", padx=(5, 5))
        self.speed_var = tk.DoubleVar(value=1.0)
        speed_combo = ttk.Combobox(
            ctrl, textvariable=self.speed_var, width=5, state="readonly",
            values=[0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0],
        )
        speed_combo.pack(side="right")
        ttk.Label(ctrl, text="Tốc độ:").pack(side="right", padx=(0, 3))
        speed_combo.bind("<<ComboboxSelected>>", self._on_speed_change)
        ttk.Button(ctrl, text="⏹ Dừng", command=self.stop).pack(side="right", padx=(10, 0))

        self._placeholder = self.canvas.create_text(
            self._canvas_w // 2, self._canvas_h // 2,
            text="Loading...", fill="#666", font=("", 12),
        )

    def show_frame(self, seconds):
        if self.cap is None:
            return
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
        frame = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_AREA)
        img = Image.fromarray(frame)
        self._photo = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        x = (cw - nw) // 2
        y = (ch - nh) // 2
        self.canvas.create_image(x, y, anchor="nw", image=self._photo)
        self.time_label.config(
            text=f"{self._fmt(seconds)} / {self._fmt(self.duration_sec)}"
        )

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
        self.scale.set(0.0)

    def _on_speed_change(self, event=None):
        self.speed = self.speed_var.get()
        if self.playing:
            self.pause()
            self.resume()

    def _play_loop(self):
        if not self.playing or self.cap is None:
            return
        cur = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
        if cur >= self.total_frames:
            self.pause()
            return
        seconds = cur / self.fps
        self.show_frame(seconds)
        if not self._seeking:
            self.scale.set(seconds)
        delay = max(16, int(round(33 / self.speed)))
        self._after_id = self.canvas.after(delay, self._play_loop)

    def _on_seek(self, value):
        if self._seeking:
            return
        self._seeking = True
        seconds = float(value)
        self.show_frame(seconds)
        self._seeking = False

    def _on_resize(self, event):
        if event.widget != self.window:
            return
        if self.cap is None:
            return
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 10 or ch < 10:
            return
        cur_sec = self.cap.get(cv2.CAP_PROP_POS_FRAMES) / self.fps
        self._show_frame_on_canvas(cur_sec, cw, ch)

    def _show_frame_on_canvas(self, seconds, cw, ch):
        idx = int(seconds * self.fps)
        idx = max(0, min(idx, self.total_frames - 1))
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = self.cap.read()
        if not ret:
            return
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w = frame.shape[:2]
        scale = min(cw / w, ch / h)
        nw, nh = int(w * scale), int(h * scale)
        frame = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_AREA)
        img = Image.fromarray(frame)
        self._photo = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        x = (cw - nw) // 2
        y = (ch - nh) // 2
        self.canvas.create_image(x, y, anchor="nw", image=self._photo)

    def _on_close(self):
        self.pause()
        if self.cap:
            self.cap.release()
        self.window.destroy()

    @staticmethod
    def _fmt(sec):
        m, s = divmod(int(sec), 60)
        ds = int((sec - int(sec)) * 10)
        return f"{m}:{s:02d}.{ds}"
