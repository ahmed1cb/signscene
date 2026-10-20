import json
import os
from pathlib import Path

from PySide6.QtCore import QStandardPaths

DEFAULTS = {
    "voice_id": None,
    "voice_name": None,
    "rate": 100,
    "volume": 1.0,
}


def _settings_path() -> Path:
    base = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppConfigLocation
    )
    return Path(base) / "settings.json"


def load() -> dict:
    path = _settings_path()
    if not path.exists():
        return dict(DEFAULTS)
    try:
        data = json.loads(path.read_text())
    except Exception:
        return dict(DEFAULTS)
    if not isinstance(data, dict):
        return dict(DEFAULTS)
    merged = dict(DEFAULTS)
    merged.update({k: data[k] for k in DEFAULTS if k in data})
    return merged


def save(settings: dict) -> None:
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({k: settings.get(k, DEFAULTS[k]) for k in DEFAULTS}))
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
