import os
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk

from core.audio_generator import AudioGenerator


class GenAudioTab(ttk.Frame):
    def __init__(self, parent, audio_gen: AudioGenerator):
        super().__init__(parent)
        self.audio_gen = audio_gen
        self.output_dir = Path("output/audio")
        self.output_dir.mkdir(parents=True, exist_ok=True)
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
            state="readonly", width=45,
        )
        if voice_names:
            self.voice_combo.current(0)
        self.voice_combo.pack(side="left", padx=(5, 0))

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
        ttk.Button(btn_frame, text="▶ Phát thử", command=self._play_selected).pack(
            side="left", padx=(0, 5)
        )
        ttk.Button(btn_frame, text="Xóa", command=self._delete_selected).pack(
            side="left"
        )
        ttk.Button(
            btn_frame, text="Mở thư mục", command=self._open_output_dir
        ).pack(side="right")

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

        self.audio_gen.generate(
            text=text,
            voice_name=voice_id,
            output_path=output_path,
            on_done=self._on_done,
            on_error=self._on_error,
        )

    def _on_done(self, path):
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
            os.startfile(str(path))

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
