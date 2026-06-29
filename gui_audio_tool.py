import os
import sys

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from gui.app import MainApp

if __name__ == "__main__":
    app = MainApp()
    app.run()
