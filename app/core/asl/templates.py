"""Teachable gesture templates: normalized landmark sequences matched with DTW."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from core.asl.gesture_types import SignFrame
from core.config import config_path

RESAMPLE_N = 30
MATCH_THRESHOLD = 4.5  # mean per-frame distance
MATCH_MARGIN = 0.85  # best must beat runner-up by this fraction

_SHAPE = {0: 0.0, 1: 0.5, 2: 1.0}  # keyed by FingerState/ThumbState .value


def _templates_path() -> Path:
    return config_path("gestures.json")


def frame_vector(frame: SignFrame, primary: str = "Right") -> list[float] | None:
    """Fixed-length per-frame feature vector, or None when the primary hand is absent."""
    p = frame.hands.get(primary)
    if p is None:
        return None
    f = p.features
    vec = [
        _SHAPE[f.index.value],
        _SHAPE[f.middle.value],
        _SHAPE[f.ring.value],
        _SHAPE[f.pinky.value],
        _SHAPE[f.thumb.value],
        *p.palm_normal,
        p.palm_center[0],
        p.palm_center[1],
    ]
    secondary = next((h for name, h in frame.hands.items() if name != p.handedness), None)
    if secondary is not None:
        scale = max(p.hand_size, 1e-6)
        s = secondary.features
        vec += [
            1.0,
            (secondary.palm_center[0] - p.palm_center[0]) / scale,
            (secondary.palm_center[1] - p.palm_center[1]) / scale,
            _SHAPE[s.index.value],
            _SHAPE[s.middle.value],
            _SHAPE[s.ring.value],
            _SHAPE[s.pinky.value],
            _SHAPE[s.thumb.value],
        ]
    else:
        vec += [0.0] * 8
    return vec


def _sequence_vectors(
    frames: list[SignFrame], primary: str | None = None
) -> list[list[float]]:
    """Feature vectors for one consistently-chosen hand across a sequence."""
    if primary is not None:
        return [
            v for frame in frames if (v := frame_vector(frame, primary)) is not None
        ]

    counts: dict[str, int] = {}
    for frame in frames:
        for name in frame.hands:
            counts[name] = counts.get(name, 0) + 1
    if not counts:
        return []
    primary = "Right" if "Right" in counts else max(counts, key=counts.get)
    return [
        v for frame in frames if (v := frame_vector(frame, primary)) is not None
    ]


def _normalize_positions(vectors: list[list[float]]) -> list[list[float]]:
    """Shift primary hand positions relative to the first frame."""
    if not vectors:
        return vectors
    x0, y0 = vectors[0][8], vectors[0][9]
    for vec in vectors:
        vec[8] -= x0
        vec[9] -= y0
    return vectors


def _resample(vectors: list[list[float]], n: int = RESAMPLE_N) -> list[list[float]]:
    if len(vectors) == 0:
        return []
    if len(vectors) == 1:
        return [list(vectors[0]) for _ in range(n)]
    out = []
    for i in range(n):
        pos = i * (len(vectors) - 1) / (n - 1)
        lo = int(math.floor(pos))
        hi = min(lo + 1, len(vectors) - 1)
        frac = pos - lo
        out.append([a + (b - a) * frac for a, b in zip(vectors[lo], vectors[hi])])
    return out


def dtw_distance(a: list[list[float]], b: list[list[float]]) -> float:
    n, m = len(a), len(b)
    if n == 0 or m == 0:
        return float("inf")
    prev = [float("inf")] * (m + 1)
    prev[0] = 0.0
    for i in range(1, n + 1):
        cur = [float("inf")] * (m + 1)
        for j in range(1, m + 1):
            cost = math.dist(a[i - 1], b[j - 1])
            cur[j] = cost + min(cur[j - 1], prev[j], prev[j - 1])
        prev = cur
    return prev[m] / max(n, m)


@dataclass
class GestureTemplate:
    word: str
    samples: list[list[list[float]]] = field(default_factory=list)

    def to_json(self) -> dict:
        return {"word": self.word, "samples": self.samples}

    @classmethod
    def from_json(cls, data: dict) -> "GestureTemplate":
        return cls(word=data["word"], samples=data.get("samples", []))


class TemplateStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _templates_path()
        self.templates: dict[str, GestureTemplate] = {}
        self.load()

    # ---- recording ----
    def add_sample(
        self, word: str, frames: list[SignFrame], primary: str | None = None
    ) -> bool:
        vectors = _sequence_vectors(frames, primary)
        if len(vectors) < 5:
            return False
        sample = _resample(_normalize_positions(vectors))
        tpl = self.templates.setdefault(word, GestureTemplate(word=word))
        tpl.samples.append(sample)
        self.save()
        return True

    def clear_word(self, word: str) -> None:
        self.templates.pop(word, None)
        self.save()

    def sample_count(self, word: str) -> int:
        tpl = self.templates.get(word)
        return len(tpl.samples) if tpl else 0

    # ---- matching ----
    def match(
        self, frames: list[SignFrame], primary: str | None = None
    ) -> tuple[str, float, float] | None:
        if not self.templates:
            return None
        if primary is not None:
            return self._match_vectors(_sequence_vectors(frames, primary))

        best: tuple[str, float, float] | None = None
        labels = {name for frame in frames for name in frame.hands}
        for label in labels:
            result = self._match_vectors(_sequence_vectors(frames, label))
            if result is not None and (best is None or result[2] < best[2]):
                best = result
        return best

    def _match_vectors(
        self, vectors: list[list[float]]
    ) -> tuple[str, float, float] | None:
        if len(vectors) < 5:
            return None
        sample = _resample(_normalize_positions(vectors))

        scored: list[tuple[float, str]] = []
        for tpl in self.templates.values():
            if not tpl.samples:
                continue
            best = min(dtw_distance(sample, known) for known in tpl.samples)
            scored.append((best, tpl.word))
        if not scored:
            return None
        scored.sort()
        best_dist, best_word = scored[0]
        if best_dist > MATCH_THRESHOLD:
            return None
        if len(scored) > 1 and best_dist > scored[1][0] * MATCH_MARGIN:
            return None
        confidence = max(0.0, min(1.0, 1.0 - best_dist / MATCH_THRESHOLD))
        return best_word, confidence, best_dist

    # ---- persistence ----
    def save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            data = {"templates": [tpl.to_json() for tpl in self.templates.values()]}
            self._path.write_text(json.dumps(data))
        except OSError:
            pass

    def load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text())
        except Exception:
            return
        for item in data.get("templates", []):
            tpl = GestureTemplate.from_json(item)
            self.templates[tpl.word] = tpl
