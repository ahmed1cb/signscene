import base64
import io
import json
import os
import queue
import re
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QThread, Signal

# ARASAAC pictograms: CC BY-NC-SA (attribution required, non-commercial only).
# Pictograms: ARASAAC (https://arasaac.org), Government of Aragon, author Sergio Palao.
SEARCH_URL = "https://api.arasaac.org/v1/pictograms/{lang}/bestsearch/{term}"
IMAGE_URL = "https://static.arasaac.org/pictograms/{pid}/{pid}_500.png"

LANG = os.environ.get("SIGNSCENE_ARASAAC_LANG", "en")
MAX_PICTOS = 6
TIMEOUT = 10
CACHE_DIR = Path.home() / ".cache" / "signscene" / "arasaac"

# Words that rarely have a useful pictogram (English). Edit as needed.
STOPWORDS = {
    "a",
    "an",
    "the",
    "is",
    "are",
    "am",
    "be",
    "to",
    "of",
    "and",
    "or",
    "it",
    "this",
    "that",
    "in",
    "on",
    "at",
    "for",
    "with",
}


def _http_get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "signscene/1.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read()


class SceneWorker(QThread):
    scene_ready = Signal(str, str)
    scene_failed = Signal(str, str)
    status_changed = Signal(str)
    model_loaded = Signal(bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._queue = queue.Queue()
        self._stop_event = threading.Event()
        self._id_cache: dict[str, int | None] = {}

    def generate(self, sentence: str):
        if not sentence:
            return
        self._queue.put(sentence.strip())

    def stop(self):
        self._stop_event.set()
        try:
            self._queue.put_nowait("")
        except Exception:
            pass

    # ---------- ARASAAC ----------
    def _search_id(self, term: str) -> int | None:
        if term in self._id_cache:
            return self._id_cache[term]
        url = SEARCH_URL.format(lang=LANG, term=urllib.parse.quote(term))
        pid = None
        try:
            data = json.loads(_http_get(url).decode("utf-8"))
            if isinstance(data, list) and data:
                pid = int(data[0]["_id"])
        except urllib.error.HTTPError as e:
            if e.code != 404:  # 404 = no result for this word
                raise
        self._id_cache[term] = pid
        return pid

    def _fetch_image(self, pid: int) -> Image.Image:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path = CACHE_DIR / f"{pid}.png"
        if path.exists() and path.stat().st_size > 0:
            raw = path.read_bytes()
        else:
            raw = _http_get(IMAGE_URL.format(pid=pid))
            path.write_bytes(raw)
        return Image.open(io.BytesIO(raw)).convert("RGBA")

    @staticmethod
    def _compose(images: list[Image.Image]) -> Image.Image:
        n = len(images)
        cols = min(n, 3)
        rows = (n + cols - 1) // cols
        tile = 512 if n == 1 else 256
        canvas = Image.new("RGB", (cols * tile, rows * tile), "white")
        for i, img in enumerate(images):
            img = img.resize((tile, tile), Image.LANCZOS)
            x, y = (i % cols) * tile, (i // cols) * tile
            canvas.paste(img, (x, y), img)  # alpha mask keeps white background
        return canvas

    @staticmethod
    def _words(sentence: str) -> list[str]:
        seen, out = set(), []
        for w in re.findall(r"[^\W\d_]+", sentence.lower()):
            if w in STOPWORDS or w in seen:
                continue
            seen.add(w)
            out.append(w)
        return out

    def _build_scene(self, sentence: str) -> Image.Image:
        images = []
        for word in self._words(sentence):
            if self._stop_event.is_set():
                break
            pid = self._search_id(word)
            if pid is None:
                continue
            images.append(self._fetch_image(pid))
            if len(images) >= MAX_PICTOS:
                break
        if not images:
            raise LookupError("No pictograms found for this sentence")
        return self._compose(images)

    # ---------- thread ----------
    def run(self):
        self.model_loaded.emit(True, "ARASAAC")
        self.status_changed.emit("Scene ready (ARASAAC)")

        while not self._stop_event.is_set():
            try:
                sentence = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            if sentence == "" or self._stop_event.is_set():
                break

            try:
                self.status_changed.emit("Generating scene...")
                image = self._build_scene(sentence)

                buf = io.BytesIO()
                image.save(buf, format="JPEG", quality=88)
                b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
                self.scene_ready.emit(sentence, f"data:image/jpeg;base64,{b64}")
                self.status_changed.emit("Scene ready")
            except Exception as e:
                self.scene_failed.emit(sentence, str(e))
                self.status_changed.emit(f"Scene failed: {e}")
