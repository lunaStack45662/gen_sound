import os
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from core.audio_generator import AudioGenerator
from core.model_loader import ModelLoader
from core.audio_player import AudioPlayer
from gui.icons import Icons
from gui.tooltip import add_tooltip
from gui.theme import COLORS, SPACING, RADIUS


class GenAudioTab(ctk.CTkFrame):
    def __init__(self, parent, model_loader: ModelLoader, player: AudioPlayer):
        super().__init__(parent, fg_color="transparent")
        self.model_loader = model_loader
        self.player = player
        self.output_dir = Path("output/audio")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._selected_path = None
        self._file_widgets = []
        self._build_ui()
        self._refresh_file_list()
        self.pack(fill="both", expand=True)

    def _build_ui(self):
        self._img_play = Icons.get("play_arrow", 18)
        self._img_stop = Icons.get("stop", 18)
        self._img_delete = Icons.get("delete", 18)
        self._img_folder = Icons.get("folder_open", 18)
        self._img_add = Icons.get("add", 18)
        self._img_play_small = Icons.get("play_arrow", 14)
        self._img_stop_small = Icons.get("stop", 14)
        self._img_delete_small = Icons.get("delete", 14)

        main_pan = ctk.CTkFrame(self, fg_color="transparent")
        main_pan.pack(fill="both", expand=True)

        # Left sidebar
        sidebar = ctk.CTkFrame(main_pan, fg_color=COLORS["bg_sidebar"],
                               border_width=1, border_color=COLORS["border"],
                               corner_radius=RADIUS["md"], width=220)
        sidebar.pack(side="left", fill="y", padx=(SPACING["md"], SPACING["sm"]), pady=SPACING["sm"])
        sidebar.pack_propagate(False)

        ctk.CTkLabel(sidebar, text="  Các file đã tạo:", text_color=COLORS["text_primary"],
                      font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=SPACING["sm"], pady=(SPACING["md"], SPACING["sm"]))

        list_container = ctk.CTkFrame(sidebar, fg_color="transparent")
        list_container.pack(fill="both", expand=True, padx=SPACING["xs"], pady=(0, SPACING["sm"]))

        canvas_frame = ctk.CTkFrame(list_container, fg_color="transparent")
        canvas_frame.pack(fill="both", expand=True)

        self.files_canvas = tk.Canvas(canvas_frame, bg=COLORS["bg_card"], highlightthickness=0)
        self.files_canvas.pack(side="left", fill="both", expand=True)

        vscroll = tk.Scrollbar(canvas_frame, orient="vertical", command=self.files_canvas.yview)
        vscroll.pack(side="right", fill="y")
        self.files_canvas.configure(yscrollcommand=vscroll.set)

        self.files_inner = ctk.CTkFrame(self.files_canvas, fg_color="transparent")
        self.files_window = self.files_canvas.create_window((0, 0), window=self.files_inner, anchor="nw")

        self.files_inner.bind("<Configure>", lambda e: self.files_canvas.configure(scrollregion=self.files_canvas.bbox("all")))
        self.files_canvas.bind("<Configure>", lambda e: self.files_canvas.itemconfig(self.files_window, width=e.width))

        # Button bar
        btn_bar = ctk.CTkFrame(sidebar, fg_color="transparent")
        btn_bar.pack(fill="x", pady=(SPACING["sm"], SPACING["md"]))

        self.preview_btn = ctk.CTkButton(btn_bar, image=self._img_play, text="",
                                          command=self._toggle_play, width=28, height=28,
                                          corner_radius=RADIUS["sm"])
        self.preview_btn.pack(side="left", padx=(SPACING["md"], SPACING["xs"]))
        add_tooltip(self.preview_btn, "Phát/Dừng file đã chọn")

        del_btn = ctk.CTkButton(btn_bar, image=self._img_delete, text="",
                                command=self._delete_selected, width=28, height=28,
                                corner_radius=RADIUS["sm"], fg_color=COLORS["error"], hover_color="#DC2626")
        del_btn.pack(side="left", padx=(0, SPACING["xs"]))
        add_tooltip(del_btn, "Xoá file đã chọn")

        folder_btn = ctk.CTkButton(btn_bar, image=self._img_folder, text="",
                                   command=self._open_output_dir, width=28, height=28,
                                   corner_radius=RADIUS["sm"])
        folder_btn.pack(side="left")
        add_tooltip(folder_btn, "Mở thư mục chứa file")

        # Right panel
        right_panel = ctk.CTkFrame(main_pan, fg_color="transparent")
        right_panel.pack(side="right", fill="both", expand=True)

        engine_row = ctk.CTkFrame(right_panel, fg_color="transparent")
        engine_row.pack(fill="x", padx=SPACING["md"], pady=(SPACING["sm"], SPACING["xs"]))
        ctk.CTkLabel(engine_row, text="Model TTS:", text_color=COLORS["text_secondary"]).pack(side="left")
        self.engine_var = tk.StringVar(value="Vieneu")
        self.engine_combo = ctk.CTkComboBox(engine_row, variable=self.engine_var, values=["Vieneu", "OmniVoice"],
                                            state="readonly", width=160, command=self._on_engine_change,
                                            corner_radius=RADIUS["sm"], height=32)
        self.engine_combo.pack(side="left", padx=(SPACING["sm"], 0))
        add_tooltip(self.engine_combo, "Chuyển đổi giữa Vieneu và OmniVoice")

        self.tabview = ctk.CTkTabview(right_panel, corner_radius=RADIUS["md"], fg_color=COLORS["bg_card"],
                                      border_width=1, border_color=COLORS["border"])
        self.tabview.pack(fill="x", padx=SPACING["md"], pady=(SPACING["xs"], SPACING["xs"]))

        tab1 = self.tabview.add("Giọng có sẵn")
        tab2 = self.tabview.add("Giọng từ file")
        self._build_tab_preset(tab1)
        self._build_tab_import(tab2)

        ctk.CTkLabel(right_panel, text="Nhập text:", text_color=COLORS["text_primary"]).pack(anchor="w",
                     padx=SPACING["md"], pady=(SPACING["sm"], SPACING["xs"]))
        self.text_input = ctk.CTkTextbox(right_panel, corner_radius=RADIUS["md"],
                                         border_width=1, border_color=COLORS["border"], height=320)
        self.text_input.pack(fill="x", padx=SPACING["md"])

        row2 = ctk.CTkFrame(right_panel, fg_color="transparent")
        row2.pack(fill="x", padx=SPACING["md"], pady=(SPACING["sm"], SPACING["md"]))
        self.gen_btn = ctk.CTkButton(row2, text="Tạo âm thanh", command=self._on_generate,
                                      corner_radius=RADIUS["sm"], height=36)
        self.gen_btn.pack(side="left")
        add_tooltip(self.gen_btn, "Tạo file MP3 từ text với giọng đã chọn")
        self.progress = ctk.CTkProgressBar(row2, width=200)
        self.progress.pack(side="left", padx=(SPACING["lg"], 0))
        self.progress.set(0)

    def _on_engine_change(self, choice):
        self.engine_combo.configure(state="disabled")
        self.progress.start()
        self.after(100, self._do_engine_switch, choice)

    def _do_engine_switch(self, choice):
        try:
            is_omni = choice == "OmniVoice"
            engine = self.model_loader.switch(choice)
            voice_names = [label for label, _ in engine.voices]
            self.voice_combo.configure(values=voice_names)
            if voice_names:
                self.voice_combo.set(voice_names[0])
            if is_omni:
                self.tabview.set("Giọng từ file")
        finally:
            self.engine_combo.configure(state="readonly")
            self.progress.stop()

    @property
    def _current_engine(self):
        return self.model_loader.get_engine(self.engine_var.get())

    def _build_tab_preset(self, parent):
        inner = ctk.CTkFrame(parent, fg_color="transparent")
        inner.pack(padx=SPACING["md"], pady=SPACING["sm"])
        ctk.CTkLabel(inner, text="Giọng đọc", text_color=COLORS["text_secondary"]).pack(side="left")
        self.voice_var = tk.StringVar()
        voice_names = ["Ngọc Lan", "Gia Bảo", "Thái Sơn", "Đức Trí", "Mỹ Duyên",
                       "Trúc Ly", "Xuân Vĩnh", "Trọng Hữu", "Bình An", "Ngọc Linh"]
        self.voice_combo = ctk.CTkComboBox(inner, variable=self.voice_var, values=voice_names,
                                           state="readonly", width=320, corner_radius=RADIUS["sm"])
        if voice_names:
            self.voice_combo.set(voice_names[0])
        self.voice_combo.pack(side="left", padx=(SPACING["sm"], 0))
        ctk.CTkLabel(inner, text="Tốc độ", text_color=COLORS["text_secondary"]).pack(
            side="left", padx=(SPACING["lg"], 0))
        self.speed_var = tk.StringVar(value="Thường (1.0x)")
        self.speed_combo = ctk.CTkComboBox(inner, variable=self.speed_var,
            values=["Chậm (0.8x)", "Thường (1.0x)", "Nhanh (1.25x)", "Rất nhanh (1.5x)"],
            state="readonly", width=140, corner_radius=RADIUS["sm"])
        self.speed_combo.set("Thường (1.0x)")
        self.speed_combo.pack(side="left", padx=(SPACING["sm"], 0))

    def _build_tab_import(self, parent):
        inner = ctk.CTkFrame(parent, fg_color="transparent")
        inner.pack(padx=SPACING["md"], pady=SPACING["sm"])
        row = ctk.CTkFrame(inner, fg_color="transparent")
        row.pack(fill="x", pady=(0, SPACING["sm"]))
        ctk.CTkLabel(row, text="Tốc độ", text_color=COLORS["text_secondary"]).pack(side="left")
        self.imp_speed_var = tk.StringVar(value="Thường (1.0x)")
        self.imp_speed_combo = ctk.CTkComboBox(row, variable=self.imp_speed_var,
            values=["Chậm (0.8x)", "Thường (1.0x)", "Nhanh (1.25x)", "Rất nhanh (1.5x)"],
            state="readonly", width=140, corner_radius=RADIUS["sm"])
        self.imp_speed_combo.set("Thường (1.0x)")
        self.imp_speed_combo.pack(side="left")
        file_row = ctk.CTkFrame(inner, fg_color="transparent")
        file_row.pack(fill="x", pady=(SPACING["sm"], 0))
        ctk.CTkButton(file_row, image=self._img_add, text="",
                      command=self._select_ref_audio, width=32, height=32, corner_radius=RADIUS["sm"]).pack(side="left")
        ctk.CTkLabel(file_row, text="Chọn file giọng mẫu (3-5s)", text_color=COLORS["text_secondary"]).pack(
            side="left", padx=(SPACING["xs"], SPACING["md"]))
        self.ref_audio_label = ctk.CTkLabel(file_row, text="Chưa chọn", text_color=COLORS["warning"])
        self.ref_audio_label.pack(side="left")
        self.ref_audio_path = None
        add_tooltip(file_row, "Chọn file WAV/MP3 để clone giọng")

    def _select_ref_audio(self):
        path = filedialog.askopenfilename(
            title="Chọn file giọng mẫu (WAV/MP3, 3-5s)",
            filetypes=[("Audio files", "*.wav *.mp3"), ("All files", "*.*")])
        if path:
            self.ref_audio_path = Path(path)
            self.ref_audio_label.configure(text=self.ref_audio_path.name, text_color="#F1F1F3")

    def _on_generate(self):
        text = self.text_input.get("1.0", "end-1c").strip()
        if not text:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập text!")
            return
        engine = self._current_engine
        active_tab = self.tabview.get()
        if active_tab == "Giọng có sẵn":
            voice_label = self.voice_var.get()
            if not voice_label:
                messagebox.showwarning("Cảnh báo", "Vui lòng chọn giọng đọc!")
                return
            voice_id = voice_label
            if hasattr(engine, 'voices'):
                for label, vid in engine.voices:
                    if label == voice_label:
                        voice_id = vid
                        break
            ref_audio = None
            speed_text = self.speed_var.get()
        else:
            if not self.ref_audio_path or not self.ref_audio_path.exists():
                messagebox.showwarning("Cảnh báo", "Vui lòng chọn file giọng mẫu ở tab 'Giọng từ file'!")
                return
            ref_audio = self.ref_audio_path
            speed_text = self.imp_speed_var.get()
            voice_id = "default"
        from datetime import datetime
        timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
        output_path = self.output_dir / f"audio_{timestamp}.mp3"
        self.gen_btn.configure(state="disabled")
        self.progress.start()
        speed_map = {"Chậm (0.8x)": 0.8, "Thường (1.0x)": 1.0, "Nhanh (1.25x)": 1.25, "Rất nhanh (1.5x)": 1.5}
        target_speed = speed_map.get(speed_text, 1.0)
        self._pending_speed = target_speed
        engine.generate(text=text, voice_name=voice_id, output_path=output_path,
                      ref_audio=ref_audio, on_done=self._on_done, on_error=self._on_error)

    def _on_done(self, path):
        path = Path(path)
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
        for frame, _, _ in self._file_widgets:
            frame.destroy()
        self._file_widgets.clear()
        files = sorted(self.output_dir.glob("*.mp3"))
        for f in files:
            self._add_file_row(f)

    def _add_file_row(self, file_path):
        file_name = file_path.name
        display_name = file_path.stem
        row_frame = ctk.CTkFrame(self.files_inner, fg_color=COLORS["bg_secondary"], height=32)
        row_frame.pack(fill="x", pady=1)

        play_btn = ctk.CTkButton(row_frame, image=self._img_play_small, text="", width=28, height=28,
                                corner_radius=0, fg_color="transparent", hover_color=COLORS["bg_hover"])
        play_btn.pack(side="left", padx=(SPACING["xs"], SPACING["xs"]))
        play_btn.bind("<Button-1>", lambda e, fn=file_name, btn=play_btn: self._toggle_play_row(fn, btn))

        del_btn = ctk.CTkButton(row_frame, image=self._img_delete_small, text="", width=28, height=28,
                               corner_radius=0, fg_color="transparent", hover_color=COLORS["bg_hover"])
        del_btn.pack(side="left", padx=(0, SPACING["xs"]))
        del_btn.bind("<Button-1>", lambda e, fn=file_name: self._delete_file_row(fn))

        name_label = ctk.CTkLabel(row_frame, text=f" {display_name}", text_color=COLORS["text_primary"],
                                  font=("Segoe UI", 11), anchor="w")
        name_label.pack(side="left", fill="both", expand=True)

        self._file_widgets.append((row_frame, file_name, play_btn))

    def _toggle_play_row(self, file_name, btn):
        path = self.output_dir / file_name
        if self.player.is_playing and self._selected_path == path:
            self._stop_play()
            btn.configure(image=self._img_play_small)
        elif path.exists():
            self._selected_path = path
            self._play_file(path, btn)

    def _play_file(self, path, btn=None):
        self.player.stop()
        if btn:
            btn.configure(image=self._img_stop_small)
        def on_finish():
            self.preview_btn.configure(image=self._img_play)
        self.player.play(path, on_finish=on_finish)
        self.preview_btn.configure(image=self._img_stop)

    def _delete_file_row(self, file_name):
        path = self.output_dir / file_name
        if not path.exists():
            return
        if not messagebox.askyesno("Xác nhận", f"Xóa {file_name}?"):
            return
        self.player.stop()
        self.preview_btn.configure(image=self._img_play)
        import time
        for attempt in range(3):
            try:
                path.unlink()
                break
            except PermissionError:
                if attempt < 2:
                    time.sleep(0.3)
                    self.player.stop()
                else:
                    messagebox.showerror("Lỗi", f"Không thể xoá file:\n{path}\nFile đang được sử dụng.")
        self._selected_path = None
        self._refresh_file_list()

    def _play_file_from_row(self, file_name):
        path = self.output_dir / file_name
        if path.exists():
            self._selected_path = path
            if self.player.is_playing:
                self._stop_play()
            else:
                self._play_file(path)

    def _toggle_play(self):
        if self.player.is_playing:
            self._stop_play()
        else:
            selected = self._selected_path
            if selected and selected.exists():
                self._play_file(selected)

    def _stop_play(self):
        self.player.stop()
        self.preview_btn.configure(image=self._img_play)

    def _delete_selected(self):
        selected = self._selected_path
        if not selected or not selected.exists():
            return
        if not messagebox.askyesno("Xác nhận", f"Xóa {selected.name}?"):
            return
        self.player.stop()
        self.preview_btn.configure(image=self._img_play)
        import time
        for attempt in range(3):
            try:
                selected.unlink()
                break
            except PermissionError:
                if attempt < 2:
                    time.sleep(0.3)
                    self.player.stop()
                else:
                    messagebox.showerror("Lỗi", f"Không thể xoá file:\n{selected}\nFile đang được sử dụng.")
        self._selected_path = None
        self._refresh_file_list()

    def _open_output_dir(self):
        os.startfile(str(self.output_dir.resolve()))