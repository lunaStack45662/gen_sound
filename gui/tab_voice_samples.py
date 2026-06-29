import subprocess
import tkinter as tk
from pathlib import Path
from tkinter import ttk

import imageio_ffmpeg

from core.audio_generator import AudioGenerator
from core.audio_player import AudioPlayer

SPEEDS = [("Chậm", 0.8), ("Thường", 1.0), ("Nhanh", 1.25)]

DEMO_TEXTS = {
    "Ngọc Lan": "Mời bạn lắng nghe giọng đọc dịu dàng của tôi. Công nghệ VieNeu-TTS giúp tiếng nói trở nên tự nhiên và sống động. Hy vọng bạn sẽ thích và sử dụng cho các dự án sáng tạo của mình.",
    "Trúc Ly": "[cười] Chào bạn, mình là Trúc Ly. Giọng mình trẻ trung và tươi sáng. Hãy cùng trải nghiệm công nghệ chuyển văn bản thành tiếng nói nhé!",
    "Mỹ Duyên": "Xin chào, tôi là Mỹ Duyên. Giọng đọc mượt mà, phù hợp cho các nội dung nhẹ nhàng và sâu lắng. Cảm ơn bạn đã lắng nghe.",
    "Ngọc Linh": "Chào bạn, tôi là Ngọc Linh. Giọng nói tươi sáng và năng động. Hy vọng đồng hành cùng bạn trong các dự án thú vị.",
}

DEFAULT_TEXT = (
    "Mời bạn lắng nghe giọng đọc của tôi. "
    "Đây là công nghệ chuyển văn bản thành tiếng nói do VieNeu phát triển. "
    "Hy vọng bạn sẽ thích giọng đọc này và sử dụng nó cho các dự án sáng tạo của mình. "
    "Cảm ơn bạn đã lắng nghe."
)

# Extra variants: Trúc Ly hiển thị 2 phiên bản
TRUCY_EXTRA = ("Trúc Ly (có [cười])", "Trúc Ly")


class VoiceSamplesTab(ttk.Frame):
    def __init__(self, parent, audio_gen, player: AudioPlayer):
        super().__init__(parent)
        self.audio_gen = audio_gen
        self.player = player
        self.sample_dir = Path("output/samples")
        self.sample_dir.mkdir(parents=True, exist_ok=True)
        self._playing_idx = None
        self._build_ui()
        self._check_samples()

    def _build_ui(self):
        header = ttk.Frame(self)
        header.pack(fill="x", padx=10, pady=(10, 5))
        ttk.Label(header, text="Danh sách giọng đọc mẫu", font=("", 12, "bold")).pack(
            side="left"
        )

        self.gen_btn = ttk.Button(
            header, text="Tạo tất cả file mẫu", command=self._generate_all
        )
        self.gen_btn.pack(side="right")

        self.progress = ttk.Progressbar(self, mode="determinate", length=400)
        self.progress_label = ttk.Label(self, text="")

        self.canvas = tk.Canvas(self, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.list_frame = ttk.Frame(self.canvas)
        self.list_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.create_window((0, 0), window=self.list_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

    def _build_items(self):
        items = []
        for label, vid in self.audio_gen.voices:
            text = DEMO_TEXTS.get(label, DEFAULT_TEXT)
            items.append((label, vid, text, self._slug(vid)))
        items.append(("Trúc Ly (có [cười])", "Trúc Ly",
                       DEMO_TEXTS["Trúc Ly"], "trucly_cuoi"))
        return items

    def _check_samples(self):
        self.items = self._build_items()
        all_exist = all(
            (self.sample_dir / f"{slug}.mp3").exists()
            for _, _, _, slug in self.items
        )

        if all_exist:
            self.gen_btn.pack_forget()
            self._show_list()
        else:
            self.canvas.pack_forget()
            scrollbar = getattr(self, "scrollbar", None)
            if scrollbar:
                scrollbar.pack_forget()
            self.gen_btn.config(text="Tạo tất cả file mẫu (gen 11 giọng)")
            self.gen_btn.pack(side="right")

    def _generate_all(self):
        total = len(self.items)
        self.gen_btn.config(state="disabled", text="Đang gen...")
        self.progress_label.pack(pady=(0, 5))
        self.progress.pack(fill="x", padx=10, pady=(0, 10))
        self.progress["maximum"] = total
        self.progress["value"] = 0
        self._gen_queue = list(self.items)
        self._gen_next()

    def _gen_next(self):
        if not self._gen_queue:
            self.progress.pack_forget()
            self.progress_label.pack_forget()
            self._check_samples()
            return
        label, vid, text, slug = self._gen_queue.pop(0)
        path = self.sample_dir / f"{slug}.mp3"

        def on_done(p):
            self.progress["value"] += 1
            self.progress_label.config(
                text=f"Đã gen {int(self.progress['value'])}/{len(self.items)}"
            )
            self._gen_next()

        def on_error(err):
            self.progress["value"] += 1
            self.progress_label.config(
                text=f"Lỗi: {err[:50]}...  ({int(self.progress['value'])}/{len(self.items)})"
            )
            self._gen_next()

        self.audio_gen.generate(
            text=text, voice_name=vid, output_path=path,
            on_done=on_done, on_error=on_error,
        )

    def _show_list(self):
        for w in self.list_frame.winfo_children():
            w.destroy()

        headers = ["", "Giọng", "Mô tả", "Chậm (0.8x)", "▶ Thường", "Nhanh (1.25x)"]
        for col, h in enumerate(headers):
            lbl = ttk.Label(self.list_frame, text=h, font=("", 9, "bold"))
            lbl.grid(row=0, column=col, sticky="w", padx=(4, 4), pady=2)

        self.rows = []
        for i, (label, vid, text, slug) in enumerate(self.items):
            path = self.sample_dir / f"{slug}.mp3"
            dur = self._get_duration(path) if path.exists() else 0
            desc = self._get_desc(vid)
            display_label = label

            ttk.Label(self.list_frame, text="♫").grid(
                row=i + 1, column=0, padx=(4, 0), pady=3
            )
            ttk.Label(self.list_frame, text=display_label, width=22, anchor="w").grid(
                row=i + 1, column=1, sticky="w", padx=(4, 0)
            )
            ttk.Label(self.list_frame, text=desc, width=24, anchor="w").grid(
                row=i + 1, column=2, sticky="w", padx=(4, 0)
            )

            btns = {}
            for si, (sp_label, sp_factor) in enumerate(SPEEDS):
                def make_handler(idx=i, p=path, sf=sp_factor, sid=si):
                    return lambda: self._play_speed(idx, p, sf, sid)

                btn = ttk.Button(
                    self.list_frame, text="▶", width=3,
                    command=make_handler(),
                )
                btn.grid(row=i + 1, column=3 + si, padx=(2, 2))
                btns[si] = btn

            self.rows.append({
                "path": path, "dur": dur, "btns": btns,
                "playing_speed": None,
            })

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar = ttk.Scrollbar(
            self, orient="vertical", command=self.canvas.yview
        )
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

    def _play_speed(self, idx, orig_path, speed_factor, speed_idx):
        if self.rows[idx].get("playing_speed") == speed_idx:
            self.player.stop()
            self.rows[idx]["btns"][speed_idx].config(text="▶")
            self.rows[idx]["playing_speed"] = None
            return

        self.player.stop()
        for ri in self.rows:
            for si, b in ri["btns"].items():
                b.config(text="▶")
            ri["playing_speed"] = None

        if speed_factor == 1.0:
            play_path = orig_path
        else:
            label = SPEEDS[speed_idx][0].lower()
            stem = Path(orig_path).stem
            cached = Path(orig_path).parent / ".cache" / f"{stem}_{label}.mp3"
            cached.parent.mkdir(parents=True, exist_ok=True)
            if not cached.exists():
                AudioGenerator.adjust_speed(orig_path, speed_factor, cached)
            play_path = cached

        def on_finish():
            self.rows[idx]["btns"][speed_idx].config(text="▶")
            self.rows[idx]["playing_speed"] = None

        self.player.play(play_path, on_finish=on_finish)
        self.rows[idx]["btns"][speed_idx].config(text="⏹")
        self.rows[idx]["playing_speed"] = speed_idx

    def _slug(self, text):
        import re
        s = text.lower().replace("đ", "d")
        s = re.sub(r"[^a-z0-9]", "_", s)
        s = re.sub(r"_+", "_", s).strip("_")
        return s or "voice"

    def _get_duration(self, path):
        try:
            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
            r = subprocess.run(
                [ffmpeg, "-i", str(path), "-hide_banner"],
                capture_output=True, text=True,
            )
            for line in r.stderr.splitlines():
                if "Duration:" in line:
                    t = line.split("Duration:")[1].split(",")[0].strip()
                    h, m, s = t.split(":")
                    return int(h) * 3600 + int(m) * 60 + float(s)
        except Exception:
            pass
        return 0.0

    def _get_desc(self, voice_id):
        desc_map = {
            "Ngọc Lan": "nữ, giọng dịu dàng",
            "Gia Bảo": "nam, giọng mượt mà",
            "Thái Sơn": "nam, giọng chắc khỏe",
            "Đức Trí": "nam, giọng rõ ràng",
            "Mỹ Duyên": "nữ, giọng mượt mà",
            "Trúc Ly": "nữ, giọng trẻ trung",
            "Xuân Vĩnh": "nam, giọng vui tươi",
            "Trọng Hữu": "nam, giọng uyên bác",
            "Bình An": "nam, giọng điềm đạm",
            "Ngọc Linh": "nữ, giọng tươi sáng",
        }
        return desc_map.get(voice_id, "")
