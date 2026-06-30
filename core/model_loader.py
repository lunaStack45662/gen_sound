import gc
import threading
from pathlib import Path


class ModelLoader:
    def __init__(self, root=None):
        self._root = root
        self._engines = {}
        self._current_name = None
        self._lock = threading.Lock()

    def register(self, name, factory):
        self._engines[name] = {"factory": factory, "instance": None}

    @property
    def available_engines(self):
        return list(self._engines.keys())

    @property
    def current_name(self):
        return self._current_name

    def get_engine(self, name):
        if name not in self._engines:
            raise ValueError(f"Unknown engine: {name}")

        with self._lock:
            entry = self._engines[name]
            if entry["instance"] is None:
                entry["instance"] = entry["factory"]()
            return entry["instance"]

    def switch(self, name):
        if name not in self._engines:
            raise ValueError(f"Unknown engine: {name}")

        if name == self._current_name:
            return self.get_engine(name)

        with self._lock:
            old_name = self._current_name
            if old_name is not None and old_name in self._engines:
                old_entry = self._engines[old_name]
                if old_entry["instance"] is not None:
                    old_entry["instance"] = None

            self._current_name = name
            entry = self._engines[name]
            if entry["instance"] is None:
                entry["instance"] = entry["factory"]()

        gc.collect()

        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        return entry["instance"]

    def cleanup(self):
        with self._lock:
            for entry in self._engines.values():
                entry["instance"] = None
        gc.collect()
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
