"""Pose polygon features for hands, fingers, and bodies.

The schemas follow common markerless-pose conventions:
  - 21-point hands: wrist plus four joints per finger.
  - 33-point body pose: shoulders, elbows, wrists, hips, knees, ankles, and
    face/foot landmarks compatible with MediaPipe/ML Kit style outputs.

This module does not run a pose detector. It converts detector landmarks into
stable geometry vectors that can be fed into the video lattice.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import IntEnum
from typing import Iterable, Mapping, Sequence

import numpy as np

_EPS = 1e-9


@dataclass(frozen=True)
class Landmark:
    """One normalized landmark point.

    x and y are image-plane coordinates. z is optional depth. visibility is a
    detector confidence or in-frame likelihood in [0, 1].
    """

    x: float
    y: float
    z: float = 0.0
    visibility: float = 1.0

    def xy(self) -> np.ndarray:
        return np.array([self.x, self.y], dtype=np.float64)

    def xyz(self) -> np.ndarray:
        return np.array([self.x, self.y, self.z], dtype=np.float64)


class HandLandmark(IntEnum):
    WRIST = 0
    THUMB_CMC = 1
    THUMB_MCP = 2
    THUMB_IP = 3
    THUMB_TIP = 4
    INDEX_MCP = 5
    INDEX_PIP = 6
    INDEX_DIP = 7
    INDEX_TIP = 8
    MIDDLE_MCP = 9
    MIDDLE_PIP = 10
    MIDDLE_DIP = 11
    MIDDLE_TIP = 12
    RING_MCP = 13
    RING_PIP = 14
    RING_DIP = 15
    RING_TIP = 16
    PINKY_MCP = 17
    PINKY_PIP = 18
    PINKY_DIP = 19
    PINKY_TIP = 20


class BodyLandmark(IntEnum):
    NOSE = 0
    LEFT_EYE_INNER = 1
    LEFT_EYE = 2
    LEFT_EYE_OUTER = 3
    RIGHT_EYE_INNER = 4
    RIGHT_EYE = 5
    RIGHT_EYE_OUTER = 6
    LEFT_EAR = 7
    RIGHT_EAR = 8
    MOUTH_LEFT = 9
    MOUTH_RIGHT = 10
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_ELBOW = 13
    RIGHT_ELBOW = 14
    LEFT_WRIST = 15
    RIGHT_WRIST = 16
    LEFT_PINKY = 17
    RIGHT_PINKY = 18
    LEFT_INDEX = 19
    RIGHT_INDEX = 20
    LEFT_THUMB = 21
    RIGHT_THUMB = 22
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_KNEE = 25
    RIGHT_KNEE = 26
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28
    LEFT_HEEL = 29
    RIGHT_HEEL = 30
    LEFT_FOOT_INDEX = 31
    RIGHT_FOOT_INDEX = 32


HAND_FINGERS: Mapping[str, tuple[HandLandmark, ...]] = {
    "thumb": (
        HandLandmark.WRIST,
        HandLandmark.THUMB_CMC,
        HandLandmark.THUMB_MCP,
        HandLandmark.THUMB_IP,
        HandLandmark.THUMB_TIP,
    ),
    "index": (
        HandLandmark.WRIST,
        HandLandmark.INDEX_MCP,
        HandLandmark.INDEX_PIP,
        HandLandmark.INDEX_DIP,
        HandLandmark.INDEX_TIP,
    ),
    "middle": (
        HandLandmark.WRIST,
        HandLandmark.MIDDLE_MCP,
        HandLandmark.MIDDLE_PIP,
        HandLandmark.MIDDLE_DIP,
        HandLandmark.MIDDLE_TIP,
    ),
    "ring": (
        HandLandmark.WRIST,
        HandLandmark.RING_MCP,
        HandLandmark.RING_PIP,
        HandLandmark.RING_DIP,
        HandLandmark.RING_TIP,
    ),
    "pinky": (
        HandLandmark.WRIST,
        HandLandmark.PINKY_MCP,
        HandLandmark.PINKY_PIP,
        HandLandmark.PINKY_DIP,
        HandLandmark.PINKY_TIP,
    ),
}

HAND_PALM_POLYGON: tuple[HandLandmark, ...] = (
    HandLandmark.WRIST,
    HandLandmark.INDEX_MCP,
    HandLandmark.MIDDLE_MCP,
    HandLandmark.RING_MCP,
    HandLandmark.PINKY_MCP,
)

BODY_TORSO_POLYGON: tuple[BodyLandmark, ...] = (
    BodyLandmark.LEFT_SHOULDER,
    BodyLandmark.RIGHT_SHOULDER,
    BodyLandmark.RIGHT_HIP,
    BodyLandmark.LEFT_HIP,
)

BODY_CHAINS: Mapping[str, tuple[BodyLandmark, ...]] = {
    "left_arm": (BodyLandmark.LEFT_SHOULDER, BodyLandmark.LEFT_ELBOW, BodyLandmark.LEFT_WRIST),
    "right_arm": (BodyLandmark.RIGHT_SHOULDER, BodyLandmark.RIGHT_ELBOW, BodyLandmark.RIGHT_WRIST),
    "left_leg": (BodyLandmark.LEFT_HIP, BodyLandmark.LEFT_KNEE, BodyLandmark.LEFT_ANKLE),
    "right_leg": (BodyLandmark.RIGHT_HIP, BodyLandmark.RIGHT_KNEE, BodyLandmark.RIGHT_ANKLE),
}


def _as_landmark_map(landmarks: Sequence[Landmark] | Mapping[IntEnum, Landmark]) -> dict[int, Landmark]:
    if isinstance(landmarks, Mapping):
        return {int(key): value for key, value in landmarks.items()}
    return {index: value for index, value in enumerate(landmarks)}


def _point(landmarks: Mapping[int, Landmark], index: IntEnum) -> Landmark:
    try:
        return landmarks[int(index)]
    except KeyError as exc:
        raise ValueError(f"missing landmark {index.name} ({int(index)})") from exc


def polygon_points(
    landmarks: Sequence[Landmark] | Mapping[IntEnum, Landmark], indices: Iterable[IntEnum]
) -> np.ndarray:
    mapped = _as_landmark_map(landmarks)
    return np.array([_point(mapped, index).xy() for index in indices], dtype=np.float64)


def polygon_area(points: np.ndarray) -> float:
    """Shoelace area of a 2D polygon."""

    points = np.asarray(points, dtype=np.float64)
    if len(points) < 3:
        return 0.0
    x = points[:, 0]
    y = points[:, 1]
    return float(abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))) / 2.0)


def polygon_centroid(points: np.ndarray) -> np.ndarray:
    """Area-weighted centroid, falling back to arithmetic mean."""

    points = np.asarray(points, dtype=np.float64)
    if len(points) == 0:
        return np.zeros(2, dtype=np.float64)
    area_signed = 0.0
    cx = 0.0
    cy = 0.0
    for i, p0 in enumerate(points):
        p1 = points[(i + 1) % len(points)]
        cross = p0[0] * p1[1] - p1[0] * p0[1]
        area_signed += cross
        cx += (p0[0] + p1[0]) * cross
        cy += (p0[1] + p1[1]) * cross
    if abs(area_signed) < _EPS:
        return np.mean(points, axis=0)
    return np.array([cx / (3.0 * area_signed), cy / (3.0 * area_signed)], dtype=np.float64)


def chain_length(points: np.ndarray) -> float:
    points = np.asarray(points, dtype=np.float64)
    if len(points) < 2:
        return 0.0
    return float(sum(np.linalg.norm(points[i + 1] - points[i]) for i in range(len(points) - 1)))


def angle_at(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """Interior angle ABC in radians."""

    ba = np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64)
    bc = np.asarray(c, dtype=np.float64) - np.asarray(b, dtype=np.float64)
    denom = max(float(np.linalg.norm(ba) * np.linalg.norm(bc)), _EPS)
    cos_theta = float(np.dot(ba, bc) / denom)
    return float(math.acos(max(-1.0, min(1.0, cos_theta))))


def finger_curl(points: np.ndarray) -> float:
    """Curl score in [0, 1], where 0 is straight and 1 is tightly folded."""

    points = np.asarray(points, dtype=np.float64)
    if len(points) < 4:
        return 0.0
    angles = [angle_at(points[i - 1], points[i], points[i + 1]) for i in range(1, len(points) - 1)]
    straightness = sum(angles) / (math.pi * len(angles))
    return float(max(0.0, min(1.0, 1.0 - straightness)))


def hand_polygon_features(landmarks: Sequence[Landmark] | Mapping[IntEnum, Landmark]) -> np.ndarray:
    """Return a fixed hand geometry vector.

    Vector layout:
      palm area, palm perimeter, palm centroid x/y,
      five finger curl scores,
      five fingertip distances from wrist,
      thumb-index spread, index-pinky spread, mean visibility.
    """

    mapped = _as_landmark_map(landmarks)
    palm = polygon_points(mapped, HAND_PALM_POLYGON)
    wrist = _point(mapped, HandLandmark.WRIST).xy()
    finger_points = {name: polygon_points(mapped, chain) for name, chain in HAND_FINGERS.items()}
    curls = [finger_curl(finger_points[name]) for name in ("thumb", "index", "middle", "ring", "pinky")]
    tip_indices = (
        HandLandmark.THUMB_TIP,
        HandLandmark.INDEX_TIP,
        HandLandmark.MIDDLE_TIP,
        HandLandmark.RING_TIP,
        HandLandmark.PINKY_TIP,
    )
    tip_distances = [float(np.linalg.norm(_point(mapped, index).xy() - wrist)) for index in tip_indices]
    thumb_index_spread = float(
        np.linalg.norm(_point(mapped, HandLandmark.THUMB_TIP).xy() - _point(mapped, HandLandmark.INDEX_TIP).xy())
    )
    index_pinky_spread = float(
        np.linalg.norm(_point(mapped, HandLandmark.INDEX_TIP).xy() - _point(mapped, HandLandmark.PINKY_TIP).xy())
    )
    visibility = float(np.mean([point.visibility for point in mapped.values()]))
    centroid = polygon_centroid(palm)
    return np.array(
        [
            polygon_area(palm),
            chain_length(np.vstack([palm, palm[0]])),
            centroid[0],
            centroid[1],
            *curls,
            *tip_distances,
            thumb_index_spread,
            index_pinky_spread,
            visibility,
        ],
        dtype=np.float64,
    )


def body_polygon_features(landmarks: Sequence[Landmark] | Mapping[IntEnum, Landmark]) -> np.ndarray:
    """Return a fixed body geometry vector for full-body pose coherence."""

    mapped = _as_landmark_map(landmarks)
    torso = polygon_points(mapped, BODY_TORSO_POLYGON)
    left_shoulder = _point(mapped, BodyLandmark.LEFT_SHOULDER).xy()
    right_shoulder = _point(mapped, BodyLandmark.RIGHT_SHOULDER).xy()
    left_hip = _point(mapped, BodyLandmark.LEFT_HIP).xy()
    right_hip = _point(mapped, BodyLandmark.RIGHT_HIP).xy()
    left_wrist = _point(mapped, BodyLandmark.LEFT_WRIST).xy()
    right_wrist = _point(mapped, BodyLandmark.RIGHT_WRIST).xy()
    left_ankle = _point(mapped, BodyLandmark.LEFT_ANKLE).xy()
    right_ankle = _point(mapped, BodyLandmark.RIGHT_ANKLE).xy()

    chain_angles = []
    chain_lengths = []
    for chain in BODY_CHAINS.values():
        points = polygon_points(mapped, chain)
        chain_lengths.append(chain_length(points))
        chain_angles.append(angle_at(points[0], points[1], points[2]))

    shoulder_width = float(np.linalg.norm(left_shoulder - right_shoulder))
    hip_width = float(np.linalg.norm(left_hip - right_hip))
    body_height = float(max(np.linalg.norm(left_shoulder - left_ankle), np.linalg.norm(right_shoulder - right_ankle)))
    hand_span = float(np.linalg.norm(left_wrist - right_wrist))
    foot_span = float(np.linalg.norm(left_ankle - right_ankle))
    centroid = polygon_centroid(torso)
    visibility = float(np.mean([point.visibility for point in mapped.values()]))

    return np.array(
        [
            polygon_area(torso),
            chain_length(np.vstack([torso, torso[0]])),
            centroid[0],
            centroid[1],
            shoulder_width,
            hip_width,
            body_height,
            hand_span,
            foot_span,
            *chain_lengths,
            *chain_angles,
            visibility,
        ],
        dtype=np.float64,
    )
