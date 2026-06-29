"""Video player popup window — orchestrates player, segments, timeline, merge."""
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from core.video_merger import VideoMerger
from .player import VideoPlayer
from .segments import SegmentManager
from .timeline import TimelineRenderer


class VideoPlayerWindow:
    INIT_W = 800
    INIT_H = 480

    def __init__(self, parent, video_path, merger=None, on_close=None):
        self._on_close_cb = on_close
        self._merger = merger or VideoMerger()

        # Init player
        self.player = VideoPlayer(video_path, None)
        if self.player.cap is None or not self.player.cap.isOpened():
            if self.player.cap:
                self.player.cap.release()
            if on_close:
                on_close()
            return

        self.video_file = video_path
        self.window = tk.Toplevel(parent)
        self.window.title(f"Video Preview - {Path(video_path).name}")
        self.window.minsize(500, 400)

        self._build_ui()

        self._init_player_canvas()
        self._init_segments()
        self._init_timeline()

        self._bind_events()
        self.player.seek(0)
        self.player.display_frame(self.player.get_frame_at(0))
        self._draw_all()
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)
        self.window.bind("<Configure>", self._on_resize)
        self.toggle_play()

    def _init_player_canvas(self):
        self.player.canvas = self.canvas

    def _init_segments(self):
        self.segments = SegmentManager(self.player.duration_sec, self._merger)

    def _init_timeline(self):
        self.timeline = TimelineRenderer(
            self.timeline_canvas, self.player.cap,
            self.player.total_frames, self.player.fps,
            self.player.duration_sec,
        )
        self.timeline.generate_thumbnails()

    # ── UI ──

    def _build_ui(self):
        self.canvas = tk.Canvas(
            self.window, bg="black", highlightthickness=1,
            highlightbackground="#888", cursor="hand2",
        )
        self.canvas.pack(padx=10, pady=(10, 2), fill="both", expand=True)

        self.timeline_canvas = tk.Canvas(
            self.window, height=75, bg="#e0e0e0",
            highlightthickness=0, cursor="hand2",
        )
        self.timeline_canvas.pack(fill="x", padx=10, pady=(2, 5))

        ctrl = ttk.Frame(self.window)
        ctrl.pack(fill="x", padx=10, pady=(0, 5))

        self.play_btn = ttk.Button(ctrl, text="▶ Phát",
                                   command=self.toggle_play, width=10)
        self.play_btn.pack(side="left")

        self.time_label = ttk.Label(ctrl, text="0:00.0 / 0:00.0", width=16)
        self.time_label.pack(side="left", padx=(8, 0))

        ttk.Separator(ctrl, orient="vertical").pack(
            side="right", fill="y", padx=(6, 6))
        self.speed_var = tk.DoubleVar(value=1.0)
        speed_combo = ttk.Combobox(
            ctrl, textvariable=self.speed_var, width=5, state="readonly",
            values=[0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0],
        )
        speed_combo.pack(side="right")
        ttk.Label(ctrl, text="Tốc độ:").pack(side="right", padx=(0, 3))
        speed_combo.bind("<<ComboboxSelected>>", self._on_speed_change)
        ttk.Button(ctrl, text="⏹ Stop", command=self.stop).pack(
            side="right", padx=(5, 0))
        ttk.Button(ctrl, text="Ghép ▶", command=self._do_merge).pack(
            side="right")

        bot = ttk.Frame(self.window)
        bot.pack(fill="x", padx=10, pady=(0, 10))
        self.add_btn = ttk.Button(bot, text="+ Thêm audio",
                                  command=self._add_audio)
        self.add_btn.pack(side="left")
        self.sel_label = ttk.Label(bot, text="")
        self.sel_label.pack(side="left", padx=(10, 0))
        self.del_btn = ttk.Button(bot, text="Xoá",
                                  command=self._delete_selected,
                                  state="disabled")
        self.del_btn.pack(side="left", padx=(5, 0))

        self._seek_overlay = self.canvas.create_text(
            0, 0, text="", fill="#fff", font=("", 11, "bold"),
            anchor="center", state="hidden", tags="overlay",
        )

    # ── Events ──

    def _bind_events(self):
        self.canvas.tag_bind("overlay", "<Button-1>", lambda e: None)
        self.canvas.bind("<Button-1>", self._canvas_press)
        self.canvas.bind("<B1-Motion>", self._canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._canvas_release)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.timeline_canvas.bind("<Button-1>", self._timeline_press)
        self.timeline_canvas.bind("<B1-Motion>", self._timeline_drag)
        self.timeline_canvas.bind("<ButtonRelease-1>", self._timeline_release)
        self.timeline_canvas.bind("<Double-1>", self._timeline_double)
        self.timeline_canvas.bind("<Button-3>", self._timeline_right)
        self.window.bind("<Left>", lambda e: self._nudge_frame(-1))
        self.window.bind("<Right>", lambda e: self._nudge_frame(1))
        self.window.bind("<Up>", lambda e: self._nudge_sec(-1))
        self.window.bind("<Down>", lambda e: self._nudge_sec(1))
        self.window.bind("<space>", lambda e: self.toggle_play())
        self.window.bind("j", lambda e: self._nudge_sec(-1))
        self.window.bind("k", lambda e: self.toggle_play())
        self.window.bind("l", lambda e: self._nudge_sec(1))
        self.window.bind("<Delete>", lambda e: self._delete_selected())

    # ── Drawing helpers ──

    def _draw_all(self):
        self.timeline.draw(
            self.segments.segments, self.player.current_sec,
            self.segments.selected_id, self.window.winfo_width(),
        )
        self._update_time_label()

    def _update_time_label(self):
        self.time_label.config(
            text=f"{self._fmt(self.player.current_sec)} / "
                 f"{self._fmt(self.player.duration_sec)}"
        )

    @staticmethod
    def _fmt(sec):
        m, s = divmod(int(sec), 60)
        return f"{m}:{s:02d}.{int((sec - int(sec)) * 10)}"

    # ── Playback ──

    def toggle_play(self):
        if self.player.playing:
            self.player.pause()
            self.play_btn.config(text="▶ Phát")
            self.segments.stop_all_preview()
        else:
            self.player.play(
                on_frame=self._on_play_frame,
                on_finish=self._on_play_finish,
            )
            self.play_btn.config(text="⏸ Tạm dừng")
            self.segments.reset_preview()

    def stop(self):
        self.player.pause()
        self.play_btn.config(text="▶ Phát")
        self.segments.stop_all_preview()
        self.player.seek(0)
        self.player.display_frame(self.player.get_frame_at(0))
        self.segments.reset_preview()
        self._draw_all()

    def _on_play_frame(self, seconds, frame):
        self.player.display_frame(frame)
        self._update_time_label()
        self.timeline.draw_playhead(self.player.current_sec)
        self.segments.update_preview(seconds)

    def _on_play_finish(self):
        self.play_btn.config(text="▶ Phát")
        self.timeline.draw_playhead(self.player.current_sec)
        self.segments.stop_all_preview()

    def _on_speed_change(self, event=None):
        self.player.speed = self.speed_var.get()
        if self.player.playing:
            self.player.pause()
            self.toggle_play()

    # ── Seek (canvas click/drag) ──

    def _canvas_press(self, event):
        self._dragging = True
        self._was_playing = self.player.playing
        if self.player.playing:
            self.player.pause()
            self.play_btn.config(text="▶ Phát")
            self.segments.stop_all_preview()
        self._do_seek(event.x, self.canvas.winfo_width())

    def _canvas_drag(self, event):
        if self._dragging:
            self._do_seek(event.x, self.canvas.winfo_width())

    def _canvas_release(self, event):
        self._dragging = False
        self.canvas.itemconfig("overlay", state="hidden")
        if self._was_playing:
            self.toggle_play()

    def _do_seek(self, x, w):
        seconds = self.timeline.x_to_sec(x)
        frame = self.player.seek(seconds)
        if frame is not None:
            self.player.display_frame(frame)
        self._update_time_label()
        self.timeline.draw_playhead(self.player.current_sec)
        cw = self.canvas.winfo_width()
        self.canvas.coords("overlay", cw - 70, 20)
        self.canvas.itemconfig("overlay",
                               text=self._fmt(seconds), state="normal")

    # ── Timeline interaction ──

    def _timeline_press(self, event):
        seg = self.segments.find_at(event.x, self.timeline.tl_w)
        if seg:
            self.segments.select(seg["id"])
            self._drag_seg = seg
            self._drag_off = event.x
            self._was_playing = self.player.playing
            if self.player.playing:
                self.player.pause()
                self.play_btn.config(text="▶ Phát")
                self.segments.stop_all_preview()
            self._update_sel_label()
            self._draw_all()
        else:
            self.segments.select(None)
            self._drag_seg = None
            self._update_sel_label()
            self._draw_all()
            self._dragging = True
            self._was_playing = self.player.playing
            if self.player.playing:
                self.player.pause()
                self.play_btn.config(text="▶ Phát")
                self.segments.stop_all_preview()
            self._timeline_seek(event.x)

    def _timeline_drag(self, event):
        if self._drag_seg:
            cw = max(self.timeline.tl_w, 10)
            delta = ((event.x - self._drag_off) / cw) * self.player.duration_sec
            new_s = self._drag_seg["start"] + delta
            if self.segments.move(self._drag_seg, new_s):
                self._drag_off = event.x
            self._draw_all()
        elif self._dragging:
            self._timeline_seek(event.x)

    def _timeline_release(self, event):
        self._drag_seg = None
        self._dragging = False
        if self._was_playing:
            self.toggle_play()

    def _timeline_seek(self, x):
        frame = self.player.seek(self.timeline.x_to_sec(x))
        if frame is not None:
            self.player.display_frame(frame)
        self._update_time_label()
        self.timeline.draw_playhead(self.player.current_sec)

    def _timeline_double(self, event):
        seg = self.segments.find_at(event.x, self.timeline.tl_w)
        if seg:
            self._edit_segment(seg)

    def _timeline_right(self, event):
        seg = self.segments.find_at(event.x, self.timeline.tl_w)
        if seg:
            self.segments.select(seg["id"])
            self._update_sel_label()
            self._draw_all()
            menu = tk.Menu(self.window, tearoff=0)
            menu.add_command(label="Sửa...",
                             command=lambda: self._edit_segment(seg))
            menu.add_command(label="Xoá",
                             command=lambda: self._remove_segment(seg["id"]))
            menu.tk_popup(event.x_root, event.y_root)

    # ── Segment editing ──

    def _add_audio(self):
        path = filedialog.askopenfilename(
            title="Chọn file âm thanh",
            filetypes=[("Audio files", "*.mp3 *.wav"), ("All files", "*.*")],
        )
        if not path:
            return
        seg = self.segments.add(path)
        if seg is None:
            messagebox.showerror("Lỗi", "Không đọc được duration audio!")
            return
        self._update_sel_label()
        self._draw_all()

    def _edit_segment(self, seg):
        dialog = tk.Toplevel(self.window)
        dialog.title("Sửa audio")
        dialog.geometry("280x140")
        dialog.transient(self.window)
        dialog.grab_set()
        ttk.Label(dialog, text="Từ giây:").pack(pady=(8, 0))
        sv = tk.StringVar(value=f"{seg['start']:.1f}")
        ttk.Entry(dialog, textvariable=sv).pack()
        ttk.Label(dialog, text="Đến giây:").pack(pady=(5, 0))
        ev = tk.StringVar(value=f"{seg['end']:.1f}")
        ttk.Entry(dialog, textvariable=ev).pack()

        def save():
            try:
                s, e = float(sv.get()), float(ev.get())
                if self.segments.edit(seg, s, e):
                    self.segments.reset_preview()
                    self._update_sel_label()
                    self._draw_all()
                    dialog.destroy()
                else:
                    raise ValueError
            except ValueError:
                messagebox.showwarning("Lỗi", "Giá trị không hợp lệ!")
        ttk.Button(dialog, text="Lưu", command=save).pack(pady=8)

    def _delete_selected(self):
        if self.segments.selected_id is not None:
            self._remove_segment(self.segments.selected_id)

    def _remove_segment(self, sid):
        self.segments.remove(sid)
        self._update_sel_label()
        self._draw_all()

    def _update_sel_label(self):
        seg = self.segments.get_by_id(self.segments.selected_id)
        if seg:
            self.sel_label.config(
                text=f"{seg['name']}  ({seg['start']:.1f}s → {seg['end']:.1f}s)"
            )
            self.del_btn.config(state="normal")
        else:
            self.sel_label.config(text="")
            self.del_btn.config(state="disabled")

    # ── Nudge ──

    def _nudge_frame(self, direction):
        cur = int(self.player.current_sec * self.player.fps)
        new = max(0, min(cur + direction, self.player.total_frames - 1))
        self.player.seek(new / self.player.fps)
        self.player.display_frame(self.player.get_frame_at(new / self.player.fps))
        self.segments.reset_preview()
        self._draw_all()

    def _nudge_sec(self, direction):
        new = max(0, min(self.player.current_sec + direction,
                         self.player.duration_sec))
        self.player.seek(new)
        self.player.display_frame(self.player.get_frame_at(new))
        self.segments.reset_preview()
        self._draw_all()

    def _on_mousewheel(self, event):
        self._nudge_frame(event.delta // 120)

    # ── Resize ──

    def _on_resize(self, event):
        if event.widget != self.window or self.player.cap is None:
            return
        self.player.display_frame(self.player.get_frame_at(
            self.player.current_sec))
        self._draw_all()

    # ── Merge ──

    def _do_merge(self):
        segs = self.segments.get_merge_tuples()
        if not segs:
            messagebox.showwarning("Cảnh báo", "Chưa có audio nào!")
            return

        output_dir = Path("output/video")
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / f"{Path(self.video_file).stem}_merged.mp4"
        log_path = output_dir / "_merge_debug.log"

        self.add_btn.config(state="disabled")
        self.play_btn.config(state="disabled")

        try:
            self._merger.chain_merge(
                video_path=self.video_file,
                segments=segs,
                output_path=str(out_path),
                log_path=str(log_path),
                work_dir=str(output_dir),
            )

            self.add_btn.config(state="normal")
            self.play_btn.config(state="normal")
            if messagebox.askyesno("Thành công",
                                   f"Đã tạo:\n{out_path}\n\nMở file?"):
                import os
                os.startfile(out_path)

        except Exception as e:
            self.add_btn.config(state="normal")
            self.play_btn.config(state="normal")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"EXCEPTION: {e}\n")
            messagebox.showerror("Lỗi", str(e))

    # ── Cleanup ──

    def _on_close(self):
        self.player.cleanup()
        self.segments.stop_all_preview()
        self.segments = None
        self.timeline.cleanup()
        if self._on_close_cb:
            self._on_close_cb()
        self.window.destroy()
