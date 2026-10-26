import re

import numpy as np
from core import speaker
from core.asl.templates import TemplateStore
from core.camera import CameraWorker
from core.message import Message
from core.realtime import RealtimeClient
from core.scene import SceneWorker
from core.speaker import Speaker
from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QImage, QPixmap, QResizeEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ui.screens.teach_dialog import TeachDialog
from ui.widgets.message_panel import MessagesArea

COM_ID_PATTERN = re.compile(r"^[A-Z][A-Z0-9]{1,10}-\d{4}$")


class VideoLabel(QLabel):
    """QLabel with fixed layout hints so placeholder text/pixmap never resizes it."""

    def sizeHint(self) -> QSize:
        return QSize(480, 360)

    def minimumSizeHint(self) -> QSize:
        return QSize(320, 240)


class HomeScreen(QWidget):
    def __init__(self, on_sign_out, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._on_sign_out = on_sign_out
        self._camera_worker: CameraWorker | None = None
        self._last_frame: np.ndarray | None = None
        self._templates = TemplateStore()
        self._recording_word: str | None = None
        self._realtime: RealtimeClient | None = None
        self._call_state = "idle"  # idle | outgoing | incoming | active
        self._call_id: str | None = None
        self._last_sentence: str = ""
        self._composing = False
        self._scene_generating = False
        self._last_scene: str = ""
        self._scene_sent = False
        self._token: str | None = None
        self._scene_worker: SceneWorker | None = None
        speaker.apply_saved()
        self._build_ui()
        self._update_scene_send_button()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(14)

        root.addLayout(self._build_top_bar())
        root.addLayout(self._build_call_bar())
        root.addWidget(self._build_incoming_bar())
        root.addLayout(self._build_main_area(), stretch=1)

    # ---------- top bar ----------
    def _build_top_bar(self) -> QHBoxLayout:
        bar = QHBoxLayout()

        self.status_dot = QLabel("●")
        self.status_dot.setObjectName("StatusDot")
        self.own_id = QLabel("")
        self.own_id.setObjectName("Hint")

        self.name = QLabel("")
        self.name.setObjectName("Hint")

        identity = QHBoxLayout()
        identity.setSpacing(6)
        identity.addWidget(self.status_dot)
        identity.addWidget(self.own_id)
        identity.addWidget(self.name)

        self.teach_button = QPushButton("Teach signs")
        self.teach_button.setObjectName("GhostButton")
        self.teach_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.teach_button.setFixedWidth(120)
        self.teach_button.clicked.connect(self._show_teach)

        sign_out = QPushButton("Sign out")
        sign_out.setObjectName("GhostButton")
        sign_out.setCursor(Qt.CursorShape.PointingHandCursor)
        sign_out.setFixedWidth(110)
        sign_out.clicked.connect(self._on_sign_out)

        bar.addLayout(identity)
        bar.addStretch(1)
        bar.addWidget(self.teach_button)
        bar.addSpacing(8)
        bar.addWidget(sign_out)
        return bar

    # ---------- call bar ----------
    def _build_call_bar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.setSpacing(10)

        self.peer_edit = QLineEdit()
        self.peer_edit.setPlaceholderText("Enter com_id to call — e.g. JOHN-7290")
        self.peer_edit.setMinimumHeight(42)
        self.peer_edit.setMaxLength(16)
        self.peer_edit.textChanged.connect(self._on_peer_changed)
        self.peer_edit.returnPressed.connect(self._try_call)

        self.call_button = QPushButton("Connect")
        self.call_button.setMinimumHeight(42)
        self.call_button.setMinimumWidth(110)
        self.call_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.call_button.setEnabled(False)
        self.call_button.clicked.connect(self._try_call)

        self.call_status = QLabel("")
        self.call_status.setObjectName("Hint")

        bar.addWidget(self.peer_edit, 1)
        bar.addWidget(self.call_button)
        bar.addWidget(self.call_status)
        return bar

    def _build_incoming_bar(self) -> QFrame:
        self.incoming_bar = QFrame()
        self.incoming_bar.setObjectName("IncomingCallBar")

        layout = QHBoxLayout(self.incoming_bar)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(10)

        self.incoming_label = QLabel("")
        self.incoming_label.setObjectName("IncomingCallLabel")
        self.incoming_label.setWordWrap(True)

        accept = QPushButton("Accept")
        accept.setCursor(Qt.CursorShape.PointingHandCursor)
        accept.setFixedWidth(100)
        accept.clicked.connect(self._accept_incoming)

        reject = QPushButton("Reject")
        reject.setObjectName("DangerButton")
        reject.setCursor(Qt.CursorShape.PointingHandCursor)
        reject.setFixedWidth(100)
        reject.clicked.connect(self._reject_incoming)

        layout.addWidget(self.incoming_label, 1)
        layout.addWidget(accept)
        layout.addWidget(reject)

        self.incoming_bar.hide()
        return self.incoming_bar

    # ---------- camera + side panels ----------
    def _build_main_area(self) -> QHBoxLayout:
        area = QHBoxLayout()
        area.setSpacing(14)

        camera_card = QFrame()
        camera_card.setObjectName("Card")
        camera_layout = QVBoxLayout(camera_card)
        camera_layout.setContentsMargins(10, 10, 10, 10)
        camera_layout.setSpacing(12)

        camera_title = QLabel("Camera")
        camera_title.setObjectName("Subtitle")

        self.camera_video = VideoLabel()
        self.camera_video.setObjectName("CameraVideo")
        self.camera_video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_video.setText("Camera feed will appear here")

        self.gesture_label = QLabel("")
        self.gesture_label.setObjectName("GestureLabel")
        self.gesture_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.composing_label = QLabel("—")
        self.composing_label.setObjectName("ComposingLabel")
        self.composing_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.composing_label.setWordWrap(True)

        self.camera_hud = QLabel("Hand tracking is off")
        self.camera_hud.setObjectName("CameraHud")
        self.camera_hud.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.scene_status = QLabel("")
        self.scene_status.setObjectName("Hint")
        self.scene_status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.fps_label = QLabel("")
        self.fps_label.setObjectName("CameraHud")

        status_row = QHBoxLayout()
        status_row.setSpacing(10)
        status_row.addWidget(self.camera_hud)
        status_row.addWidget(self.scene_status)
        status_row.addStretch(1)
        status_row.addWidget(self.fps_label)

        self.camera_button = QPushButton("Open Camera")
        self.camera_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.camera_button.setFixedWidth(160)
        self.camera_button.clicked.connect(self._open_camera)

        self.clear_button = QPushButton("Clear")
        self.clear_button.setObjectName("GhostButton")
        self.clear_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_button.setFixedWidth(90)
        self.clear_button.setEnabled(False)
        self.clear_button.clicked.connect(self._clear_composing)

        self.gen_scene_btn = QPushButton("Generate Scene")
        self.gen_scene_btn.setObjectName("GhostButton")
        self.gen_scene_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.gen_scene_btn.setFixedWidth(150)
        self.gen_scene_btn.setEnabled(False)
        self.gen_scene_btn.clicked.connect(self._generate_scene)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        button_row.addWidget(self.camera_button)
        button_row.addWidget(self.clear_button)
        button_row.addWidget(self.gen_scene_btn)
        button_row.addStretch(1)

        camera_layout.addWidget(camera_title, alignment=Qt.AlignmentFlag.AlignLeft)
        camera_layout.addWidget(self.camera_video, stretch=1)
        camera_layout.addWidget(self.gesture_label)
        camera_layout.addWidget(self.composing_label)
        camera_layout.addLayout(status_row)
        camera_layout.addLayout(button_row)

        # side panels: messages (default) or the teach panel
        self.messages_area = MessagesArea()
        self.messages_area.send_scene_requested.connect(self._send_scene)

        messages_page = QWidget()
        messages_layout = QVBoxLayout(messages_page)
        messages_layout.setContentsMargins(0, 0, 0, 0)
        messages_layout.setSpacing(14)
        messages_layout.addWidget(self.messages_area, stretch=1)

        self._messages_page = messages_page

        self._teach = TeachDialog(
            templates=self._templates,
            on_record=self._start_record,
            on_clear=self._clear_word,
            on_close=self._show_messages,
        )

        self.side_stack = QStackedWidget()
        self.side_stack.addWidget(self._messages_page)
        self.side_stack.addWidget(self._teach)
        self.side_stack.setCurrentWidget(self._messages_page)

        area.addWidget(camera_card, 62)
        area.addWidget(self.side_stack, 38)
        return area

    # ---------- teach panel wiring ----------
    def _show_teach(self) -> None:
        self._teach.refresh()
        self.side_stack.setCurrentWidget(self._teach)

    def _show_messages(self) -> None:
        self.side_stack.setCurrentWidget(self._messages_page)

    def _start_record(self, word: str) -> None:
        if self._camera_worker is None:
            self._teach.status.setText("Open the camera first.")
            return
        self._recording_word = word
        self._camera_worker.request_record(word)

    def _clear_word(self, word: str) -> None:
        self._templates.clear_word(word)

    # ---------- behavior ----------
    def set_user(self, full_name: str, com_id: str) -> None:
        self.own_id.setText(com_id)
        self.name.setText(full_name)
        self.setToolTip(full_name)

    def reset(self) -> None:
        self.shutdown_camera()
        self.shutdown_realtime()
        self._recording_word = None
        self._reset_call_state()
        self._scene_sent = False
        self._scene_generating = False
        self._composing = False
        self._last_scene = ""
        self._last_sentence = ""
        self.peer_edit.clear()
        self.call_status.setText("")
        self.own_id.setText("")
        self.name.setText("")
        self.setToolTip("")
        self.camera_hud.setText("Hand tracking is off")
        self.scene_status.setText("")
        self.fps_label.setText("")
        self.gesture_label.setText("")
        self.composing_label.setText("—")
        self._teach.status.setText("")
        self.messages_area.clear()
        self._show_messages()
        self._update_scene_send_button()
        self._update_generate_button()

    def _on_peer_changed(self, text: str) -> None:
        upper = text.upper()
        if text != upper:
            self.peer_edit.blockSignals(True)
            self.peer_edit.setText(upper)
            self.peer_edit.blockSignals(False)

        valid = bool(COM_ID_PATTERN.match(self.peer_edit.text().strip()))

        self.peer_edit.setProperty("invalid", bool(upper) and not valid)
        self.peer_edit.setProperty("valid", valid)
        self.peer_edit.style().unpolish(self.peer_edit)
        self.peer_edit.style().polish(self.peer_edit)
        self._update_call_button()

    def _update_call_button(self) -> None:
        valid = bool(COM_ID_PATTERN.match(self.peer_edit.text().strip()))
        ready = self._realtime is not None and self._realtime.is_ready
        if self._call_state in ("active", "outgoing"):
            self.call_button.setEnabled(True)
            return
        self.call_button.setEnabled(valid and ready and self._call_state == "idle")

    def _try_call(self) -> None:
        if self._call_state == "active" and self._call_id:
            if self._realtime and self._realtime.end_call(self._call_id):
                self.call_status.setText("Ending call…")
            return

        if self._call_state == "outgoing" and self._call_id:
            if self._realtime and self._realtime.end_call(self._call_id):
                self.call_status.setText("Cancelling call…")
            return

        peer = self.peer_edit.text().strip()
        if not peer:
            return
        if self._realtime is None or not self._realtime.is_ready:
            self.call_status.setText("Realtime is not connected yet")
            return
        if peer == self.own_id.text():
            self.call_status.setText("You cannot call yourself")
            return

        if self._realtime.start_call(peer):
            self._call_state = "outgoing"
            self._call_id = None
            self.call_status.setText(f"Calling {peer}…")
            self._update_call_button()
        else:
            self.call_status.setText("Realtime is not connected yet")

    # ---------- realtime ----------
    def start_realtime(self, token: str) -> None:
        if not token:
            return

        self._token = token
        if self._realtime is not None:
            self._realtime.close()
            self._realtime.deleteLater()

        self._realtime = RealtimeClient(self)
        self._realtime.ready.connect(self._on_realtime_ready)
        self._realtime.ringing.connect(self._on_call_ringing)
        self._realtime.incoming.connect(self._on_call_incoming)
        self._realtime.accepted.connect(self._on_call_accepted)
        self._realtime.rejected.connect(self._on_call_rejected)
        self._realtime.ended.connect(self._on_call_ended)
        self._realtime.content.connect(self._on_realtime_content)
        self._realtime.error.connect(self._on_realtime_error)
        self._realtime.connection_changed.connect(self._on_realtime_connection)
        self._realtime.connect(token)
        self.call_status.setText("Connecting to realtime…")
        self._update_scene_send_button()

    def shutdown_realtime(self) -> None:
        if self._realtime is not None:
            self._realtime.close()
            self._realtime.deleteLater()
            self._realtime = None
        self._token = None
        self._reset_call_state()
        self.call_status.setText("")
        self._update_scene_send_button()

    def _on_realtime_ready(self, _payload: dict) -> None:
        if self._call_state == "idle":
            self.call_status.setText("Realtime connected")
        self._update_call_button()
        self._update_scene_send_button()

    def _on_realtime_connection(self, connected: bool) -> None:
        if not connected and self._call_state in ("active", "outgoing", "incoming"):
            self._reset_call_state("Realtime disconnected")
        elif not connected:
            self.call_status.setText("Realtime offline — retrying…")
        self._update_call_button()
        self._update_scene_send_button()

    def _on_realtime_error(self, code: str, message: str) -> None:
        labels = {
            "target_not_found": "No user found with that com_id",
            "user_offline": "That user is offline",
            "user_busy": "That user is busy",
            "cannot_call_self": "You cannot call yourself",
            "call_not_found": "Call is no longer available",
            "call_not_active": "Call is not active",
            "forbidden": "You are not allowed to do that",
            "rate_limited": "Slow down — too many messages",
            "invalid_payload": "Invalid request",
            "server_error": "Server error — please try again",
            "unauthorized": "Realtime authentication failed",
            "session_replaced": message,
        }
        text = labels.get(code, message or "Realtime error")

        if code in (
            "unauthorized",
            "session_replaced",
            "call_not_found",
            "call_not_active",
            "forbidden",
        ):
            self._reset_call_state(text)
            return

        if code == "socket":
            self.call_status.setText("Realtime offline — retrying…")
        else:
            self.call_status.setText(text)
        self._update_call_button()

    def _on_call_ringing(self, payload: dict) -> None:
        self._call_state = "outgoing"
        self._call_id = payload.get("call_id")
        peer = payload.get("to", self.peer_edit.text().strip())
        self.call_status.setText(f"Calling {peer}…")
        self.call_button.setText("Cancel")
        self.peer_edit.setEnabled(False)
        self.incoming_bar.hide()
        self._update_call_button()

    def _on_call_incoming(self, payload: dict) -> None:
        call_id = payload.get("call_id")
        if not call_id:
            return
        if self._call_state != "idle":
            if self._realtime:
                self._realtime.reject_call(call_id)
            return

        caller = payload.get("from") or {}
        name = caller.get("full_name") or caller.get("com_id") or "Someone"
        com_id = caller.get("com_id", "")
        self._call_state = "incoming"
        self._call_id = call_id
        self.incoming_label.setText(f"Incoming call from {name} ({com_id})")
        self.incoming_bar.show()
        self.call_button.setEnabled(False)
        self.peer_edit.setEnabled(False)

    def _accept_incoming(self) -> None:
        call_id = self._call_id
        if not call_id or self._realtime is None or self._call_state != "incoming":
            return
        if self._realtime.accept_call(call_id):
            self.incoming_bar.hide()
            self.call_status.setText("Accepting call…")
            self._update_call_button()

    def _reject_incoming(self) -> None:
        call_id = self._call_id
        if not call_id or self._realtime is None:
            return
        if self._realtime.reject_call(call_id):
            self._reset_call_state("Call declined")

    def _on_call_accepted(self, payload: dict) -> None:
        self._call_state = "active"
        self._call_id = payload.get("call_id")
        self.incoming_bar.hide()

        peer = payload.get("peer") or {}
        name = peer.get("full_name", "")
        com_id = peer.get("com_id", "")
        if name and com_id:
            self.call_status.setText(f"In call with {name} ({com_id})")
        else:
            self.call_status.setText(f"In call with {com_id or 'peer'}")

        self.call_button.setText("End call")
        self.peer_edit.setEnabled(False)
        self._update_call_button()
        self._update_scene_send_button()

    def _on_call_rejected(self, _payload: dict) -> None:
        self._reset_call_state("Call declined")

    def _on_call_ended(self, payload: dict) -> None:
        reason = payload.get("reason", "ended")
        labels = {
            "timeout": "Call timed out",
            "peer_disconnected": "Call ended — peer disconnected",
            "session_replaced": "Call ended",
            "ended": "Call ended",
            "rejected": "Call declined",
        }
        self._reset_call_state(labels.get(reason, "Call ended"))

    def _on_realtime_content(self, payload: dict) -> None:
        content = payload.get("content")
        if not content:
            return
        msg_type = "scene" if payload.get("kind") == "scene" else "txt"
        msg = Message(msg_type, content, mine=False)
        self.messages_area.add_message(msg)
        self._show_messages()
        if msg_type == "txt":
            try:
                Speaker.say(msg)
            except Exception:
                pass

    def _reset_call_state(self, status: str | None = None) -> None:
        self._call_state = "idle"
        self._call_id = None
        self.incoming_bar.hide()
        self.call_button.setText("Connect")
        self.peer_edit.setEnabled(True)
        self._update_call_button()
        self._update_scene_send_button()
        if status is not None:
            self.call_status.setText(status)

    def _open_camera(self) -> None:
        if self._camera_worker is not None:
            self._camera_worker.stop()
            self.camera_button.setEnabled(False)
            self.camera_hud.setText("Stopping camera…")
            return

        self.camera_button.setText("Stop Camera")
        self.camera_hud.setText("Starting camera…")

        worker = CameraWorker(templates=self._templates, parent=self)
        worker.frame_ready.connect(self._on_frame)
        worker.status_changed.connect(self.camera_hud.setText)
        worker.sentence_changed.connect(self._on_sentence_changed)
        worker.sentence_ready.connect(self._on_sentence_ready)
        worker.gesture_detected.connect(self._on_gesture)
        worker.gesture_recorded.connect(self._on_gesture_recorded)
        worker.gesture_record_failed.connect(self._on_gesture_record_failed)
        worker.record_progress.connect(self._on_record_progress)
        worker.fps_changed.connect(self._on_fps)
        worker.stopped.connect(self._on_camera_stopped)
        self._camera_worker = worker
        self.clear_button.setEnabled(True)
        worker.start()

    def _on_frame(self, rgb: np.ndarray) -> None:
        if rgb is None or rgb.size == 0:
            return
        self._last_frame = rgb
        self._render_frame()

    def _render_frame(self) -> None:
        if self._last_frame is None:
            return
        h, w, _ = self._last_frame.shape
        qimage = QImage(self._last_frame.data, w, h, 3 * w, QImage.Format.Format_RGB888)
        target = self.camera_video.size()
        if target.width() < 1 or target.height() < 1:
            return
        pixmap = QPixmap.fromImage(qimage).scaled(
            target,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = max(0, (pixmap.width() - target.width()) // 2)
        y = max(0, (pixmap.height() - target.height()) // 2)
        self.camera_video.setPixmap(pixmap.copy(x, y, target.width(), target.height()))

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._render_frame()

    def _on_sentence_changed(self, text: str) -> None:
        self.composing_label.setText(text if text else "—")
        self._composing = bool(text.strip())
        self._update_generate_button()

    def _on_sentence_ready(self, text: str) -> None:
        self._composing = False
        if text:
            self._last_sentence = text.strip()
            msg = Message("txt", text)
            self.messages_area.add_message(msg)

            if self._call_state == "active" and self._call_id and self._realtime is not None:
                self._realtime.send_text(self._call_id, text)

            self.camera_hud.setText("Sentence sent to My messages")
        else:
            self._last_sentence = ""
        self._update_generate_button()
        self.composing_label.setText("—")

    def _on_gesture(self, word: str, confidence: float) -> None:
        self.gesture_label.setText(f"Sign: {word}  ({confidence * 100:.0f}%)")
        QTimer.singleShot(2500, lambda: self.gesture_label.setText(""))
        try:
            Speaker.say(Message("txt", word))
        except Exception:
            pass

    def _on_gesture_recorded(self, word: str, total: int) -> None:
        self._recording_word = None
        self._teach.on_recorded(word, total)

    def _on_gesture_record_failed(self, word: str) -> None:
        self._recording_word = None
        self._teach.status.setText(
            f"Could not save “{word}” — keep your hand in view and try again."
        )

    def _on_record_progress(self, remaining_ms: int) -> None:
        if self._recording_word:
            self._teach.on_record_progress(self._recording_word, remaining_ms)

    def _on_fps(self, fps: float) -> None:
        self.fps_label.setText(f"{fps:.0f} fps")

    def _clear_composing(self) -> None:
        if self._camera_worker is not None:
            self._camera_worker.request_clear()
        self.composing_label.setText("—")
        self._composing = False
        self._last_sentence = ""
        self._update_generate_button()

    def _ensure_scene_worker(self):
        if self._scene_worker is None:
            self._scene_worker = SceneWorker(self)
            self._scene_worker.scene_ready.connect(self._on_scene_ready)
            self._scene_worker.scene_failed.connect(self._on_scene_failed)
            self._scene_worker.status_changed.connect(self.scene_status.setText)
        if not self._scene_worker.isRunning():
            self._scene_worker.start()
        return self._scene_worker

    def _update_generate_button(self) -> None:
        if not hasattr(self, "gen_scene_btn"):
            return
        self.gen_scene_btn.setEnabled(
            bool(self._last_sentence.strip())
            and not self._composing
            and not self._scene_generating
        )

    def _generate_scene(self):
        if self._scene_generating:
            return
        sentence = self._last_sentence.strip()
        if not sentence:
            return
        if not self._token:
            self.scene_status.setText("Sign in again to generate scenes")
            return
        self._scene_generating = True
        self._update_generate_button()
        self.scene_status.setText("Generating scene...")
        worker = self._ensure_scene_worker()
        worker.generate(sentence, self._token)

    def _on_scene_ready(self, sentence: str, data_url: str):
        self._scene_generating = False
        self._last_scene = data_url
        self._scene_sent = False
        msg = Message("scene", data_url, mine=True)
        self.messages_area.add_message(msg)
        self._show_messages()
        self.scene_status.setText("Scene ready — click Send")
        self._update_scene_send_button()
        self._update_generate_button()

    def _on_scene_failed(self, sentence: str, error: str):
        self._scene_generating = False
        self.scene_status.setText(f"Scene generation failed: {error}")
        self._update_scene_send_button()
        self._update_generate_button()

    def _send_scene(self) -> None:
        if not self._last_scene:
            self.scene_status.setText("Generate a scene first")
            return
        if (
            self._call_state != "active"
            or not self._call_id
            or self._realtime is None
        ):
            self.scene_status.setText("Start a call before sending scenes")
            self._update_scene_send_button()
            return

        if self._realtime.send_scene(self._call_id, self._last_scene):
            self._scene_sent = True
            self.scene_status.setText("Scene sent")
        else:
            self.scene_status.setText("Scene send failed — realtime offline")
        self._update_scene_send_button()

    def _update_scene_send_button(self) -> None:
        if not hasattr(self, "messages_area"):
            return
        active = (
            self._call_state == "active"
            and bool(self._call_id)
            and self._realtime is not None
        )
        enabled = bool(self._last_scene) and active and not self._scene_sent
        self.messages_area.set_scene_send_state(
            enabled, "Sent" if self._scene_sent else "Send"
        )

    def _on_camera_stopped(self) -> None:
        worker = self.sender()
        if worker is not None and worker is not self._camera_worker:
            return
        worker = self._camera_worker
        self._camera_worker = None
        self._reset_camera_ui()
        if worker is not None:
            worker.deleteLater()

    def _reset_camera_ui(self) -> None:
        self._last_frame = None
        self.camera_button.setText("Open Camera")
        self.camera_button.setEnabled(True)
        self.clear_button.setEnabled(False)
        self.camera_hud.setText("Hand tracking is off")
        self.fps_label.setText("")
        self.gesture_label.setText("")
        self.composing_label.setText("—")
        self._composing = False
        self._scene_generating = False
        self._last_sentence = ""
        self._update_generate_button()
        self.camera_video.clear()
        self.camera_video.setText("Camera feed will appear here")

    def shutdown_camera(self) -> None:
        worker = self._camera_worker
        self._camera_worker = None
        if worker is not None:
            try:
                worker.disconnect()
            except (RuntimeError, TypeError):
                pass
            worker.stop()
            worker.wait(3000)
            worker.deleteLater()
        self._reset_camera_ui()
        if self._scene_worker is not None:
            try:
                self._scene_worker.stop()
                self._scene_worker.wait(2000)
            except Exception:
                pass
            self._scene_worker.deleteLater()
            self._scene_worker = None
