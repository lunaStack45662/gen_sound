import threading
import time
from pathlib import Path

import pygame.mixer


class AudioPlayer:
    def __init__(self):
        try:
            pygame.mixer.init(frequency=48000, size=-16, channels=2, buffer=1024)
            self._available = True
        except Exception:
            self._available = False

    @property
    def available(self):
        return self._available

    def play(self, path, on_finish=None):
        if not self._available:
            return
        self.stop()
        path = Path(path)
        if not path.exists():
            return
        pygame.mixer.music.load(str(path))
        pygame.mixer.music.play()
        if on_finish:
            self._monitor(on_finish)

    def stop(self):
        if self._available and self.is_playing:
            pygame.mixer.music.fadeout(100)

    @property
    def is_playing(self):
        if not self._available:
            return False
        return pygame.mixer.music.get_busy()

    def _monitor(self, callback):
        def _run():
            while self.is_playing:
                time.sleep(0.1)
            try:
                import tkinter as tk
                root = tk._default_root
                if root:
                    root.after(0, callback)
            except Exception:
                pass
        threading.Thread(target=_run, daemon=True).start()
