import tkinter as tk
from tkinter import ttk

from core.audio_generator import AudioGenerator
from core.video_merger import VideoMerger
from gui.tab_gen_audio import GenAudioTab
from gui.tab_merge_audio import MergeAudioTab


class MainApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Công cụ tạo audio và ghép video")
        self.root.geometry("780x650")
        self.root.minsize(600, 500)

        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        self.audio_gen = AudioGenerator()
        self.video_merger = VideoMerger()

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=5, pady=5)

        self.tab1 = GenAudioTab(notebook, self.audio_gen)
        self.tab2 = MergeAudioTab(notebook, self.video_merger)
        notebook.add(self.tab1, text="  Tạo âm thanh  ")
        notebook.add(self.tab2, text="  Ghép vào video  ")

    def run(self):
        self.root.mainloop()
