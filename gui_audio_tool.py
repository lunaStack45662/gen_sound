import os
import sys

os.environ["HF_TOKEN"] = "3FZ7pR81g40dVF043Rz5Uho6EPX_7LBfHH8xKxhHkM2pP45Z9"
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import customtkinter as ctk

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

from gui.app import MainApp

if __name__ == "__main__":
    app = MainApp()
    app.run()
