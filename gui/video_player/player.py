"""Video playback: OpenCV capture, play/pause/seek, frame display."""
import cv2
import pygame
from PIL import Image, ImageTk


class VideoPlayer:
    def __init__(self, video_path, canvas):
        self.canvas = canvas
        self.cap = cv2.VideoCapture(str(video_path))

        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
        self.duration_sec = self.total_frames / self.fps if self.fps > 0 else 0

        self._vw = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
        self._vh = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 360

        self.playing = False
        self._after_id = None
        self.speed = 1.0
        self._current_sec = 0.0
        self._photo = None

        self._init_pygame()

    def _init_pygame(self):
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init(frequency=48000, size=-16, channels=2)
            except Exception:
                pass

    @property
    def current_sec(self):
        return self._current_sec

    def display_frame(self, frame):
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w = frame.shape[:2]
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 10 or ch < 10:
            return
        scale = min(cw / w, ch / h)
        nw, nh = int(w * scale), int(h * scale)
        frame = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_LINEAR)
        self._photo = ImageTk.PhotoImage(Image.fromarray(frame))
        self.canvas.delete("frame")
        x = (cw - nw) // 2
        y = (ch - nh) // 2
        self.canvas.create_image(x, y, anchor="nw", image=self._photo, tags="frame")

    def seek(self, seconds):
        if self.cap is None:
            return
        seconds = max(0, min(seconds, self.duration_sec))
        self._current_sec = seconds
        idx = int(seconds * self.fps)
        idx = max(0, min(idx, self.total_frames - 1))
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = self.cap.read()
        if ret:
            return frame
        return None

    def get_frame_at(self, seconds):
        return self.seek(seconds)

    def play(self, on_frame=None, on_finish=None):
        self.playing = True
        idx = max(0, min(int(self._current_sec * self.fps), self.total_frames - 1))
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        self._play_loop(on_frame, on_finish)

    def pause(self):
        self.playing = False
        if self._after_id:
            self.canvas.after_cancel(self._after_id)
            self._after_id = None

    def _play_loop(self, on_frame=None, on_finish=None):
        if not self.playing or self.cap is None:
            return
        ret, frame = self.cap.read()
        if not ret:
            self.pause()
            self._current_sec = self.duration_sec
            if on_finish:
                on_finish()
            return
        frame_pos = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
        seconds = (frame_pos - 1) / self.fps
        self._current_sec = seconds
        if on_frame:
            on_frame(seconds, frame)
        delay = max(16, int(round(33 / self.speed)))
        self._after_id = self.canvas.after(delay, lambda: self._play_loop(on_frame, on_finish))

    def cleanup(self):
        self.pause()
        if self._after_id:
            self.canvas.after_cancel(self._after_id)
            self._after_id = None
        if self.cap:
            self.cap.release()
            self.cap = None
        if self._photo:
            del self._photo
            self._photo = None
