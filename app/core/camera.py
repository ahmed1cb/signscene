import time
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    HandLandmarker,
    HandLandmarkerOptions,
    HandLandmarksConnections,
    RunningMode,
)
from PySide6.QtCore import QThread, Signal

from core.asl.decoder import SentenceBuilder
from core.asl.gesture_engine import GestureEngine
from core.asl.templates import TemplateStore

MODEL_PATH = Path(__file__).resolve().parents[1] / "assets" / "models" / "hand_landmarker.task"
CONNECTIONS = HandLandmarksConnections.HAND_CONNECTIONS
HUD_BGR = (3, 183, 255)  # #FFB703
LANDMARK_BGR = (166, 162, 31)  # #1FA2A6
POINT_BGR = (255, 255, 255)
HUD_BG_BGR = (48, 19, 11)  # #0B1330

RECORD_MS = 2000


class CameraWorker(QThread):
    """Captures the webcam, tracks hands, and recognizes signs."""

    frame_ready = Signal(object)  # numpy RGB ndarray
    status_changed = Signal(str)
    sentence_changed = Signal(str)
    sentence_ready = Signal(str)
    gesture_detected = Signal(str, float)  # word, confidence
    gesture_recorded = Signal(str, int)  # word, total samples
    record_progress = Signal(int)  # remaining ms in the current recording
    fps_changed = Signal(float)
    stopped = Signal()

    def __init__(self, templates: TemplateStore | None = None, parent=None) -> None:
        super().__init__(parent)
        self._running = False
        self._clear_requested = False
        self._record_word: str | None = None
        self._templates = templates or TemplateStore()
        self._engine = GestureEngine(templates=self._templates)
        self._builder: SentenceBuilder | None = None

    # ---------- thread-safe requests ----------
    def stop(self) -> None:
        self._running = False

    def request_clear(self) -> None:
        self._clear_requested = True

    def request_record(self, word: str) -> None:
        self._record_word = word

    # ---------- main loop ----------
    def run(self) -> None:
        self._running = True

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            self.status_changed.emit("Camera unavailable — is it connected and not in use?")
            self.stopped.emit()
            return

        try:
            options = HandLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=str(MODEL_PATH)),
                running_mode=RunningMode.VIDEO,
                num_hands=2,
            )
            landmarker = HandLandmarker.create_from_options(options)
        except Exception as exc:
            cap.release()
            self.status_changed.emit(f"Hand tracking failed to start: {exc}")
            self.stopped.emit()
            return

        prev_ts = -1
        self.status_changed.emit("Looking for a hand…")

        builder = SentenceBuilder(
            on_sentence_changed=lambda text: self.sentence_changed.emit(text),
            on_sentence_ready=lambda text: self.sentence_ready.emit(text),
        )
        self._builder = builder

        frame_times: list[float] = []
        last_fps_emit = 0.0

        try:
            while self._running:
                ok, frame = cap.read()
                if not ok:
                    self.status_changed.emit("Camera read failed")
                    break

                frame = cv2.flip(frame, 1)  # selfie view; handedness output matches flipped input
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                ts_ms = int(time.monotonic() * 1000)
                if ts_ms <= prev_ts:
                    ts_ms = prev_ts + 1
                prev_ts = ts_ms

                result = landmarker.detect_for_video(
                    mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), ts_ms
                )

                height, width = rgb.shape[:2]
                hands = []
                if result.hand_landmarks:
                    for index, landmarks in enumerate(result.hand_landmarks):
                        label = "Right"
                        if result.handedness and result.handedness[index]:
                            label = result.handedness[index][0].category_name or "Right"
                        hands.append((landmarks, label))
                        self._draw_landmarks(rgb, landmarks)

                self._apply_requests(ts_ms)

                gesture = self._engine.update(ts_ms, hands, width, height)

                if gesture.recorded_word:
                    total = self._templates.sample_count(gesture.recorded_word)
                    self.gesture_recorded.emit(gesture.recorded_word, total)
                    self.status_changed. emit(f"Recorded “{gesture.recorded_word}” ({total} samples)")
                if gesture.recording:
                    self.record_progress.emit(gesture.record_remaining_ms)

                if gesture.word:
                    builder.add_word(gesture.word)
                    self.gesture_detected.emit(gesture.word, gesture.word_confidence)
                    self.status_changed.emit(f"Detected “{gesture.word}”")
                elif hands:
                    self.status_changed.emit(f"Tracking {len(hands)} hand(s)")

                builder.tick(ts_ms, has_hand=bool(hands))

                self._draw_hud(rgb, gesture.word)

                self.frame_ready.emit(rgb)

                now = time.monotonic()
                frame_times.append(now)
                frame_times = [t for t in frame_times if now - t <= 2.0]
                if now - last_fps_emit > 0.5:
                    last_fps_emit = now
                    self.fps_changed.emit(len(frame_times) / min(2.0, max(now - frame_times[0], 1e-3)))
        finally:
            cap.release()
            landmarker.close()
            self.stopped.emit()

    # ---------- helpers ----------
    def _apply_requests(self, ts_ms: int) -> None:
        if self._clear_requested:
            self._clear_requested = False
            if self._builder is not None:
                self._builder.clear_sentence()
            self._engine.clear()

        if self._record_word is not None and not self._engine.is_recording:
            word = self._record_word
            self._record_word = None
            self._engine.start_recording(word, RECORD_MS, ts_ms)
            self.status_changed.emit(f"Recording “{word}” — perform the sign now")

    @staticmethod
    def _draw_hud(rgb, word: str | None) -> None:
        if not word:
            return
        cv2.rectangle(rgb, (10, 10), (320, 52), HUD_BG_BGR, -1)
        cv2.rectangle(rgb, (10, 10), (320, 52), HUD_BGR, 1)
        cv2.putText(
            rgb, word.lower(), (20, 42),
            cv2.FONT_HERSHEY_SIMPLEX, 0.9, HUD_BGR, 2, cv2.LINE_AA,
        )

    @staticmethod
    def _draw_landmarks(rgb, landmarks) -> None:
        h, w = rgb.shape[:2]
        points = [(int(lm.x * w), int(lm.y * h)) for lm in landmarks]
        for connection in CONNECTIONS:
            cv2.line(rgb, points[connection.start], points[connection.end], LANDMARK_BGR, 2)
        for point in points:
            cv2.circle(rgb, point, 3, POINT_BGR, -1)
