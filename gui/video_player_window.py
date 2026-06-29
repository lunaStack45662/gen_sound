import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import cv2
import pygame
from PIL import Image, ImageTk

COLORS = ["#ff6b6b", "#4ecdc4", "#45b7d1", "#96ceb4", "#ffeaa7", "#dda0dd", "#98d8c8"]


class VideoPlayerWindow:
    INIT_W = 800
    INIT_H = 480
    TIMELINE_H = 75
    N_THUMBS = 20
    SEG_TRACK_Y0 = 35
    SEG_TRACK_Y1 = 72

    def __init__(self, parent, video_path, merger=None, on_close=None):
        self._on_close_cb = on_close
        self._merger = merger

        self.cap = cv2.VideoCapture(str(video_path))
        if not self.cap.isOpened():
            self.cap.release()
            if on_close:
                on_close()
            return

        self.video_file = video_path
        self.window = tk.Toplevel(parent)
        self.window.title(f"Video Preview - {Path(video_path).name}")
        self.window.minsize(500, 400)

        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
        self.duration_sec = self.total_frames / self.fps if self.fps > 0 else 0

        self._vw = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
        self._vh = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 360
        aspect = self._vw / self._vh
        init_w = min(self.INIT_W, self._vw)
        init_h = int(init_w / aspect)
        if init_h > self.INIT_H:
            init_h = self.INIT_H
            init_w = int(init_h * aspect)

        self._canvas_w = init_w
        self._canvas_h = init_h
        self._timeline_thumbs = []
        self._tl_w = 600
        self._current_sec = 0.0
        self._dragging = False
        self._was_playing = False
        self._photo = None

        self.playing = False
        self._after_id = None
        self.speed = 1.0

        # Audio segments
        self._segments = []
        self._seg_id = 0
        self._selected_seg = None
        self._seg_sounds = {}
        self._seg_playing = set()
        self._seg_triggered = set()
        self._drag_seg = None
        self._drag_off = 0

        self._init_pygame()
        self._build_ui()
        self._generate_thumbnails()
        self._bind_events()
        self.show_frame(0)
        self._draw_timeline()
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)
        self.window.bind("<Configure>", self._on_resize)
        self.toggle_play()

    def _init_pygame(self):
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init(frequency=48000, size=-16, channels=2)
            except Exception:
                pass

    # ── UI ──

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
        ctrl.pack(fill="x", padx=10, pady=(0, 5))

        self.play_btn = ttk.Button(ctrl, text="▶ Phát", command=self.toggle_play, width=10)
        self.play_btn.pack(side="left")

        self.time_label = ttk.Label(ctrl, text="0:00.0 / 0:00.0", width=16)
        self.time_label.pack(side="left", padx=(8, 0))

        ttk.Separator(ctrl, orient="vertical").pack(side="right", fill="y", padx=(6, 6))
        self.speed_var = tk.DoubleVar(value=1.0)
        speed_combo = ttk.Combobox(
            ctrl, textvariable=self.speed_var, width=5, state="readonly",
            values=[0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0],
        )
        speed_combo.pack(side="right")
        ttk.Label(ctrl, text="Tốc độ:").pack(side="right", padx=(0, 3))
        speed_combo.bind("<<ComboboxSelected>>", self._on_speed_change)
        ttk.Button(ctrl, text="⏹ Stop", command=self.stop).pack(side="right", padx=(5, 0))
        ttk.Button(ctrl, text="Ghép ▶", command=self._do_merge).pack(side="right")

        # Bottom bar: add audio button + segment info
        bot = ttk.Frame(self.window)
        bot.pack(fill="x", padx=10, pady=(0, 10))
        self.add_btn = ttk.Button(bot, text="+ Thêm audio", command=self._add_audio)
        self.add_btn.pack(side="left")
        self.sel_label = ttk.Label(bot, text="")
        self.sel_label.pack(side="left", padx=(10, 0))
        self.del_btn = ttk.Button(bot, text="Xoá", command=self._delete_selected, state="disabled")
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

    # ── Thumbnails ──

    def _generate_thumbnails(self):
        self._timeline_thumbs.clear()
        if self.duration_sec <= 0:
            return
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

    # ── Timeline drawing ──

    def _draw_timeline(self):
        self.timeline_canvas.delete("all")
        cw = self.timeline_canvas.winfo_width()
        if cw < 10:
            cw = self.window.winfo_width() - 20 or 600
        self._tl_w = cw

        # Thumbnails (top)
        self.timeline_canvas.create_rectangle(0, 0, cw, 33, fill="#ccc", outline="")
        n = max(len(self._timeline_thumbs), 1)
        tw = cw / n
        for i, photo in enumerate(self._timeline_thumbs):
            if photo:
                x = int(i * tw) + int((tw - 60) / 2)
                self.timeline_canvas.create_image(x, 0, anchor="nw", image=photo)

        # Track background
        y0, y1 = self.SEG_TRACK_Y0, self.SEG_TRACK_Y1
        self.timeline_canvas.create_rectangle(0, y0, cw, y1, fill="#2a2a2a", outline="")
        self.timeline_canvas.create_text(
            6, (y0 + y1) // 2, text="♪", fill="#888", anchor="w", font=("", 10),
        )

        # Audio segments
        if self.duration_sec > 0:
            for seg in self._segments:
                sx = int((seg["start"] / self.duration_sec) * cw)
                ex = int((seg["end"] / self.duration_sec) * cw)
                if ex - sx < 6:
                    ex = sx + 6
                color = seg.get("color", "#ff6b6b")
                outline = "#fff" if seg.get("id") == self._selected_seg else "#333"
                width = 2 if seg.get("id") == self._selected_seg else 1
                self.timeline_canvas.create_rectangle(
                    sx, y0, ex, y1, fill=color, outline=outline, width=width,
                    tags=f"seg_{seg['id']}",
                )
                mx, my = (sx + ex) // 2, (y0 + y1) // 2
                self.timeline_canvas.create_text(
                    mx, my, text=seg["name"], fill="white", font=("", 8),
                    tags=f"seg_{seg['id']}",
                )

        self._draw_playhead()

    def _draw_playhead(self):
        self.timeline_canvas.delete("playhead")
        cw = max(self._tl_w, 10)
        frac = self._current_sec / self.duration_sec if self.duration_sec > 0 else 0
        x = int(frac * cw)
        self.timeline_canvas.create_line(
            x, 0, x, self.TIMELINE_H, fill="red", width=2, tags="playhead",
        )

    # ── Frame ──

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
        self._display_frame(frame)
        self.time_label.config(
            text=f"{self._fmt(seconds)} / {self._fmt(self.duration_sec)}"
        )
        self._draw_playhead()

    def _display_frame(self, frame):
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

    # ── Seek ──

    def _x_to_sec(self, x, w):
        if w < 10 or self.duration_sec <= 0:
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
        self.canvas.itemconfig("overlay", text=self._fmt(seconds), state="normal")

    # ── Timeline interaction ──

    def _seg_at(self, x):
        if self.duration_sec <= 0:
            return None
        cw = max(self._tl_w, 10)
        sec = self._x_to_sec(x, cw)
        for seg in reversed(self._segments):
            if seg["start"] <= sec <= seg["end"]:
                return seg
        return None

    def _timeline_press(self, event):
        seg = self._seg_at(event.x)
        if seg:
            self._selected_seg = seg["id"]
            self._drag_seg = seg
            self._drag_off = event.x
            self._was_playing = self.playing
            if self.playing:
                self.pause()
            self._update_sel_label()
            self._draw_timeline()
        else:
            self._selected_seg = None
            self._drag_seg = None
            self._update_sel_label()
            self._draw_timeline()
            self._dragging = True
            self._was_playing = self.playing
            if self.playing:
                self.pause()
            self._timeline_seek(event.x)

    def _timeline_drag(self, event):
        if self._drag_seg:
            dx = self._x_to_sec(event.x, max(self._tl_w, 10)) - self._x_to_sec(self._drag_off, max(self._tl_w, 10))
            cw = max(self._tl_w, 10)
            delta = ((event.x - self._drag_off) / cw) * self.duration_sec
            new_s = self._drag_seg["start"] + delta
            new_e = self._drag_seg["end"] + delta
            if new_s >= 0 and new_e <= self.duration_sec and new_s < new_e:
                self._drag_seg["start"] = new_s
                self._drag_seg["end"] = new_e
                self._drag_off = event.x
            self._draw_timeline()
        elif self._dragging:
            self._timeline_seek(event.x)

    def _timeline_release(self, event):
        self._drag_seg = None
        self._dragging = False
        if self._was_playing:
            self.resume()

    def _timeline_double(self, event):
        seg = self._seg_at(event.x)
        if seg:
            self._edit_segment(seg)

    def _timeline_right(self, event):
        seg = self._seg_at(event.x)
        if seg:
            self._selected_seg = seg["id"]
            self._update_sel_label()
            self._draw_timeline()
            menu = tk.Menu(self.window, tearoff=0)
            menu.add_command(label="Sửa...", command=lambda: self._edit_segment(seg))
            menu.add_command(label="Xoá", command=lambda: self._remove_segment(seg["id"]))
            menu.tk_popup(event.x_root, event.y_root)

    def _timeline_seek(self, x):
        self.show_frame(self._x_to_sec(x, self._tl_w))

    def _update_sel_label(self):
        if self._selected_seg:
            seg = next((s for s in self._segments if s["id"] == self._selected_seg), None)
            if seg:
                self.sel_label.config(
                    text=f"{seg['name']}  ({seg['start']:.1f}s → {seg['end']:.1f}s)"
                )
                self.del_btn.config(state="normal")
                return
        self.sel_label.config(text="")
        self.del_btn.config(state="disabled")

    # ── Audio segment management ──

    def _add_audio(self):
        if self.duration_sec <= 0:
            return
        path = filedialog.askopenfilename(
            title="Chọn file âm thanh",
            filetypes=[("Audio files", "*.mp3 *.wav"), ("All files", "*.*")],
        )
        if not path:
            return
        dur = self._get_audio_duration(path)
        if dur <= 0:
            messagebox.showerror("Lỗi", "Không đọc được duration audio!")
            return
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
        self._update_sel_label()
        self._draw_timeline()

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
                if s >= e or s < 0 or e > self.duration_sec:
                    raise ValueError
                seg["start"] = s
                seg["end"] = e
                self._reset_segments()
                self._update_sel_label()
                self._draw_timeline()
                dialog.destroy()
            except ValueError:
                messagebox.showwarning("Lỗi", "Giá trị không hợp lệ!")
        ttk.Button(dialog, text="Lưu", command=save).pack(pady=8)

    def _delete_selected(self):
        if self._selected_seg:
            self._remove_segment(self._selected_seg)

    def _remove_segment(self, sid):
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
        self._update_sel_label()
        self._draw_timeline()

    # ── Playback ──

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
        self._stop_all_segments()

    def resume(self):
        self.playing = True
        self.play_btn.config(text="⏸ Tạm dừng")
        # Seek cap to current position before sequential reading
        idx = max(0, min(int(self._current_sec * self.fps), self.total_frames - 1))
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        self._reset_segments()
        self._play_loop()

    def stop(self):
        self.pause()
        self.show_frame(0)
        self._reset_segments()

    def _play_loop(self):
        if not self.playing or self.cap is None:
            return
        ret, frame = self.cap.read()
        if not ret:
            self.pause()
            self._current_sec = self.duration_sec
            self._draw_playhead()
            self._stop_all_segments()
            return
        frame_pos = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
        seconds = (frame_pos - 1) / self.fps
        self._current_sec = seconds
        self._display_frame(frame)
        self.time_label.config(
            text=f"{self._fmt(seconds)} / {self._fmt(self.duration_sec)}"
        )
        self._draw_playhead()
        self._update_segments(seconds)
        delay = max(16, int(round(33 / self.speed)))
        self._after_id = self.canvas.after(delay, self._play_loop)

    def _on_speed_change(self, event=None):
        self.speed = self.speed_var.get()
        if self.playing:
            self.pause()
            self.resume()

    # ── Audio segment playback ──

    def _update_segments(self, seconds):
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
            seg = next((s for s in self._segments if s["id"] == sid), None)
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

    def _stop_all_segments(self):
        for sid in list(self._seg_playing):
            sound = self._seg_sounds.get(sid)
            if sound:
                try:
                    sound.stop()
                except Exception:
                    pass
        self._seg_playing.clear()

    def _reset_segments(self):
        self._stop_all_segments()
        self._seg_triggered.clear()

    # ── Merge ──

    def _do_merge(self):
        if not self._segments:
            messagebox.showwarning("Cảnh báo", "Chưa có audio nào!")
            return
        output_dir = Path("output/video")
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / f"{Path(self.video_file).stem}_merged.mp4"
        log_path = output_dir / "_merge_debug.log"

        self.add_btn.config(state="disabled")
        self.play_btn.config(state="disabled")

        import subprocess, imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

        try:
            self._segments.sort(key=lambda s: s["start"])
            current = str(self.video_file)
            for i, seg in enumerate(self._segments):
                out = str(output_dir / f"_part_{i}.mp4")
                delay_ms = int(seg["start"] * 1000)
                insert_dur = seg["end"] - seg["start"]

                r = subprocess.run([ffmpeg, "-i", current, "-hide_banner"],
                                   capture_output=True, text=True)
                has_audio = "Audio:" in r.stderr
                vid_dur = 0.0
                for line in r.stderr.splitlines():
                    if "Duration:" in line:
                        t = line.split("Duration:")[1].split(",")[0].strip()
                        h, m, s = t.split(":")
                        vid_dur = int(h) * 3600 + int(m) * 60 + float(s)
                if vid_dur <= 0:
                    raise RuntimeError(f"Could not probe video duration from: {current}")

                if has_audio:
                    fc = (
                        f"[0:a:0]volume=0:enable='between(t,{seg['start']},{seg['start'] + insert_dur})'[muted];"
                        f"[1:a:0]atrim=end={insert_dur}[trimmed];"
                        f"[trimmed]adelay={delay_ms}:all=1[delayed];"
                        f"[delayed]apad=whole_dur={vid_dur}[padded];"
                        f"[muted][padded]amix=inputs=2:duration=first:weights=1 1,volume=2[outa]"
                    )
                else:
                    fc = (
                        f"[1:a:0]atrim=end={insert_dur}[trimmed];"
                        f"[trimmed]adelay={delay_ms}:all=1[delayed];"
                        f"[delayed]apad=whole_dur={vid_dur}[outa]"
                    )

                cmd = [
                    ffmpeg, "-y", "-hide_banner", "-loglevel", "warning",
                    "-i", current, "-i", seg["path"],
                    "-filter_complex", fc,
                    "-map", "0:v:0", "-map", "[outa]",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-t", str(vid_dur), out,
                ]

                with open(log_path, "a", encoding="utf-8") as log:
                    log.write(f"=== SEGMENT {i} ===\n")
                    log.write(f"start={seg['start']}, end={seg['end']}, insert_dur={insert_dur}\n")
                    log.write(f"delay_ms={delay_ms}, vid_dur={vid_dur}, has_audio={has_audio}\n")
                    log.write(f"fc={fc}\n")
                    log.write(f"cmd={' '.join(str(x) for x in cmd)}\n")

                result = subprocess.run(cmd, capture_output=True, text=True)
                with open(log_path, "a", encoding="utf-8") as log:
                    log.write(f"returncode={result.returncode}\n")
                    log.write(f"stderr={result.stderr[-500:]}\n\n")

                if result.returncode != 0:
                    raise RuntimeError(f"ffmpeg thất bại (segment {i}):\n{result.stderr[-300:]}")

                current = out

            import shutil
            shutil.move(current, out_path)
            for p in output_dir.glob("_part_*.mp4"):
                p.unlink(missing_ok=True)

            self.add_btn.config(state="normal")
            self.play_btn.config(state="normal")
            if messagebox.askyesno("Thành công", f"Đã tạo:\n{out_path}\n\nMở file?"):
                import os
                os.startfile(out_path)

        except Exception as e:
            self.add_btn.config(state="normal")
            self.play_btn.config(state="normal")
            with open(log_path, "a", encoding="utf-8") as log:
                log.write(f"EXCEPTION: {e}\n")
            messagebox.showerror("Lỗi", str(e))

    # ── Nudge ──

    def _nudge_frame(self, direction):
        cur = int(self._current_sec * self.fps)
        new = max(0, min(cur + direction, self.total_frames - 1))
        self.show_frame(new / self.fps)
        self._reset_segments()

    def _nudge_sec(self, direction):
        new = max(0, min(self._current_sec + direction, self.duration_sec))
        self.show_frame(new)
        self._reset_segments()

    def _on_mousewheel(self, event):
        self._nudge_frame(event.delta // 120)

    # ── Resize ──

    def _on_resize(self, event):
        if event.widget != self.window or self.cap is None:
            return
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        if cw >= 10 and ch >= 10:
            self.show_frame(self._current_sec)
            self._draw_timeline()

    # ── Cleanup ──

    def _on_close(self):
        self.pause()
        if self._after_id:
            self.canvas.after_cancel(self._after_id)
            self._after_id = None
        self._stop_all_segments()
        self._seg_sounds.clear()
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
