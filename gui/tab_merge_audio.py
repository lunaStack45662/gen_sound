import os
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import cv2
from PIL import Image, ImageTk

from core.audio_player import AudioPlayer
from core.video_merger import VideoMerger
from gui.video_player_window import VideoPlayerWindow


class MergeAudioTab(ttk.Frame):
    def __init__(self, parent, merger: VideoMerger, player: AudioPlayer):
        super().__init__(parent)
        self.merger = merger
        self.player = player
        self.video_path = tk.StringVar()
        self.audio_path = tk.StringVar()
        self._cap = None
        self._build_ui()

    def _build_ui(self):
        frame1 = ttk.LabelFrame(self, text="Video", padding=10)
        frame1.pack(fill="x", padx=10, pady=(10, 5))
        row1 = ttk.Frame(frame1)
        row1.pack(fill="x")
        ttk.Button(
            row1, text="Chọn video...", command=self._select_video
        ).pack(side="left")
        self.video_label = ttk.Label(row1, text="Chưa chọn", foreground="gray")
        self.video_label.pack(side="left", padx=(10, 0))

        canvas_frame = ttk.Frame(frame1)
        canvas_frame.pack(fill="x", pady=(8, 0))
        self.video_canvas = tk.Canvas(
            canvas_frame, width=320, height=180, bg="black",
            highlightthickness=1, highlightbackground="#888",
        )
        self.video_canvas.pack(side="left")
        self.video_canvas.create_text(
            160, 90, text="Chưa có video", fill="#666",
            font=("", 10), tags="placeholder",
        )

        ctrl_frame = ttk.Frame(canvas_frame)
        ctrl_frame.pack(side="left", fill="y", padx=(10, 0))
        self.view_btn = ttk.Button(
            ctrl_frame, text="▶ Xem video", command=self._open_player, width=12,
        )
        self.view_btn.pack(pady=(0, 5))
        self.time_label = ttk.Label(ctrl_frame, text="0.0s / 0.0s")
        self.time_label.pack()

        frame2 = ttk.LabelFrame(self, text="Âm thanh (.mp3 / .wav)", padding=10)
        frame2.pack(fill="x", padx=10)
        ttk.Button(
            frame2, text="Chọn audio...", command=self._select_audio
        ).pack(side="left")
        self.audio_label = ttk.Label(frame2, text="Chưa chọn", foreground="gray")
        self.audio_label.pack(side="left", padx=(10, 0))
        self.audio_preview_btn = ttk.Button(
            frame2, text="▶ Phát thử", command=self._preview_audio
        )
        self.audio_preview_btn.pack(side="left", padx=(10, 0))
        ttk.Button(
            frame2, text="⏹ Dừng", command=lambda: self.player.stop()
        ).pack(side="left")

        frame3 = ttk.LabelFrame(self, text="Thời gian ghép", padding=10)
        frame3.pack(fill="x", padx=10, pady=10)
        ttk.Label(frame3, text="Từ giây:").grid(row=0, column=0, sticky="w")
        self.start_var = tk.StringVar(value="0")
        ttk.Entry(frame3, textvariable=self.start_var, width=10).grid(
            row=0, column=1, padx=(5, 20)
        )
        ttk.Label(frame3, text="Đến giây:").grid(row=0, column=2, sticky="w")
        self.end_var = tk.StringVar(value="10")
        ttk.Entry(frame3, textvariable=self.end_var, width=10).grid(
            row=0, column=3, padx=(5, 0)
        )
        ttk.Button(
            frame3, text="Xem thông tin video", command=self._show_info
        ).grid(row=1, column=0, columnspan=4, pady=(10, 0))

        frame4 = ttk.Frame(self)
        frame4.pack(fill="x", padx=10, pady=10)
        self.merge_btn = ttk.Button(
            frame4, text="Ghép vào video", command=self._on_merge
        )
        self.merge_btn.pack(side="left")
        self.progress = ttk.Progressbar(frame4, mode="indeterminate", length=200)
        self.progress.pack(side="left", padx=(10, 0))

        self.output_label = ttk.Label(self, text="", foreground="blue")
        self.output_label.pack(anchor="w", padx=10)

    def _select_video(self):
        path = filedialog.askopenfilename(
            title="Chọn video",
            filetypes=[
                ("Video files", "*.mp4 *.avi *.mov *.mkv"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.video_path.set(path)
            self.video_label.config(text=Path(path).name, foreground="black")
            self._load_video(path)

    def _load_video(self, path):
        if self._cap:
            self._cap.release()
        self._cap = cv2.VideoCapture(str(path))
        if not self._cap.isOpened():
            self.video_canvas.delete("all")
            self.video_canvas.create_text(
                160, 90, text="Không thể mở video", fill="#f44",
                font=("", 10), tags="placeholder",
            )
            return
        self._total_frames = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self._fps = self._cap.get(cv2.CAP_PROP_FPS)
        if self._fps <= 0:
            self._fps = 30
        self._show_frame(0)

    def _show_frame(self, frame_idx):
        if self._cap is None:
            return
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = self._cap.read()
        if not ret:
            return
        self._display_frame(frame)
        sec = frame_idx / self._fps if self._fps > 0 else 0
        total = self._total_frames / self._fps if self._fps > 0 else 0
        self.time_label.config(text=f"{sec:.1f}s / {total:.1f}s")

    def _display_frame(self, frame):
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w = frame.shape[:2]
        scale = min(320 / w, 180 / h)
        nw, nh = int(w * scale), int(h * scale)
        frame = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_AREA)
        img = Image.fromarray(frame)
        self._photo = ImageTk.PhotoImage(img)
        self.video_canvas.delete("all")
        x = (320 - nw) // 2
        y = (180 - nh) // 2
        self.video_canvas.create_image(x, y, anchor="nw", image=self._photo)

    def _open_player(self):
        path = self.video_path.get()
        if not path or not Path(path).exists():
            messagebox.showwarning("Cảnh báo", "Chưa chọn video!")
            return
        VideoPlayerWindow(self, path)

    def _select_audio(self):
        path = filedialog.askopenfilename(
            title="Chọn file âm thanh",
            filetypes=[("Audio files", "*.mp3 *.wav"), ("All files", "*.*")],
        )
        if path:
            self.audio_path.set(path)
            self.audio_label.config(text=Path(path).name, foreground="black")

    def _preview_audio(self):
        path = self.audio_path.get()
        if not path or not Path(path).exists():
            messagebox.showwarning("Cảnh báo", "Chưa chọn file audio!")
            return
        self.player.stop()

        def on_finish():
            self.audio_preview_btn.config(text="▶ Phát thử")

        self.player.play(path, on_finish=on_finish)
        self.audio_preview_btn.config(text="⏸ Đang phát")

    def _show_info(self):
        path = self.video_path.get()
        if not path:
            messagebox.showwarning("Cảnh báo", "Chưa chọn video!")
            return
        try:
            info = self.merger.get_video_info(path)
            msg = (
                f"Tên: {Path(path).name}\n"
                f"Độ dài: {info['duration']:.2f}s\n"
                f"Kích thước: {info['width']}x{info['height']}\n"
                f"Có audio gốc: {'Có' if info['has_audio'] else 'Không'}"
            )
            messagebox.showinfo("Thông tin video", msg)
        except Exception as e:
            messagebox.showerror("Lỗi", str(e))

    def _on_merge(self):
        video = self.video_path.get()
        audio = self.audio_path.get()
        if not video or not Path(video).exists():
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn video hợp lệ!")
            return
        if not audio or not Path(audio).exists():
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn file audio hợp lệ!")
            return
        try:
            start = float(self.start_var.get())
            end = float(self.end_var.get())
        except ValueError:
            messagebox.showwarning("Cảnh báo", "Từ giây / Đến giây phải là số!")
            return

        output_dir = Path("output/video")
        output_dir.mkdir(parents=True, exist_ok=True)
        out_name = f"{Path(video).stem}_{Path(audio).stem}.mp4"
        output_path = output_dir / out_name

        self.merge_btn.config(state="disabled")
        self.progress.start()
        self.output_label.config(text="Đang xử lý...", foreground="blue")

        self.merger.merge(
            video_path=video,
            audio_path=audio,
            start_sec=start,
            end_sec=end,
            output_path=output_path,
            on_done=self._on_done,
            on_error=self._on_error,
        )

    def _on_done(self, path):
        self.merge_btn.config(state="normal")
        self.progress.stop()
        self.output_label.config(text=f"Đã tạo: {path}", foreground="green")
        if messagebox.askyesno("Thành công", f"Đã tạo:\n{path}\n\nMở file?"):
            os.startfile(path)

    def _on_error(self, error):
        self.merge_btn.config(state="normal")
        self.progress.stop()
        self.output_label.config(text="Thất bại", foreground="red")
        messagebox.showerror("Lỗi", f"Ghép thất bại:\n{error}")
