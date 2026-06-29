"""Load icons từ assets/icons/ thành PhotoImage."""

import os
from tkinter import PhotoImage

_here = os.path.dirname(os.path.abspath(__file__))
_asset_dir = os.path.join(_here, "..", "assets", "icons")


def load(name, size=None):
    path = os.path.join(_asset_dir, name)
    if not os.path.exists(path):
        return None
    if size:
        from PIL import Image, ImageTk
        img = Image.open(path).resize((size, size), Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    return PhotoImage(file=path)


class Icons:
    _cache = {}

    @classmethod
    def get(cls, name, size=24):
        key = f"{name}_{size}"
        if key not in cls._cache:
            cls._cache[key] = load(f"{name}.png", size)
        return cls._cache[key]
