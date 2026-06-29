import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import cv2
from PIL import Image, ImageTk

from gui.video_player import VideoPlayerWindow


class MergeAudioTab(ttk.Frame):
    def __init__(self, parent, merger, player):
        super().__init__(parent)
        self.merger = merger
        self.player = player
        self.video_path = tk.StringVar()
        self._cap = None
        self._build_ui()

    def _build_ui(self):
        frame = ttk.LabelFrame(self, text="Video", padding=10)
        frame.pack(fill="x", padx=10, pady=(10, 5))

        row1 = ttk.Frame(frame)
        row1.pack(fill="x")
        ttk.Button(row1, text="Chọn video...", command=self._select_video).pack(side="left")
        self.video_label = ttk.Label(row1, text="Chưa chọn", foreground="gray")
        self.video_label.pack(side="left", padx=(10, 0))

        cf = ttk.Frame(frame)
        cf.pack(fill="x", pady=(6, 0))
        self.video_canvas = tk.Canvas(
            cf, width=320, height=180, bg="black",
            highlightthickness=1, highlightbackground="#888",
        )
        self.video_canvas.pack(side="left")
        self.video_canvas.create_text(
            160, 90, text="Chưa có video", fill="#666", font=("", 10), tags="placeholder",
        )

        ctrl = ttk.Frame(cf)
        ctrl.pack(side="left", fill="y", padx=(10, 0))
        self.view_btn = ttk.Button(ctrl, text="▶ Xem video", command=self._open_player, width=12)
        self.view_btn.pack(pady=(0, 5))
        self.time_label = ttk.Label(ctrl, text="0.0s / 0.0s")
        self.time_label.pack()

        self.info_label = ttk.Label(self, text="", foreground="gray")
        self.info_label.pack(anchor="w", padx=10)

    def _select_video(self):
        path = filedialog.askopenfilename(
            title="Chọn video",
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv"), ("All files", "*.*")],
        )
        if not path:
            return
        self.video_path.set(path)
        self.video_label.config(text=Path(path).name, foreground="black")
        if self._cap:
            self._cap.release()
        self._cap = cv2.VideoCapture(str(path))
        if not self._cap.isOpened():
            return
        total_frames = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = self._cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30
        duration = total_frames / fps if fps > 0 else 0
        self._show_frame(0)
        w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.info_label.config(text=f"{duration:.1f}s  |  {w}x{h}")

    def _show_frame(self, frame_idx):
        if self._cap is None:
            return
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, int(frame_idx)))
        ret, frame = self._cap.read()
        if not ret:
            return
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w = frame.shape[:2]
        scale = min(320 / w, 180 / h)
        nw, nh = int(w * scale), int(h * scale)
        frame = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_AREA)
        self._photo = ImageTk.PhotoImage(Image.fromarray(frame))
        self.video_canvas.delete("all")
        x = (320 - nw) // 2
        y = (180 - nh) // 2
        self.video_canvas.create_image(x, y, anchor="nw", image=self._photo)
        total_frames = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = self._cap.get(cv2.CAP_PROP_FPS) or 30
        duration = total_frames / fps
        sec = frame_idx / fps
        self.time_label.config(text=f"{sec:.1f}s / {duration:.1f}s")

    def _open_player(self):
        path = self.video_path.get()
        if not path or not Path(path).exists():
            messagebox.showwarning("Cảnh báo", "Chưa chọn video!")
            return
        self.view_btn.config(state="disabled")

        def on_close():
            self.view_btn.config(state="normal")

        VideoPlayerWindow(
            self, path,
            merger=self.merger,
            on_close=on_close,
        )
