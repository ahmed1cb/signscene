"""Geometric hand features from MediaPipe world landmarks (metric, scale-invariant)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

# MediaPipe hand landmark indices
WRIST = 0
THUMB_CMC, THUMB_MCP, THUMB_TIP = 1, 2, 4
INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP = 5, 6, 7, 8
MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP = 9, 10, 11, 12
RING_MCP, RING_PIP, RING_DIP, RING_TIP = 13, 14, 15, 16
PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP = 17, 18, 19, 20


class FingerState(Enum):
    CURLED = 0
    HALF = 1
    EXTENDED = 2


class ThumbState(Enum):
    CURLED = 0
    HALF = 1
    EXTENDED = 2


@dataclass
class HandFeatures:
    index: FingerState
    middle: FingerState
    ring: FingerState
    pinky: FingerState
    thumb: ThumbState


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _norm(a):
    return math.sqrt(_dot(a, a))


def _angle_between(u, v) -> float:
    """Angle in degrees between two vectors."""
    nu, nv = _norm(u), _norm(v)
    if nu < 1e-9 or nv < 1e-9:
        return 180.0
    cos = max(-1.0, min(1.0, _dot(u, v) / (nu * nv)))
    return math.degrees(math.acos(cos))


def _point(lm, idx):
    p = lm[idx]
    return (p.x, p.y, p.z)


def _finger_state(landmarks, mcp: int, pip: int, dip: int, tip: int) -> FingerState:
    mcp_p, pip_p, tip_p = _point(landmarks, mcp), _point(landmarks, pip), _point(landmarks, tip)
    bend = _angle_between(_sub(mcp_p, pip_p), _sub(tip_p, pip_p))
    if bend >= 150:
        return FingerState.EXTENDED
    if bend >= 105:
        return FingerState.HALF
    return FingerState.CURLED


class FeatureExtractor:
    """Extracts hand-shape features from a frame's landmarks."""

    def extract(self, landmarks) -> HandFeatures:
        index = _finger_state(landmarks, INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP)
        middle = _finger_state(landmarks, MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP)
        ring = _finger_state(landmarks, RING_MCP, RING_PIP, RING_DIP, RING_TIP)
        pinky = _finger_state(landmarks, PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP)

        thumb_a = _angle_between(
            _sub(_point(landmarks, THUMB_MCP), _point(landmarks, THUMB_CMC)),
            _sub(_point(landmarks, THUMB_TIP), _point(landmarks, THUMB_MCP)),
        )
        if thumb_a >= 150:
            thumb = ThumbState.EXTENDED
        elif thumb_a >= 115:
            thumb = ThumbState.HALF
        else:
            thumb = ThumbState.CURLED

        return HandFeatures(
            index=index,
            middle=middle,
            ring=ring,
            pinky=pinky,
            thumb=thumb,
        )
