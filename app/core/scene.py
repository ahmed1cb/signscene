import queue
import threading

from PySide6.QtCore import QThread, Signal

from core import scene_api


class SceneWorker(QThread):
    scene_ready = Signal(str, str)
    scene_failed = Signal(str, str)
    status_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._queue: queue.Queue[tuple[str, str] | None] = queue.Queue()
        self._stop_event = threading.Event()

    def generate(self, sentence: str, token: str):
        if not sentence:
            return
        self._queue.put((sentence.strip(), token))

    def stop(self):
        self._stop_event.set()
        try:
            self._queue.put_nowait(None)
        except Exception:
            pass

    def run(self):
        while not self._stop_event.is_set():
            try:
                item = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if item is None or self._stop_event.is_set():
                break

            sentence, token = item
            try:
                self.status_changed.emit("Generating scene...")
                result = scene_api.generate_scene(sentence, token)
                self.scene_ready.emit(sentence, result["scene"])
                self.status_changed.emit("Scene ready")
            except Exception as exc:
                self.scene_failed.emit(sentence, str(exc))
                self.status_changed.emit(f"Scene failed: {exc}")
