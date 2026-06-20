"""Realtime multi-view perception bridge for video lattice control.

This module is the "eyes" layer. It accepts observations from multiple views
or cameras, fuses matching landmarks, preserves uncertainty, and emits a compact
vector for the existing Poincare lattice.

Undefined space is represented explicitly. A missing depth value or weak
confidence does not become fake certainty; it increases the undefined-space
score so downstream renderers can ask for another view, a rerender, or a human
input mark.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence

import numpy as np

from .pose_polygons import Landmark

_EPS = 1e-9


@dataclass(frozen=True)
class CameraView:
    """One camera/view description.

    baseline is a coarse horizontal offset from the reference view. It is enough
    for deterministic disparity scoring without pretending to be full camera
    calibration.
    """

    camera_id: str
    baseline: float = 0.0
    yaw: float = 0.0
    pitch: float = 0.0
    confidence: float = 1.0


@dataclass(frozen=True)
class LandmarkObservation:
    landmark_id: str
    point: Landmark
    confidence: float = 1.0


@dataclass(frozen=True)
class ViewFrame:
    frame_index: int
    camera: CameraView
    landmarks: tuple[LandmarkObservation, ...] = ()
    input_events: tuple[str, ...] = ()


@dataclass(frozen=True)
class FusedLandmark:
    landmark_id: str
    point: Landmark
    view_count: int
    confidence: float
    undefined_depth: float
    disparity: float


@dataclass
class MultiViewState:
    frame_index: int
    fused_landmarks: dict[str, FusedLandmark] = field(default_factory=dict)
    undefined_space_score: float = 1.0
    input_events: list[str] = field(default_factory=list)

    def perception_vector(self) -> np.ndarray:
        """Vector layout for the lattice perception axis.

        count, mean confidence, undefined score, mean disparity, centroid x/y/z,
        input-event pressure.
        """

        if not self.fused_landmarks:
            return np.array([0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, float(len(self.input_events))])

        landmarks = list(self.fused_landmarks.values())
        confidences = np.array([item.confidence for item in landmarks], dtype=np.float64)
        disparities = np.array([item.disparity for item in landmarks], dtype=np.float64)
        points = np.array([item.point.xyz() for item in landmarks], dtype=np.float64)
        centroid = points.mean(axis=0)
        return np.array(
            [
                float(len(landmarks)),
                float(confidences.mean()),
                self.undefined_space_score,
                float(disparities.mean()),
                float(centroid[0]),
                float(centroid[1]),
                float(centroid[2]),
                float(len(self.input_events)),
            ],
            dtype=np.float64,
        )


class MultiViewPerception:
    """Fuse multiple view frames into an uncertainty-aware perception state."""

    def __init__(self, *, min_depth_confidence: float = 0.55) -> None:
        self.min_depth_confidence = min_depth_confidence
        self._history: list[MultiViewState] = []

    def fuse(self, frames: Sequence[ViewFrame]) -> MultiViewState:
        if not frames:
            state = MultiViewState(frame_index=0)
            self._history.append(state)
            return state

        frame_index = frames[0].frame_index
        grouped: dict[str, list[tuple[ViewFrame, LandmarkObservation]]] = {}
        input_events: list[str] = []
        for frame in frames:
            input_events.extend(frame.input_events)
            for obs in frame.landmarks:
                grouped.setdefault(obs.landmark_id, []).append((frame, obs))

        fused: dict[str, FusedLandmark] = {}
        undefined_scores = []
        for landmark_id, observations in grouped.items():
            fused[landmark_id] = self._fuse_landmark(landmark_id, observations)
            undefined_scores.append(fused[landmark_id].undefined_depth)

        if not fused:
            undefined_space_score = 1.0
        else:
            missing_view_penalty = _missing_view_penalty(len(frames), grouped.values())
            undefined_space_score = float(np.clip(np.mean(undefined_scores) + missing_view_penalty, 0.0, 1.0))

        state = MultiViewState(
            frame_index=frame_index,
            fused_landmarks=fused,
            undefined_space_score=undefined_space_score,
            input_events=input_events,
        )
        self._history.append(state)
        return state

    @property
    def history(self) -> list[MultiViewState]:
        return list(self._history)

    def _fuse_landmark(
        self,
        landmark_id: str,
        observations: Sequence[tuple[ViewFrame, LandmarkObservation]],
    ) -> FusedLandmark:
        weights = []
        points = []
        x_by_view = []
        z_defined = []
        for frame, obs in observations:
            weight = max(0.0, min(1.0, obs.confidence * frame.camera.confidence * obs.point.visibility))
            weights.append(weight)
            points.append(obs.point.xyz())
            x_by_view.append((frame.camera.baseline, obs.point.x))
            z_defined.append(abs(obs.point.z) > _EPS and weight >= self.min_depth_confidence)

        weight_arr = np.asarray(weights, dtype=np.float64)
        point_arr = np.asarray(points, dtype=np.float64)
        if float(weight_arr.sum()) <= _EPS:
            fused_point = point_arr.mean(axis=0)
            confidence = 0.0
        else:
            fused_point = np.average(point_arr, weights=weight_arr, axis=0)
            confidence = float(weight_arr.mean())

        disparity = _mean_disparity(x_by_view)
        triangulated_z = _estimate_z_from_disparity(disparity)
        if not any(z_defined) and triangulated_z is not None:
            fused_point[2] = triangulated_z

        undefined_depth = _undefined_depth_score(
            view_count=len(observations),
            confidence=confidence,
            has_defined_depth=any(z_defined) or triangulated_z is not None,
        )
        return FusedLandmark(
            landmark_id=landmark_id,
            point=Landmark(float(fused_point[0]), float(fused_point[1]), float(fused_point[2]), confidence),
            view_count=len(observations),
            confidence=confidence,
            undefined_depth=undefined_depth,
            disparity=disparity,
        )


def make_view_frame(
    frame_index: int,
    camera_id: str,
    landmarks: Mapping[str, Landmark] | Iterable[LandmarkObservation],
    *,
    baseline: float = 0.0,
    confidence: float = 1.0,
    input_events: Iterable[str] = (),
) -> ViewFrame:
    if isinstance(landmarks, Mapping):
        observations = tuple(
            LandmarkObservation(landmark_id=key, point=value, confidence=value.visibility)
            for key, value in landmarks.items()
        )
    else:
        observations = tuple(landmarks)
    return ViewFrame(
        frame_index=frame_index,
        camera=CameraView(camera_id=camera_id, baseline=baseline, confidence=confidence),
        landmarks=observations,
        input_events=tuple(input_events),
    )


def _mean_disparity(x_by_view: Sequence[tuple[float, float]]) -> float:
    if len(x_by_view) < 2:
        return 0.0
    ordered = sorted(x_by_view, key=lambda item: item[0])
    disparities = [abs(ordered[i + 1][1] - ordered[i][1]) for i in range(len(ordered) - 1)]
    return float(np.mean(disparities)) if disparities else 0.0


def _estimate_z_from_disparity(disparity: float) -> float | None:
    if disparity <= _EPS:
        return None
    # Coarse normalized inverse-depth estimate: high disparity means closer.
    return float(1.0 / (1.0 + disparity))


def _undefined_depth_score(view_count: int, confidence: float, has_defined_depth: bool) -> float:
    if has_defined_depth and view_count >= 2 and confidence >= 0.75:
        return 0.0
    score = 0.0
    if view_count < 2:
        score += 0.45
    if not has_defined_depth:
        score += 0.35
    if confidence < 0.75:
        score += 0.75 - confidence
    return float(np.clip(score, 0.0, 1.0))


def _missing_view_penalty(
    total_views: int, grouped_values: Iterable[Sequence[tuple[ViewFrame, LandmarkObservation]]]
) -> float:
    if total_views <= 1:
        return 0.25
    penalties = [1.0 - (len(group) / total_views) for group in grouped_values]
    return float(0.25 * np.mean(penalties)) if penalties else 0.0
