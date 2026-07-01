import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image, ImageTk

from core.image_editor import ImageEditor
from gui.icons import Icons
from gui.theme import COLORS, SPACING, RADIUS
from gui.tooltip import add_tooltip


class ImageEditorTab(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.editor = ImageEditor()
        self._original: Image.Image | None = None
        self._processed: Image.Image | None = None
        self._tk_image: ImageTk.PhotoImage | None = None
        self._current_path: Path | None = None
        self._build_ui()
        self.pack(fill="both", expand=True)

    def _build_ui(self):
        self._img_add = Icons.get("add", 20)
        self._img_save = Icons.get("check", 20)
        self._img_folder = Icons.get("folder_open", 20)
        self._img_delete = Icons.get("delete", 20)

        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", padx=SPACING["md"], pady=(SPACING["md"], SPACING["sm"]))

        open_btn = ctk.CTkButton(toolbar, image=self._img_add, text=" Mở ảnh",
                                 command=self._open_image, corner_radius=RADIUS["sm"], height=32)
        open_btn.pack(side="left", padx=(0, SPACING["xs"]))
        add_tooltip(open_btn, "Mở file ảnh (PNG/JPG/WEBP)")

        self.model_var = tk.StringVar(value="SAM2")
        self.model_combo = ctk.CTkComboBox(toolbar, variable=self.model_var,
                                            values=["SAM2", "rembg"],
                                            state="readonly", width=90, corner_radius=RADIUS["sm"],
                                            height=28)
        self.model_combo.pack(side="left", padx=(SPACING["xs"], SPACING["xs"]))
        add_tooltip(self.model_combo, "SAM2: cắt vật thể chính xác | rembg: xoá nền nhanh")

        self.rm_bg_btn = ctk.CTkButton(toolbar, text=" Xóa nền",
                                        command=self._remove_bg, corner_radius=RADIUS["sm"],
                                        height=32, state="disabled")
        self.rm_bg_btn.pack(side="left", padx=(0, SPACING["xs"]))
        add_tooltip(self.rm_bg_btn, "Xoá phông bằng AI (SAM2 hoặc rembg, GPU)")

        self.upscale_btn = ctk.CTkButton(toolbar, text=" Phóng to 2x",
                                          command=self._upscale, corner_radius=RADIUS["sm"],
                                          height=32, state="disabled")
        self.upscale_btn.pack(side="left", padx=(0, SPACING["xs"]))
        add_tooltip(self.upscale_btn, "Tăng gấp đôi kích thước (GPU)")

        self.enhance_btn = ctk.CTkButton(toolbar, text=" Làm nét",
                                          command=self._sharpen, corner_radius=RADIUS["sm"],
                                          height=32, state="disabled")
        self.enhance_btn.pack(side="left", padx=(0, SPACING["xs"]))
        add_tooltip(self.enhance_btn, "Tăng độ nét (GPU)")

        self.denoise_btn = ctk.CTkButton(toolbar, text=" Khử nhiễu",
                                          command=self._denoise, corner_radius=RADIUS["sm"],
                                          height=32, state="disabled")
        self.denoise_btn.pack(side="left", padx=(0, SPACING["xs"]))
        add_tooltip(self.denoise_btn, "Giảm nhiễu ảnh (GPU)")

        sep = ctk.CTkFrame(toolbar, width=1, height=24, fg_color=COLORS["border"])
        sep.pack(side="left", padx=SPACING["sm"])

        self.bg_btn = ctk.CTkButton(toolbar, image=self._img_folder, text=" Ảnh nền",
                                     command=self._select_bg, corner_radius=RADIUS["sm"],
                                     height=32, state="disabled")
        self.bg_btn.pack(side="left", padx=(0, SPACING["xs"]))
        add_tooltip(self.bg_btn, "Chọn ảnh nền để ghép với ảnh đã xoá nền")

        self.bg_label = ctk.CTkLabel(toolbar, text="", text_color=COLORS["warning"],
                                      font=("Segoe UI", 9))
        self.bg_label.pack(side="left", padx=(0, SPACING["sm"]))

        self.save_btn = ctk.CTkButton(toolbar, image=self._img_save, text=" Lưu",
                                       command=self._save_image, corner_radius=RADIUS["sm"],
                                       height=32, state="disabled")
        self.save_btn.pack(side="left", padx=(SPACING["md"], SPACING["xs"]))
        add_tooltip(self.save_btn, "Lưu ảnh đã xử lý")

        reset_btn = ctk.CTkButton(toolbar, image=self._img_delete, text=" Reset",
                                   command=self._reset, corner_radius=RADIUS["sm"],
                                   height=32, fg_color=COLORS["error"], hover_color="#DC2626")
        reset_btn.pack(side="left")
        add_tooltip(reset_btn, "Khôi phục ảnh gốc")

        self.gpu_label = ctk.CTkLabel(toolbar, text="", text_color=COLORS["success"],
                                       font=("Segoe UI", 9))
        self.gpu_label.pack(side="right", padx=(0, SPACING["sm"]))

        self.progress = ctk.CTkProgressBar(toolbar, width=200)
        self.progress_label = ctk.CTkLabel(toolbar, text="", text_color=COLORS["text_secondary"])

        self.preview_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_card"],
                                           corner_radius=RADIUS["md"],
                                           border_width=1, border_color=COLORS["border"])
        self.preview_frame.pack(fill="both", expand=True,
                                padx=SPACING["md"], pady=(0, SPACING["md"]))

        self.canvas = tk.Canvas(self.preview_frame, bg=COLORS["canvas_bg"],
                                 highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.placeholder = ctk.CTkLabel(self.canvas, text="Chưa có ảnh nào\nNhấn 'Mở ảnh' để bắt đầu",
                                         font=("Segoe UI", 14),
                                         text_color=COLORS["text_muted"])
        self.placeholder.place(relx=0.5, rely=0.5, anchor="center")

        self.canvas.bind("<Configure>", self._on_resize)

        self._update_gpu_info()

    def _update_gpu_info(self):
        info = self.editor.gpu_info()
        self.gpu_label.configure(text=info)

    def cleanup(self):
        self.editor.cleanup()

    def _open_image(self):
        path = filedialog.askopenfilename(
            title="Chọn ảnh",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.webp *.bmp"), ("All files", "*.*")]
        )
        if not path:
            return
        self._current_path = Path(path)
        self._original = self.editor.load(self._current_path)
        self._processed = None
        self._bg_path = None
        self.bg_label.configure(text="")
        self._show_image(self._original)
        for btn in (self.rm_bg_btn, self.upscale_btn, self.enhance_btn, self.denoise_btn, self.bg_btn):
            btn.configure(state="normal")
        self.save_btn.configure(state="disabled")

    def _remove_bg(self):
        if self._original is None:
            return
        model = self.model_var.get()
        if model == "SAM2":
            fn = lambda: self.editor.remove_background_sam2(self._original)
        else:
            fn = lambda: self.editor.remove_background(self._original)
        self._run_gpu_task("Xoá nền...", fn, self.rm_bg_btn)

    def _upscale(self):
        if self._original is None:
            return
        self._run_gpu_task("Phóng to...",
                           lambda: self.editor.upscale(self._original, 2.0),
                           self.upscale_btn)

    def _sharpen(self):
        target = self._processed or self._original
        if target is None:
            return
        self._run_gpu_task("Làm nét...",
                           lambda: self.editor.adjust_sharpness(target, 1.5),
                           self.enhance_btn)

    def _denoise(self):
        target = self._processed or self._original
        if target is None:
            return
        self._run_gpu_task("Khử nhiễu...",
                           lambda: self.editor.denoise(target, 0.15),
                           self.denoise_btn)

    def _select_bg(self):
        path = filedialog.askopenfilename(
            title="Chọn ảnh nền",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.webp *.bmp"), ("All files", "*.*")]
        )
        if not path:
            return
        self._bg_path = Path(path)
        self.bg_label.configure(text=f"nền: {self._bg_path.name}")
        self._merge_bg()

    def _merge_bg(self):
        fg = self._processed or self._original
        if fg is None or self._bg_path is None:
            return
        self._run_gpu_task("Ghép nền...",
                           lambda: self.editor.replace_bg_image(fg, Image.open(self._bg_path)),
                           self.bg_btn)

    def _run_gpu_task(self, label: str, fn, btn: ctk.CTkButton):
        btn.configure(state="disabled")
        self.progress_label.configure(text=label)
        self.progress.pack(side="left", padx=(SPACING["lg"], SPACING["xs"]))
        self.progress_label.pack(side="left")
        self.progress.start()

        def task():
            try:
                result = fn()
                self.after(0, lambda: self._on_task_done(result, btn))
            except Exception as e:
                self.after(0, lambda: self._on_task_error(str(e), btn))

        threading.Thread(target=task, daemon=True).start()

    def _on_task_done(self, result: Image.Image, btn: ctk.CTkButton):
        self.progress.stop()
        self.progress.pack_forget()
        self.progress_label.pack_forget()
        self._processed = result
        self._show_image(result)
        btn.configure(state="normal")
        self.save_btn.configure(state="normal")

    def _on_task_error(self, error: str, btn: ctk.CTkButton):
        self.progress.stop()
        self.progress.pack_forget()
        self.progress_label.pack_forget()
        btn.configure(state="normal")
        messagebox.showerror("Lỗi", error)

    def _save_image(self):
        if self._processed is None:
            return
        default_name = self._current_path.stem + "_edited.png" if self._current_path else "output.png"
        path = filedialog.asksaveasfilename(
            title="Lưu ảnh",
            initialfile=default_name,
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("WEBP", "*.webp")]
        )
        if not path:
            return
        try:
            img = self._processed if self._processed.mode == "RGBA" else self._processed.convert("RGBA")
            self.editor.save(img, path)
            messagebox.showinfo("Thành công", f"Đã lưu:\n{path}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lưu thất bại:\n{e}")

    def _reset(self):
        if self._original is None:
            return
        self._processed = None
        self._show_image(self._original)
        self.save_btn.configure(state="disabled")

    def _show_image(self, img: Image.Image):
        self.placeholder.place_forget()
        self._tk_image = None

        cw = self.canvas.winfo_width() or 600
        ch = self.canvas.winfo_height() or 400
        if cw < 50:
            cw = 600
        if ch < 50:
            ch = 400

        iw, ih = img.size
        scale = min(cw / iw, ch / ih, 1.5)
        new_w = int(iw * scale)
        new_h = int(ih * scale)

        display = img.resize((new_w, new_h), Image.LANCZOS)
        if display.mode == "RGBA":
            bg = Image.new("RGBA", display.size, (*self._hex_to_rgb(COLORS["canvas_bg"]), 255))
            bg.paste(display, (0, 0), display)
            display = bg
        self._tk_image = ImageTk.PhotoImage(display)

        self.canvas.delete("all")
        x = (cw - new_w) // 2
        y = (ch - new_h) // 2
        self.canvas.create_image(x, y, anchor="nw", image=self._tk_image)

    def _on_resize(self, event=None):
        img = self._processed if self._processed is not None else self._original
        if img is not None:
            self._show_image(img)

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
        h = hex_color.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
