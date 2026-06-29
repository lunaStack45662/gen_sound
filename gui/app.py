import tkinter as tk
from tkinter import ttk

from core.audio_generator import AudioGenerator
from core.audio_player import AudioPlayer
from core.video_merger import VideoMerger
from gui.tab_gen_audio import GenAudioTab
from gui.tab_merge_audio import MergeAudioTab
from gui.tab_voice_samples import VoiceSamplesTab


class MainApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Công cụ tạo audio và ghép video")
        self.root.geometry("820x680")
        self.root.minsize(600, 500)

        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        self.player = AudioPlayer()
        self.audio_gen = AudioGenerator(root=self.root)
        self.video_merger = VideoMerger()

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=5, pady=5)

        self.tab1 = GenAudioTab(notebook, self.audio_gen, self.player)
        self.tab2 = MergeAudioTab(notebook, self.video_merger, self.player)
        self.tab3 = VoiceSamplesTab(notebook, self.audio_gen, self.player)
        notebook.add(self.tab1, text="  Tạo âm thanh  ")
        notebook.add(self.tab2, text="  Ghép vào video  ")
        notebook.add(self.tab3, text="  Nghe giọng mẫu  ")

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_quit)
        self.root.mainloop()

    def _on_quit(self):
        try:
            self.player.stop()
        except Exception:
            pass
        try:
            import pygame
            pygame.mixer.quit()
        except Exception:
            pass
        self.root.destroy()
