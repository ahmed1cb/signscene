"""Shared data structures for the gesture pipeline."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from core.asl.features import HandFeatures

WRIST = 0


@dataclass
class HandFrame:
    """One hand observed in one frame."""

    handedness: str  # "Left" | "Right"
    features: HandFeatures
    points_xy: list[tuple[float, float]]  # 21 points, normalized image coords
    palm_normal: tuple[float, float, float]
    hand_size: float  # normalized by frame width

    @property
    def palm_center(self) -> tuple[float, float]:
        pts = [self.points_xy[WRIST], self.points_xy[5], self.points_xy[9], self.points_xy[13], self.points_xy[17]]
        return (
            sum(p[0] for p in pts) / len(pts),
            sum(p[1] for p in pts) / len(pts),
        )


@dataclass
class SignFrame:
    t_ms: int
    hands: dict[str, HandFrame] = field(default_factory=dict)


class SignBuffer:
    """Rolling window of SignFrames with trajectory helpers."""

    def __init__(self, seconds: float = 2.5, maxlen: int = 150) -> None:
        self._max_ms = int(seconds * 1000)
        self.frames: deque[SignFrame] = deque(maxlen=maxlen)

    def add(self, frame: SignFrame) -> None:
        self.frames.append(frame)
        cutoff = frame.t_ms - self._max_ms
        while self.frames and self.frames[0].t_ms < cutoff:
            self.frames.popleft()
