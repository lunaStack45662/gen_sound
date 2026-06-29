import os
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from core.audio_generator import AudioGenerator
from core.audio_player import AudioPlayer


class GenAudioTab(ttk.Frame):
    def __init__(self, parent, audio_gen: AudioGenerator, player: AudioPlayer):
        super().__init__(parent)
        self.audio_gen = audio_gen
        self.player = player
        self.output_dir = Path("output/audio")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._selected_path = None
        self._build_ui()
        self._refresh_file_list()

    def _build_ui(self):
        row1 = ttk.Frame(self)
        row1.pack(fill="x", padx=10, pady=(10, 5))
        ttk.Label(row1, text="Giọng đọc:").pack(side="left")
        self.voice_var = tk.StringVar()
        voice_names = [label for label, _ in self.audio_gen.voices]
        self.voice_combo = ttk.Combobox(
            row1, textvariable=self.voice_var, values=voice_names,
            state="readonly", width=40,
        )
        if voice_names:
            self.voice_combo.current(0)
        self.voice_combo.pack(side="left", padx=(5, 0))

        ttk.Label(row1, text="  Tốc độ:").pack(side="left")
        self.speed_var = tk.StringVar(value="Thường (1.0x)")
        self.speed_combo = ttk.Combobox(
            row1, textvariable=self.speed_var,
            values=["Chậm (0.8x)", "Thường (1.0x)", "Nhanh (1.25x)", "Rất nhanh (1.5x)"],
            state="readonly", width=14,
        )
        self.speed_combo.current(1)
        self.speed_combo.pack(side="left", padx=(5, 0))

        clone_frame = ttk.LabelFrame(self, text="Voice Cloning (tùy chọn)", padding=5)
        clone_frame.pack(fill="x", padx=10, pady=(5, 5))
        ttk.Button(clone_frame, text="Chọn file giọng mẫu (3-5s)...",
                   command=self._select_ref_audio).pack(side="left")
        self.ref_audio_label = ttk.Label(clone_frame, text="Không dùng", foreground="gray")
        self.ref_audio_label.pack(side="left", padx=(10, 0))
        self.ref_audio_path = None

        ttk.Label(self, text="Nhập text:").pack(anchor="w", padx=10, pady=(10, 2))
        self.text_input = scrolledtext.ScrolledText(self, height=8, wrap="word")
        self.text_input.pack(fill="both", expand=True, padx=10)

        row2 = ttk.Frame(self)
        row2.pack(fill="x", padx=10, pady=10)
        self.gen_btn = ttk.Button(row2, text="Tạo âm thanh", command=self._on_generate)
        self.gen_btn.pack(side="left")
        self.progress = ttk.Progressbar(row2, mode="indeterminate", length=200)
        self.progress.pack(side="left", padx=(10, 0))

        ttk.Label(self, text="Các file đã tạo:").pack(anchor="w", padx=10)
        list_frame = ttk.Frame(self)
        list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical")
        self.file_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.file_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.file_listbox.pack(side="left", fill="both", expand=True)
        self.file_listbox.bind("<Double-Button-1>", lambda e: self._play_selected())

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))
        self.preview_btn = ttk.Button(btn_frame, text="▶ Phát thử", command=self._play_selected)
        self.preview_btn.pack(side="left", padx=(0, 5))
        ttk.Button(btn_frame, text="⏹ Dừng", command=self._stop_play).pack(
            side="left", padx=(0, 5)
        )
        ttk.Button(btn_frame, text="Xóa", command=self._delete_selected).pack(
            side="left"
        )
        ttk.Button(
            btn_frame, text="Mở thư mục", command=self._open_output_dir
        ).pack(side="right")

    def _select_ref_audio(self):
        path = filedialog.askopenfilename(
            title="Chọn file giọng mẫu (WAV/MP3, 3-5s)",
            filetypes=[("Audio files", "*.wav *.mp3"), ("All files", "*.*")],
        )
        if path:
            self.ref_audio_path = Path(path)
            self.ref_audio_label.config(text=self.ref_audio_path.name, foreground="black")

    def _on_generate(self):
        text = self.text_input.get("1.0", "end-1c").strip()
        if not text:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập text!")
            return
        voice_label = self.voice_var.get()
        if not voice_label:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn giọng đọc!")
            return

        voice_id = voice_label
        for label, vid in self.audio_gen.voices:
            if label == voice_label:
                voice_id = vid
                break

        idx = len(list(self.output_dir.glob("*.mp3"))) + 1
        output_path = self.output_dir / f"audio_{idx:03d}.mp3"

        self.gen_btn.config(state="disabled")
        self.progress.start()

        speed_text = self.speed_var.get()
        speed_map = {"Chậm (0.8x)": 0.8, "Thường (1.0x)": 1.0,
                      "Nhanh (1.25x)": 1.25, "Rất nhanh (1.5x)": 1.5}
        target_speed = speed_map.get(speed_text, 1.0)

        self._pending_speed = target_speed
        self._pending_mp3 = output_path

        self.audio_gen.generate(
            text=text,
            voice_name=voice_id,
            output_path=output_path,
            ref_audio=self.ref_audio_path,
            on_done=self._on_done,
            on_error=self._on_error,
        )

    def _on_done(self, path):
        apply_speed = getattr(self, "_pending_speed", 1.0)
        if apply_speed != 1.0:
            try:
                adjusted = path.with_name(f"{path.stem}_speed{apply_speed}{path.suffix}")
                AudioGenerator.adjust_speed(path, apply_speed, adjusted)
                path.unlink()
                adjusted.rename(path)
            except Exception as e:
                messagebox.showwarning("Tốc độ", f"Không thể điều chỉnh tốc độ:\n{e}")
        self.gen_btn.config(state="normal")
        self.progress.stop()
        self._refresh_file_list()
        messagebox.showinfo("Thành công", f"Đã tạo:\n{path}")

    def _on_error(self, error):
        self.gen_btn.config(state="normal")
        self.progress.stop()
        messagebox.showerror("Lỗi", f"Tạo âm thanh thất bại:\n{error}")

    def _refresh_file_list(self):
        self.file_listbox.delete(0, "end")
        for f in sorted(self.output_dir.glob("*.mp3")):
            size = f.stat().st_size / 1024
            self.file_listbox.insert("end", f"{f.name}  ({size:.1f} KB)")

    def _play_selected(self):
        sel = self.file_listbox.curselection()
        if not sel:
            return
        name = self.file_listbox.get(sel[0]).split("  ")[0]
        path = self.output_dir / name
        if path.exists():
            self._selected_path = path
            self.player.stop()

            def on_finish():
                self.preview_btn.config(text="▶ Phát thử")

            self.player.play(path, on_finish=on_finish)
            self.preview_btn.config(text="⏸ Đang phát")

    def _stop_play(self):
        self.player.stop()
        self.preview_btn.config(text="▶ Phát thử")

    def _delete_selected(self):
        sel = self.file_listbox.curselection()
        if not sel:
            return
        name = self.file_listbox.get(sel[0]).split("  ")[0]
        path = self.output_dir / name
        if path.exists() and messagebox.askyesno("Xác nhận", f"Xóa {name}?"):
            path.unlink()
            self._refresh_file_list()

    def _open_output_dir(self):
        os.startfile(str(self.output_dir.resolve()))
