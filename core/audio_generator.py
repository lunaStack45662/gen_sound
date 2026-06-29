import subprocess
import threading
from pathlib import Path

import imageio_ffmpeg
from vieneu import Vieneu


class AudioGenerator:
    def __init__(self):
        self._tts = Vieneu()
        self._voices = []
        self._init_voices()

    def _init_voices(self):
        try:
            raw = self._tts.list_preset_voices()
            self._voices = [(label, vid) for label, vid in raw]
        except Exception:
            self._voices = [("Ngọc Lan (mặc định)", "Ngọc Lan")]

    @property
    def voices(self):
        return list(self._voices)

    def generate(self, text, voice_name, output_path, on_done=None, on_error=None):
        output_path = Path(output_path)
        if not text.strip():
            raise ValueError("Text cannot be empty")

        thread = threading.Thread(
            target=self._generate_worker,
            args=(text, voice_name, output_path, on_done, on_error),
            daemon=True,
        )
        thread.start()
        return thread

    def _generate_worker(self, text, voice_name, output_path, on_done, on_error):
        try:
            audio = self._tts.infer(text=text, voice=voice_name)
            wav_path = output_path.with_suffix(".wav")
            self._tts.save(audio, str(wav_path))
            mp3_path = output_path.with_suffix(".mp3")
            self._wav_to_mp3(wav_path, mp3_path)
            wav_path.unlink(missing_ok=True)
            if on_done:
                on_done(str(mp3_path))
        except Exception as e:
            if on_error:
                on_error(str(e))

    def _wav_to_mp3(self, wav_path, mp3_path):
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        subprocess.run(
            [ffmpeg, "-y", "-i", str(wav_path), "-b:a", "192k", str(mp3_path)],
            capture_output=True,
            check=True,
        )
