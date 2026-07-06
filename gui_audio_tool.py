import json
import os
import sys
from pathlib import Path

config_path = Path(__file__).parent / "config.json"
cfg = {}
if config_path.exists():
    with open(config_path, encoding="utf-8") as f:
        cfg = json.load(f)

hf_token = cfg.get("HF_TOKEN", "")
if hf_token:
    os.environ["HF_TOKEN"] = hf_token

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS", cfg.get("HF_HUB_DISABLE_SYMLINKS", "1"))
os.environ.setdefault("TOKENIZERS_PARALLELISM", cfg.get("TOKENIZERS_PARALLELISM", "false"))

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import customtkinter as ctk

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

from gui.app import MainApp

if __name__ == "__main__":
    app = MainApp()
    app.run()
