import customtkinter as ctk

from core.audio_generator import AudioGenerator
from core.audio_player import AudioPlayer
from core.omnivoice_engine import OmniVoiceEngine
from core.model_loader import ModelLoader
from core.video_merger import VideoMerger
from gui.tab_gen_audio import GenAudioTab
from gui.tab_merge_audio import MergeAudioTab
from gui.tab_voice_samples import VoiceSamplesTab


class MainApp:
    def __init__(self):
        self.root = ctk.CTk()
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
        self.video_merger = VideoMerger()

        self.model_loader = ModelLoader(root=self.root)
        self.model_loader.register("Vieneu", lambda: AudioGenerator(root=self.root))
        self.model_loader.register("OmniVoice", lambda: OmniVoiceEngine(root=self.root))

        tabs = ctk.CTkTabview(self.root, corner_radius=8)
        tabs.pack(fill="both", expand=True, padx=8, pady=8)

        tab1 = tabs.add("  Tạo âm thanh  ")
        tab2 = tabs.add("  Ghép vào video  ")
        tab3 = tabs.add("  Nghe giọng mẫu  ")

        self.tab1 = GenAudioTab(tab1, self.model_loader, self.player)
        self.tab2 = MergeAudioTab(tab2, self.video_merger, self.player)
        self.tab3 = VoiceSamplesTab(tab3, self.model_loader, self.player)

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_quit)
        self.root.mainloop()

    def _on_quit(self):
        try:
            self.player.stop()
        except Exception:
            pass
        try:
            self.model_loader.cleanup()
        except Exception:
            pass
        try:
            import pygame
            pygame.mixer.quit()
        except Exception:
            pass
        self.root.destroy()
