import queue
import threading

import pyttsx3

from core import settings
from core.message import Message

_current: dict = dict(settings.DEFAULTS)
_tasks: "queue.Queue" = queue.Queue()
_thread: threading.Thread | None = None
_lock = threading.Lock()
_ready = threading.Event()
_voices_cache: list[tuple[str, str]] = []


def _worker():
    engine = pyttsx3.init()
    engine.setProperty("rate", int(_current["rate"]))
    engine.setProperty("volume", float(_current["volume"]))
    _voices_cache[:] = [
        (str(v.id), v.name) for v in (engine.getProperty("voices") or [])
    ]
    _ready.set()
    while True:
        task = _tasks.get()
        if task is None:
            break
        kind, value = task
        try:
            if kind == "say":
                engine.say(value)
                engine.runAndWait()
            else:  # إعداد: (اسم الخاصية، القيمة)
                engine.setProperty(kind, value)
        except Exception:
            pass


def _start():
    global _thread
    with _lock:
        if _thread is None or not _thread.is_alive():
            _ready.clear()
            _thread = threading.Thread(target=_worker, daemon=True)
            _thread.start()


def _set(prop: str, value) -> None:
    _start()
    _tasks.put((prop, value))


def list_voices() -> list[tuple[str, str]]:
    _start()
    _ready.wait()
    return list(_voices_cache)


def _resolve_voice_id(voice_id, voice_name) -> str | None:
    voices = list_voices()
    if voice_id is not None:
        for vid, _ in voices:
            if vid == str(voice_id):
                return vid
    if voice_name:
        for vid, name in voices:
            if name == voice_name:
                return vid
    return None


def apply_saved() -> None:
    global _current
    _current = settings.load()
    _set("rate", int(_current["rate"]))
    _set("volume", float(_current["volume"]))
    voice_id = _resolve_voice_id(_current.get("voice_id"), _current.get("voice_name"))
    if voice_id is not None:
        _set("voice", voice_id)
        _current["voice_id"] = voice_id


def _persist() -> None:
    settings.save(_current)


def set_voice(voice_id: str, voice_name: str | None = None) -> None:
    _set("voice", voice_id)
    _current["voice_id"] = str(voice_id)
    if voice_name is None:
        voice_name = next((n for i, n in list_voices() if i == str(voice_id)), None)
    if voice_name is not None:
        _current["voice_name"] = voice_name
    _persist()


def set_rate(rate: int) -> None:
    _current["rate"] = int(rate)
    _set("rate", int(rate))
    _persist()


def set_volume(volume: float) -> None:
    _current["volume"] = float(volume)
    _set("volume", float(volume))
    _persist()


def current() -> dict:
    return dict(_current)


class Speaker:
    @staticmethod
    def say(msg: Message):
        if msg.type == "txt":
            _start()
            _tasks.put(("say", msg.content))
