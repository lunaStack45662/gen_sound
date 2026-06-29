import os
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from core.audio_generator import AudioGenerator
from core.audio_player import AudioPlayer
from gui.icons import Icons
from gui.tooltip import add_tooltip


class GenAudioTab(ctk.CTkFrame):
    def __init__(self, parent, audio_gen: AudioGenerator, player: AudioPlayer):
        super().__init__(parent, fg_color="transparent")
        self.audio_gen = audio_gen
        self.player = player
        self.output_dir = Path("output/audio")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._selected_path = None
        self._build_ui()
        self._refresh_file_list()
        self.pack(fill="both", expand=True)

    def _build_ui(self):
        self._img_play = Icons.get("play_arrow", 20)
        self._img_stop = Icons.get("stop", 20)
        self._img_delete = Icons.get("delete", 20)
        self._img_folder = Icons.get("folder_open", 20)
        self._img_add = Icons.get("add", 20)

        # ── Card: giọng + tốc độ ──
        card1 = ctk.CTkFrame(self, fg_color="#1E2130", border_width=1,
                             border_color="#2A2D3E", corner_radius=8)
        card1.pack(fill="x", padx=16, pady=(16, 4))
        inner1 = ctk.CTkFrame(card1, fg_color="transparent")
        inner1.pack(padx=16, pady=8)

        ctk.CTkLabel(inner1, text="Giọng đọc", text_color="#8B8FA8").pack(side="left")
        self.voice_var = tk.StringVar()
        voice_names = [label for label, _ in self.audio_gen.voices]
        self.voice_combo = ctk.CTkComboBox(
            inner1, variable=self.voice_var, values=voice_names,
            state="readonly", width=320,
        )
        if voice_names:
            self.voice_combo.set(voice_names[0])
        self.voice_combo.pack(side="left", padx=(8, 0))

        ctk.CTkLabel(inner1, text="Tốc độ", text_color="#8B8FA8").pack(
            side="left", padx=(16, 0))
        self.speed_var = tk.StringVar(value="Thường (1.0x)")
        self.speed_combo = ctk.CTkComboBox(
            inner1, variable=self.speed_var,
            values=["Chậm (0.8x)", "Thường (1.0x)", "Nhanh (1.25x)", "Rất nhanh (1.5x)"],
            state="readonly", width=140,
        )
        self.speed_combo.set("Thường (1.0x)")
        self.speed_combo.pack(side="left", padx=(8, 0))

        # ── Card: Voice Cloning ──
        card2 = ctk.CTkFrame(self, fg_color="#1E2130", border_width=1,
                             border_color="#2A2D3E", corner_radius=8)
        card2.pack(fill="x", padx=16, pady=4)
        inner2 = ctk.CTkFrame(card2, fg_color="transparent")
        inner2.pack(fill="x", padx=16, pady=8)

        ctk.CTkLabel(inner2, text="Voice Cloning",
                     font=("Segoe UI", 14, "bold")).pack(anchor="w")
        r2 = ctk.CTkFrame(inner2, fg_color="transparent")
        r2.pack(fill="x", pady=(4, 0))
        ctk.CTkButton(r2, image=self._img_add, text="",
                      command=self._select_ref_audio,
                      width=32, height=32, corner_radius=6).pack(side="left")
        ctk.CTkLabel(r2, text="Chọn file giọng mẫu (3-5s)").pack(
            side="left", padx=(4, 16))
        self.ref_audio_label = ctk.CTkLabel(r2, text="Không dùng",
                                            text_color="#8B8FA8")
        self.ref_audio_label.pack(side="left")
        self.ref_audio_path = None

        # ── Text input ──
        ctk.CTkLabel(self, text="Nhập text:").pack(anchor="w",
                    padx=16, pady=(16, 4))
        self.text_input = ctk.CTkTextbox(self, corner_radius=6,
                                          border_width=1, border_color="#2A2D3E")
        self.text_input.pack(fill="both", expand=True, padx=16)

        # ── Generate row ──
        row2 = ctk.CTkFrame(self, fg_color="transparent")
        row2.pack(fill="x", padx=16, pady=16)
        self.gen_btn = ctk.CTkButton(row2, text="Tạo âm thanh",
                                      command=self._on_generate,
                                      corner_radius=6, height=36)
        self.gen_btn.pack(side="left")
        add_tooltip(self.gen_btn, "Tạo file MP3 từ text với giọng đã chọn")
        self.progress = ctk.CTkProgressBar(row2, width=200)
        self.progress.pack(side="left", padx=(16, 0))
        self.progress.set(0)

        # ── Card: file list + action buttons (grid) ──
        ctk.CTkLabel(self, text="Các file đã tạo:").pack(anchor="w", padx=16)
        card3 = ctk.CTkFrame(self, fg_color="#1E2130", border_width=1,
                             border_color="#2A2D3E", corner_radius=8)
        card3.pack(fill="both", expand=True, padx=16,
                   pady=(4, 16))
        inner3 = ctk.CTkFrame(card3, fg_color="transparent")
        inner3.pack(fill="both", expand=True, padx=8, pady=8)

        # ── File list (left) ──
        list_container = ctk.CTkFrame(inner3, fg_color="transparent")
        list_container.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(list_container, orient="vertical",
                                 bg="#1A1D27", troughcolor="#0F1117")
        self.file_listbox = tk.Listbox(list_container, yscrollcommand=scrollbar.set,
                                        bg="#1A1D27", fg="#F1F1F3",
                                        selectbackground="#3B82F6",
                                        selectforeground="#F1F1F3",
                                        relief="flat", borderwidth=0,
                                        highlightthickness=0,
                                        font=("Segoe UI", 11))
        scrollbar.config(command=self.file_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.file_listbox.pack(side="left", fill="both", expand=True)
        self.file_listbox.bind("<Double-Button-1>", lambda e: self._play_selected())

        # ── Action buttons (vertical, right side) ──
        btn_frame = ctk.CTkFrame(inner3, fg_color="transparent", width=48)
        btn_frame.pack(side="right", fill="y", padx=(8, 2))
        btn_frame.pack_propagate(False)
        # center buttons vertically
        btn_center = ctk.CTkFrame(btn_frame, fg_color="transparent")
        btn_center.pack(expand=True)

        self.preview_btn = ctk.CTkButton(btn_center, image=self._img_play, text="",
                                          command=self._play_selected,
                                          width=40, height=36, corner_radius=6)
        self.preview_btn.pack(pady=(0, 6))
        add_tooltip(self.preview_btn, "Phát thử")

        preview_stop_btn = ctk.CTkButton(btn_center, image=self._img_stop, text="",
                                          command=self._stop_play,
                                          width=40, height=36, corner_radius=6)
        preview_stop_btn.pack(pady=(0, 6))
        add_tooltip(preview_stop_btn, "Dừng")

        preview_del_btn = ctk.CTkButton(btn_center, image=self._img_delete, text="",
                                         command=self._delete_selected,
                                         width=40, height=36, corner_radius=6,
                                         fg_color="#EF4444", hover_color="#DC2626")
        preview_del_btn.pack(pady=(0, 6))
        add_tooltip(preview_del_btn, "Xoá")

        preview_folder_btn = ctk.CTkButton(btn_center, image=self._img_folder, text="",
                                            command=self._open_output_dir,
                                            width=40, height=36, corner_radius=6)
        preview_folder_btn.pack()
        add_tooltip(preview_folder_btn, "Mở thư mục")

    def _select_ref_audio(self):
        path = filedialog.askopenfilename(
            title="Chọn file giọng mẫu (WAV/MP3, 3-5s)",
            filetypes=[("Audio files", "*.wav *.mp3"), ("All files", "*.*")],
        )
        if path:
            self.ref_audio_path = Path(path)
            self.ref_audio_label.configure(text=self.ref_audio_path.name,
                                           text_color="#F1F1F3")

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

        existing = sorted(self.output_dir.glob("audio_*.mp3"))
        idx = 1
        for f in existing:
            try:
                n = int(f.stem.split("_")[1])
                if n >= idx:
                    idx = n + 1
            except (IndexError, ValueError):
                continue
        output_path = self.output_dir / f"audio_{idx:03d}.mp3"

        self.gen_btn.configure(state="disabled")
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
        self.gen_btn.configure(state="normal")
        self.progress.stop()
        self._refresh_file_list()
        messagebox.showinfo("Thành công", f"Đã tạo:\n{path}")

    def _on_error(self, error):
        self.gen_btn.configure(state="normal")
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
                self.preview_btn.configure(image=self._img_play)

            self.player.play(path, on_finish=on_finish)
            self.preview_btn.configure(image=self._img_stop)

    def _stop_play(self):
        self.player.stop()
        self.preview_btn.configure(image=self._img_play)

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
