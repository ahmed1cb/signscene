import json
import os
from pathlib import Path

from PySide6.QtCore import QStandardPaths


def _session_path() -> Path:
    base = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppConfigLocation
    )
    return Path(base) / "session.json"


def save(token: str, user: dict) -> None:
    path = _session_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"token": token, "user": user}))
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def load() -> dict | None:
    path = _session_path()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def clear() -> None:
    try:
        _session_path().unlink(missing_ok=True)
    except OSError:
        pass
