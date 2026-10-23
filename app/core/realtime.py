import json
import os

from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtNetwork import QAbstractSocket
from PySide6.QtWebSockets import QWebSocket

WS_URL = os.environ.get("SIGNSCENE_WS_URL", "ws://127.0.0.1:8080/ws")
CLOSE_REPLACED = 4001
CLOSE_UNAUTHORIZED = 4003


class RealtimeClient(QObject):
    ready = Signal(dict)
    ringing = Signal(dict)
    incoming = Signal(dict)
    accepted = Signal(dict)
    rejected = Signal(dict)
    ended = Signal(dict)
    content = Signal(dict)
    error = Signal(str, str)
    connection_changed = Signal(bool)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._socket = QWebSocket()
        self._socket.setParent(self)
        self._socket.connected.connect(self._on_connected)
        self._socket.disconnected.connect(self._on_disconnected)
        self._socket.textMessageReceived.connect(self._on_text)
        self._socket.errorOccurred.connect(self._on_error)

        self._token: str | None = None
        self._ready = False
        self._manual_close = False
        self._attempt = 0

        self._reconnect_timer = QTimer(self)
        self._reconnect_timer.setSingleShot(True)
        self._reconnect_timer.timeout.connect(self._open)

    @property
    def is_ready(self) -> bool:
        return self._ready

    def connect(self, token: str) -> None:
        self._token = token
        self._manual_close = False
        self._attempt = 0
        self._ready = False
        if self._socket.state() == QAbstractSocket.SocketState.UnconnectedState:
            self._open()

    def close(self) -> None:
        self._manual_close = True
        self._reconnect_timer.stop()
        self._ready = False
        if self._socket.state() != QAbstractSocket.SocketState.UnconnectedState:
            self._socket.close()

    def start_call(self, com_id: str) -> bool:
        return self._send({"type": "call.start", "to": com_id})

    def accept_call(self, call_id: str) -> bool:
        return self._send({"type": "call.accept", "call_id": call_id})

    def reject_call(self, call_id: str) -> bool:
        return self._send({"type": "call.reject", "call_id": call_id})

    def end_call(self, call_id: str) -> bool:
        return self._send({"type": "call.end", "call_id": call_id})

    def send_text(self, call_id: str, text: str) -> bool:
        return self._send(
            {
                "type": "content.send",
                "call_id": call_id,
                "kind": "text",
                "content": text,
            }
        )

    def send_scene(self, call_id: str, scene: str) -> bool:
        return self._send(
            {
                "type": "content.send",
                "call_id": call_id,
                "kind": "scene",
                "content": scene,
            }
        )

    def _open(self) -> None:
        if not self._token or self._manual_close:
            return
        self._socket.open(QUrl(WS_URL))

    def _send(self, payload: dict) -> bool:
        if self._socket.state() != QAbstractSocket.SocketState.ConnectedState:
            return False
        self._socket.sendTextMessage(json.dumps(payload))
        return True

    def _on_connected(self) -> None:
        self._attempt = 0
        if not self._token:
            return
        self._send({"type": "auth", "token": self._token})

    def _on_disconnected(self) -> None:
        self._ready = False
        self.connection_changed.emit(False)

        code = self._socket.closeCode()
        if code == CLOSE_REPLACED:
            self._manual_close = True
            self.error.emit(
                "session_replaced",
                "This account connected from another device",
            )
        elif code == CLOSE_UNAUTHORIZED:
            self._manual_close = True
            self.error.emit("unauthorized", "Realtime authentication failed")

        if not self._manual_close:
            self._schedule_reconnect()

    def _on_error(self, _error) -> None:
        if not self._manual_close:
            self.error.emit("socket", self._socket.errorString())

    def _on_text(self, raw: str) -> None:
        try:
            payload = json.loads(raw)
        except (TypeError, ValueError):
            self.error.emit("invalid_message", "Received an invalid server message")
            return

        message_type = payload.get("type")
        if message_type == "ready":
            self._ready = True
            self.connection_changed.emit(True)
            self.ready.emit(payload)
        elif message_type == "call.ringing":
            self.ringing.emit(payload)
        elif message_type == "call.incoming":
            self.incoming.emit(payload)
        elif message_type == "call.accepted":
            self.accepted.emit(payload)
        elif message_type == "call.rejected":
            self.rejected.emit(payload)
        elif message_type == "call.ended":
            self.ended.emit(payload)
        elif message_type == "content":
            self.content.emit(payload)
        elif message_type == "error":
            self.error.emit(
                str(payload.get("code", "error")),
                str(payload.get("message", "Realtime error")),
            )

    def _schedule_reconnect(self) -> None:
        delay = min(15_000, 1_000 * (2**self._attempt))
        self._attempt += 1
        self._reconnect_timer.start(delay)
