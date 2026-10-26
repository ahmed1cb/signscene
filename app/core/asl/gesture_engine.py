"""Per-frame orchestration: two-hand features -> word gestures."""

from __future__ import annotations

import math
from dataclasses import dataclass

from core.asl.features import FeatureExtractor
from core.asl.gesture_types import HandFrame, SignBuffer, SignFrame
from core.asl.templates import TemplateStore

WORD_COOLDOWN_MS = 700
TEMPLATE_EVERY = 3
WRIST = 0
MIDDLE_MCP = 9
MIN_CONFIDENCE = 0.80


@dataclass
class GestureResult:
    word: str | None = None
    word_confidence: float = 0.0
    recorded_word: str | None = None
    record_failed_word: str | None = None
    recording: bool = False
    record_remaining_ms: int = 0


@dataclass
class GestureEngine:
    templates: TemplateStore | None = None
    buffer_seconds: float = 2.5

    def __post_init__(self) -> None:
        self._extractors: dict[str, FeatureExtractor] = {}
        self._buffer = SignBuffer(seconds=self.buffer_seconds)
        self._frame_count = 0
        self._cooldown_until = 0
        self._record_word: str | None = None
        self._record_until = 0
        self._record_frames: list[SignFrame] = []
        self._last_word: str | None = None
        self._no_hand_since = -1

    # ---------- recording (teach mode) ----------
    def start_recording(self, word: str, duration_ms: int, now_ms: int) -> None:
        self._record_word = word
        self._record_until = now_ms + duration_ms
        self._record_frames = []
        self._buffer = SignBuffer(seconds=self.buffer_seconds)

    @property
    def is_recording(self) -> bool:
        return self._record_word is not None

    # ---------- main ----------
    def update(self, ts_ms: int, hands) -> GestureResult:
        result = GestureResult()
        self._frame_count += 1

        frame = SignFrame(t_ms=ts_ms)
        for landmarks, handedness, *rest in hands:
            world = rest[0] if rest else None
            hand_frame = self._build_hand_frame(landmarks, handedness, world)
            if hand_frame is not None:
                frame.hands[hand_frame.handedness] = hand_frame

        self._buffer.add(frame)
        active = self._active_hand(frame)
        if self._record_word is not None:
            if frame.hands:
                self._record_frames.append(frame)

            result.recording = True
            result.record_remaining_ms = max(0, self._record_until - ts_ms)

            if ts_ms >= self._record_until:
                word = self._record_word
                if self._finish_recording(ts_ms):
                    result.recorded_word = word
                else:
                    result.record_failed_word = word
                result.recording = False

            return result

        if active is None:
            if self._no_hand_since < 0:
                self._no_hand_since = ts_ms
            elif ts_ms - self._no_hand_since >= 400:
                self._last_word = None
        else:
            self._no_hand_since = -1

        if ts_ms < self._cooldown_until:
            return result

        if active is not None:
            if self.templates is not None and self._frame_count % TEMPLATE_EVERY == 0:
                window = [f for f in self._buffer.frames if ts_ms - f.t_ms <= 2000]
                match = self.templates.match(window)
                if match is not None:
                    word, confidence = match[0], match[1]
                    if confidence >= MIN_CONFIDENCE:
                        if word != self._last_word:
                            result.word = word
                            result.word_confidence = confidence
                            self._last_word = word
                        self._cooldown_until = ts_ms + WORD_COOLDOWN_MS
                        self._buffer = SignBuffer(seconds=self.buffer_seconds)
        return result

    # ---------- internals ----------
    def clear(self) -> None:
        self._buffer = SignBuffer(seconds=self.buffer_seconds)
        self._last_word = None
        self._no_hand_since = -1
        self._cooldown_until = 0

    def _finish_recording(self, ts_ms: int) -> bool:
        word = self._record_word
        self._record_word = None
        saved = False
        if word and self.templates is not None:
            saved = self.templates.add_sample(word, self._record_frames)
        self._record_frames = []
        self._buffer = SignBuffer(seconds=self.buffer_seconds)
        self._cooldown_until = ts_ms + WORD_COOLDOWN_MS
        self._last_word = None
        return saved

    def _build_hand_frame(
        self, landmarks, handedness: str, world_landmarks=None
    ) -> HandFrame | None:
        if not landmarks:
            return None
        extractor = self._extractors.setdefault(handedness, FeatureExtractor())
        features = extractor.extract(world_landmarks or landmarks)
        points = [(float(lm.x), float(lm.y)) for lm in landmarks]
        wrist = points[WRIST]
        middle_mcp = points[MIDDLE_MCP]
        hand_size = max(
            abs(middle_mcp[1] - wrist[1]) + abs(middle_mcp[0] - wrist[0]), 1e-4
        )
        normal = _palm_normal(landmarks)
        return HandFrame(
            handedness=handedness,
            features=features,
            points_xy=points,
            palm_normal=normal,
            hand_size=hand_size,
        )

    @staticmethod
    def _active_hand(frame: SignFrame, preferred: str = "Right") -> str | None:
        if not frame.hands:
            return None
        if preferred in frame.hands:
            return preferred
        return next(iter(frame.hands))


def _palm_normal(landmarks) -> tuple[float, float, float]:
    p0 = (landmarks[0].x, landmarks[0].y, landmarks[0].z)
    p5 = (landmarks[5].x, landmarks[5].y, landmarks[5].z)
    p17 = (landmarks[17].x, landmarks[17].y, landmarks[17].z)
    u = (p5[0] - p0[0], p5[1] - p0[1], p5[2] - p0[2])
    v = (p17[0] - p0[0], p17[1] - p0[1], p17[2] - p0[2])
    n = (
        u[1] * v[2] - u[2] * v[1],
        u[2] * v[0] - u[0] * v[2],
        u[0] * v[1] - u[1] * v[0],
    )
    norm = math.sqrt(sum(c * c for c in n)) or 1e-6
    return (n[0] / norm, n[1] / norm, n[2] / norm)
