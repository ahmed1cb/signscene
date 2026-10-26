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
_disabled = False


def _resolve_voice(voice_id, voice_name) -> str | None:
    if voice_id is not None:
        for vid, _ in _voices_cache:
            if vid == str(voice_id):
                return vid
    if voice_name:
        for vid, name in _voices_cache:
            if name == voice_name:
                return vid
    return None


def _worker():
    global _disabled
    try:
        engine = pyttsx3.init()
    except Exception:
        _disabled = True
        _ready.set()
        return

    try:
        engine.setProperty("rate", int(_current["rate"]))
        engine.setProperty("volume", float(_current["volume"]))
        _voices_cache[:] = [
            (str(v.id), v.name) for v in (engine.getProperty("voices") or [])
        ]
        voice_id = _resolve_voice(
            _current.get("voice_id"), _current.get("voice_name")
        )
        if voice_id is not None:
            engine.setProperty("voice", voice_id)
    except Exception:
        pass
    finally:
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
            elif kind == "voice":
                voice_id = _resolve_voice(*value)
                if voice_id is not None:
                    engine.setProperty("voice", voice_id)
            else:
                engine.setProperty(kind, value)
        except Exception:
            pass


def _start():
    global _thread
    if _disabled:
        return
    with _lock:
        if _thread is None or not _thread.is_alive():
            _ready.clear()
            _thread = threading.Thread(target=_worker, daemon=True)
            _thread.start()


def _set(prop: str, value) -> None:
    if _disabled:
        return
    _start()
    _tasks.put((prop, value))


def list_voices(wait_timeout: float = 2.0) -> list[tuple[str, str]]:
    _start()
    _ready.wait(wait_timeout)
    return list(_voices_cache)


def apply_saved() -> None:
    global _current
    _current = settings.load()
    with _lock:
        running = _thread is not None and _thread.is_alive()
    if not running:
        return
    _set("rate", int(_current["rate"]))
    _set("volume", float(_current["volume"]))
    _set("voice", (_current.get("voice_id"), _current.get("voice_name")))


class Speaker:
    @staticmethod
    def say(msg: Message):
        if msg.type == "txt" and not _disabled:
            _start()
            _tasks.put(("say", msg.content))
