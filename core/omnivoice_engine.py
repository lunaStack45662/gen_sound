import subprocess
import threading
from pathlib import Path

import imageio_ffmpeg
import numpy as np
import soundfile as sf


class OmniVoiceEngine:
    def __init__(self, root=None):
        self._root = root
        self._model = None
        self._voices = [("OmniVoice (zero-shot)", "default")]
        self._load_model()

    def _load_model(self):
        from omnivoice import OmniVoice
        import torch
        self._model = OmniVoice.from_pretrained(
            "k2-fsa/OmniVoice",
            device_map="cuda:0",
            dtype=torch.float16,
        )

    @property
    def name(self):
        return "OmniVoice"

    @property
    def voices(self):
        return list(self._voices)

    def generate(self, text, voice_name, output_path,
                 ref_audio=None, on_done=None, on_error=None):
        output_path = Path(output_path)
        if not text.strip():
            raise ValueError("Text cannot be empty")

        thread = threading.Thread(
            target=self._generate_worker,
            args=(text, output_path, ref_audio, on_done, on_error),
            daemon=True,
        )
        thread.start()
        return thread

    def _generate_worker(self, text, output_path, ref_audio,
                         on_done, on_error):
        try:
            kwargs = dict(text=text)
            if ref_audio:
                kwargs["ref_audio"] = str(ref_audio)

            audio_list = self._model.generate(**kwargs)
            audio = audio_list[0]

            wav_path = output_path.with_suffix(".wav")
            sf.write(str(wav_path), audio, 24000)
            mp3_path = output_path.with_suffix(".mp3")
            self._wav_to_mp3(wav_path, mp3_path)
            wav_path.unlink(missing_ok=True)

            if on_done and self._root:
                self._root.after(0, on_done, str(mp3_path))
            elif on_done:
                on_done(str(mp3_path))
        except Exception as e:
            if on_error and self._root:
                self._root.after(0, on_error, str(e))
            elif on_error:
                on_error(str(e))

    def _wav_to_mp3(self, wav_path, mp3_path):
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        subprocess.run(
            [ffmpeg, "-y", "-i", str(wav_path), "-b:a", "192k", str(mp3_path)],
            capture_output=True,
            check=True,
        )

    @staticmethod
    def adjust_speed(input_path, speed_factor, output_path):
        input_path = Path(input_path)
        output_path = Path(output_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Khong tim thay: {input_path}")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        subprocess.run(
            [ffmpeg, "-y", "-i", str(input_path),
             "-filter:a", f"atempo={speed_factor}",
             "-b:a", "192k", str(output_path)],
            capture_output=True, check=True,
        )
        return output_path
