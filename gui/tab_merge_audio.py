import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
import cv2
from PIL import Image, ImageTk

from gui.video_player import VideoPlayerWindow
from gui.icons import Icons
from gui.tooltip import add_tooltip


class MergeAudioTab(ctk.CTkFrame):
    def __init__(self, parent, merger, player):
        super().__init__(parent, fg_color="transparent")
        self.merger = merger
        self.player = player
        self.video_path = tk.StringVar()
        self._cap = None
        self._build_ui()

    def _build_ui(self):
        self._img_video = Icons.get("videocam", 24)
        self._img_play = Icons.get("play_arrow", 20)

        # ── Card: Video ──
        card = ctk.CTkFrame(self, fg_color="#1E2130", border_width=1,
                            border_color="#2A2D3E", corner_radius=8)
        card.pack(fill="x", padx=16, pady=(16, 4))
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=16)

        ctk.CTkLabel(inner, text="Video",
                     font=("Segoe UI", 14, "bold")).pack(anchor="w")

        row1 = ctk.CTkFrame(inner, fg_color="transparent")
        row1.pack(fill="x", pady=(8, 0))
        select_video_btn = ctk.CTkButton(row1, image=self._img_video, text="",
                                          command=self._select_video,
                                          width=32, height=32, corner_radius=6)
        select_video_btn.pack(side="left")
        add_tooltip(select_video_btn, "Chọn file video MP4/AVI/MOV")
        ctk.CTkLabel(row1, text="Chọn video...").pack(side="left",
                    padx=(4, 16))
        self.video_label = ctk.CTkLabel(row1, text="Chưa chọn",
                                         text_color="#8B8FA8")
        self.video_label.pack(side="left")

        cf = ctk.CTkFrame(inner, fg_color="transparent")
        cf.pack(fill="x", pady=(8, 0))
        self.video_canvas = tk.Canvas(
            cf, width=320, height=180, bg="black",
            highlightthickness=1, highlightbackground="#2A2D3E",
        )
        self.video_canvas.pack(side="left")
        self.video_canvas.create_text(
            160, 90, text="Chưa có video", fill="#4A4D61",
            font=("Segoe UI", 10), tags="placeholder",
        )

        ctrl = ctk.CTkFrame(cf, fg_color="transparent")
        ctrl.pack(side="left", fill="y", padx=(16, 0))
        self.view_btn = ctk.CTkButton(ctrl, image=self._img_play, text="",
                                       command=self._open_player,
                                       width=36, height=36, corner_radius=6)
        self.view_btn.pack(pady=(0, 4))
        add_tooltip(self.view_btn, "Mở video player để chỉnh sửa + ghép audio")
        ctk.CTkLabel(ctrl, text="Xem video").pack()
        self.time_label = ctk.CTkLabel(ctrl, text="0.0s / 0.0s")
        self.time_label.pack()

        self.info_label = ctk.CTkLabel(self, text="", text_color="#8B8FA8")
        self.info_label.pack(anchor="w", padx=16)

    def _select_video(self):
        path = filedialog.askopenfilename(
            title="Chọn video",
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv"), ("All files", "*.*")],
        )
        if not path:
            return
        self.video_path.set(path)
        self.video_label.configure(text=Path(path).name, text_color="#F1F1F3")
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
        self.info_label.configure(text=f"{duration:.1f}s  |  {w}x{h}")

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
        self.video_canvas.delete("frame_content")
        x = (320 - nw) // 2
        y = (180 - nh) // 2
        self.video_canvas.create_image(x, y, anchor="nw", image=self._photo,
                                        tags="frame_content")
        total_frames = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = self._cap.get(cv2.CAP_PROP_FPS) or 30
        duration = total_frames / fps
        sec = frame_idx / fps
        self.time_label.configure(text=f"{sec:.1f}s / {duration:.1f}s")

    def _open_player(self):
        path = self.video_path.get()
        if not path or not Path(path).exists():
            messagebox.showwarning("Cảnh báo", "Chưa chọn video!")
            return
        self.view_btn.configure(state="disabled")

        def on_close():
            self.view_btn.configure(state="normal")

        VideoPlayerWindow(
            self, path,
            merger=self.merger,
            on_close=on_close,
        )
