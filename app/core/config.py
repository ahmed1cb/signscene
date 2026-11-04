"""Shared filesystem and backend location helpers."""

import os
from pathlib import Path

from PySide6.QtCore import QStandardPaths

APP_NAME = "cwb"  # Communication without Barriers

HTTP_BASE = (
    os.environ.get("CWB_API_BASE")
    or os.environ.get("CWB_BACKEND_URL")
    or "http://127.0.0.1:8080"
).rstrip("/")


def _ws_url() -> str:
    override = os.environ.get("CWB_WS_URL")
    if override:
        return override
    if HTTP_BASE.startswith("https://"):
        return "wss://" + HTTP_BASE[len("https://") :] + "/ws"
    if HTTP_BASE.startswith("http://"):
        return "ws://" + HTTP_BASE[len("http://") :] + "/ws"
    return HTTP_BASE + "/ws"


WS_URL = _ws_url()


def config_dir() -> Path:
    base = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppConfigLocation
    )
    return Path(base)


def config_path(name: str) -> Path:
    return config_dir() / name
