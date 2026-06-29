"""Load icons từ assets/icons/ thành CTkImage."""

import os

from PIL import Image

_here = os.path.dirname(os.path.abspath(__file__))
_asset_dir = os.path.join(_here, "..", "assets", "icons")


def _load_ctk_image(name, size):
    path = os.path.join(_asset_dir, name)
    if not os.path.exists(path):
        return None
    img = Image.open(path).resize((size, size), Image.LANCZOS)
    from customtkinter import CTkImage
    return CTkImage(img, size=(size, size))


class Icons:
    _cache = {}

    @classmethod
    def get(cls, name, size=24):
        key = f"{name}_{size}"
        if key not in cls._cache:
            cls._cache[key] = _load_ctk_image(f"{name}.png", size)
        return cls._cache[key]
