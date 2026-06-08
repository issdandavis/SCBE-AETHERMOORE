from __future__ import annotations

import json
import math
import socket
import threading
import time
from pathlib import Path

import numpy as np

from src.video_lattice import (
    BodyLandmark,
    HandLandmark,
    Landmark,
    LatticeAxis,
    LocalVectorIndex,
    make_view_frame,
    MultiLattice,
    MultiViewPerception,
    PerspectiveMap,
    PoincareLattice,
    PoseChecker,
    PoseVerdict,
    RoundTableDirector,
    WorldDirector,
    demo_world,
    UE5Bridge,
    UE5BridgeError,
    render_body_sketch,
    render_hand_sketch,
    TemporalTracker,
    body_polygon_features,
    hand_polygon_features,
)
from src.video_lattice.frame_corrector import CorrectionSignal
from src.video_lattice.gpt_world import _world_feature_vector


def test_poincare_lattice_embeds_inside_open_ball() -> None:
    lattice = PoincareLattice(dim=3)
    point = lattice.embed(np.array([100.0, 0.0, 0.0]))
    assert np.linalg.norm(point) < 1.0


def test_poincare_distance_is_symmetric() -> None:
    lattice = PoincareLattice(dim=2)
    a = lattice.embed(np.array([0.2, 0.1]))
    b = lattice.embed(np.array([0.7, -0.2]))
    assert lattice.distance(a, b) == pytest_approx(lattice.distance(b, a))


def test_multi_lattice_triggers_correction_on_large_shift() -> None:
    tracker = TemporalTracker(MultiLattice(dim=2, correction_threshold=0.5))
    base = {
        LatticeAxis.IDENTITY: np.array([0.1, 0.1]),
        LatticeAxis.MOTION: np.array([0.1, 0.0]),
    }
    shifted = {
        LatticeAxis.IDENTITY: np.array([6.0, 6.0]),
        LatticeAxis.MOTION: np.array([6.0, 0.0]),
    }

    first = tracker.observe(base)
    second = tracker.observe(shifted)

    assert first.correction_triggered is False
    assert second.aggregate_drift > first.aggregate_drift
    assert second.correction_triggered is True
    assert tracker.correction_events() == [second]


def test_perspective_depth_moves_toward_boundary() -> None:
    pmap = PerspectiveMap(max_depth=10.0)
    near = pmap.project(depth=1.0, angle=0.0)
    far = pmap.project(depth=10.0, angle=0.0)

    assert 0.0 <= near.radius < far.radius < 1.0
    assert np.linalg.norm(far.point) < 1.0


def test_perspective_xy_depth_uses_screen_angle() -> None:
    pmap = PerspectiveMap(max_depth=10.0)
    point = pmap.project_xy_depth(0.0, 1.0, 5.0)
    radius, angle = pmap.polar(point.point)

    assert radius == pytest_approx(point.radius)
    assert angle == pytest_approx(math.pi / 2)


def test_hand_features_represent_thumb_and_four_fingers() -> None:
    open_hand = synthetic_hand(curl=0.0)
    fist = synthetic_hand(curl=0.75)

    open_features = hand_polygon_features(open_hand)
    fist_features = hand_polygon_features(fist)

    # palm area, perimeter, centroid x/y, 5 curls, 5 fingertip distances,
    # 2 spread measures, mean visibility
    assert open_features.shape == (17,)
    assert fist_features.shape == (17,)
    assert np.mean(open_features[4:9]) < np.mean(fist_features[4:9])
    assert np.mean(open_features[9:14]) > np.mean(fist_features[9:14])


def test_body_features_feed_structure_lattice() -> None:
    tracker = TemporalTracker(MultiLattice(dim=17, correction_threshold=0.5))
    standing = body_polygon_features(synthetic_body(arm_raise=0.0))
    jump_cut = body_polygon_features(synthetic_body(arm_raise=0.9, x_shift=3.0))

    first = tracker.observe({LatticeAxis.STRUCTURE: standing})
    second = tracker.observe({LatticeAxis.STRUCTURE: jump_cut})

    assert standing.shape == (18,)
    assert first.correction_triggered is False
    assert second.aggregate_drift > first.aggregate_drift
    assert second.correction_triggered is True


def test_sketch_pad_renders_hand_and_body_svg() -> None:
    hand_svg = render_hand_sketch(synthetic_hand(curl=0.2)).render_svg()
    body_svg = render_body_sketch(synthetic_body(arm_raise=0.2)).render_svg()

    assert "<svg" in hand_svg
    assert "thumb" in hand_svg
    assert "index" in hand_svg
    assert "<polygon" in body_svg
    assert "left_arm" in body_svg


def test_multiview_perception_reduces_undefined_depth() -> None:
    left = make_view_frame(
        0,
        "left",
        {"wrist": Landmark(0.40, 0.50, visibility=0.95)},
        baseline=-0.1,
        input_events=("mouse_drag",),
    )
    right = make_view_frame(
        0,
        "right",
        {"wrist": Landmark(0.46, 0.50, visibility=0.95)},
        baseline=0.1,
    )

    state = MultiViewPerception().fuse([left, right])
    fused = state.fused_landmarks["wrist"]

    assert fused.view_count == 2
    assert fused.disparity > 0
    assert fused.point.z > 0
    assert state.undefined_space_score < 0.2
    assert state.input_events == ["mouse_drag"]
    assert state.perception_vector().shape == (8,)


def test_single_view_perception_keeps_undefined_space_high() -> None:
    view = make_view_frame(
        0,
        "front",
        {"wrist": Landmark(0.40, 0.50, visibility=0.8)},
        baseline=0.0,
    )

    state = MultiViewPerception().fuse([view])

    assert state.fused_landmarks["wrist"].view_count == 1
    assert state.undefined_space_score > 0.5


def test_local_vector_index_returns_best_cosine_match(tmp_path) -> None:
    index = LocalVectorIndex(dim=3)
    index.add("frame_red_bag", [1.0, 0.0, 0.0], metadata={"timestamp": 12.0, "label": "red bag"})
    index.add("frame_blue_car", [0.0, 1.0, 0.0], metadata={"timestamp": 24.0, "label": "blue car"})
    index.add("transcript_bag", [0.9, 0.1, 0.0], modality="transcript", metadata={"timestamp": 13.0})

    results = index.search([0.95, 0.05, 0.0], top_k=2, modality="frame")

    assert results[0].record_id == "frame_red_bag"
    assert results[0].score > results[1].score

    saved = index.save(tmp_path / "index.json")
    loaded = LocalVectorIndex.load(saved)
    assert loaded.search([0.0, 1.0, 0.0], top_k=1)[0].record_id == "frame_blue_car"


def test_tiny_world_renders_pocket_dimension_and_round_trips(tmp_path) -> None:
    world = demo_world()
    rows = world.to_symbol_grid()

    assert world.pocket_id == "pocket.aether.video_lattice.demo"
    assert rows[2][2] == "@"
    assert rows[2][8] == "*"
    assert world.move_entity("hero", dx=1) is True
    assert world.move_entity("hero", dx=-3) is False

    svg = world.render_svg()
    assert "<svg" in svg
    assert "@" in svg

    saved = world.save_json(tmp_path / "world.json")
    loaded = world.load_json(saved)
    assert loaded.pocket_id == world.pocket_id
    assert loaded.to_symbol_grid() == world.to_symbol_grid()


def synthetic_hand(curl: float = 0.0) -> list[Landmark]:
    landmarks = [Landmark(0.0, 0.0) for _ in range(21)]
    landmarks[HandLandmark.WRIST] = Landmark(0.0, 0.0)
    bases = {
        HandLandmark.THUMB_CMC: (-0.24, 0.12),
        HandLandmark.INDEX_MCP: (-0.12, 0.30),
        HandLandmark.MIDDLE_MCP: (0.00, 0.34),
        HandLandmark.RING_MCP: (0.12, 0.30),
        HandLandmark.PINKY_MCP: (0.24, 0.24),
    }
    chains = [
        (HandLandmark.THUMB_CMC, HandLandmark.THUMB_MCP, HandLandmark.THUMB_IP, HandLandmark.THUMB_TIP),
        (HandLandmark.INDEX_MCP, HandLandmark.INDEX_PIP, HandLandmark.INDEX_DIP, HandLandmark.INDEX_TIP),
        (HandLandmark.MIDDLE_MCP, HandLandmark.MIDDLE_PIP, HandLandmark.MIDDLE_DIP, HandLandmark.MIDDLE_TIP),
        (HandLandmark.RING_MCP, HandLandmark.RING_PIP, HandLandmark.RING_DIP, HandLandmark.RING_TIP),
        (HandLandmark.PINKY_MCP, HandLandmark.PINKY_PIP, HandLandmark.PINKY_DIP, HandLandmark.PINKY_TIP),
    ]
    for chain in chains:
        base = chain[0]
        x, y = bases[base]
        landmarks[base] = Landmark(x, y)
        for step, joint in enumerate(chain[1:], start=1):
            folded_x = x + (0.05 * step) * np.sign(x if x else 1.0)
            straight_y = y + 0.20 * step
            folded_y = y + (0.10, 0.08, 0.02)[step - 1]
            landmarks[joint] = Landmark(
                float((1.0 - curl) * x + curl * folded_x),
                float((1.0 - curl) * straight_y + curl * folded_y),
            )
    return landmarks


def synthetic_body(arm_raise: float = 0.0, x_shift: float = 0.0) -> list[Landmark]:
    landmarks = [Landmark(x_shift, 0.0) for _ in range(33)]
    coords = {
        BodyLandmark.NOSE: (0.0, 0.0),
        BodyLandmark.LEFT_SHOULDER: (-0.4, 0.6),
        BodyLandmark.RIGHT_SHOULDER: (0.4, 0.6),
        BodyLandmark.LEFT_ELBOW: (-0.7, 1.0 - arm_raise),
        BodyLandmark.RIGHT_ELBOW: (0.7, 1.0 - arm_raise),
        BodyLandmark.LEFT_WRIST: (-0.8, 1.4 - 1.6 * arm_raise),
        BodyLandmark.RIGHT_WRIST: (0.8, 1.4 - 1.6 * arm_raise),
        BodyLandmark.LEFT_HIP: (-0.3, 1.6),
        BodyLandmark.RIGHT_HIP: (0.3, 1.6),
        BodyLandmark.LEFT_KNEE: (-0.3, 2.3),
        BodyLandmark.RIGHT_KNEE: (0.3, 2.3),
        BodyLandmark.LEFT_ANKLE: (-0.3, 3.0),
        BodyLandmark.RIGHT_ANKLE: (0.3, 3.0),
    }
    for key, (x, y) in coords.items():
        landmarks[key] = Landmark(x + x_shift, y)
    return landmarks


def test_pose_checker_identical_hand_passes() -> None:
    hand = synthetic_hand(curl=0.3)
    checker = PoseChecker()
    result = checker.check_hand(hand, hand)

    assert result.verdict == PoseVerdict.PASS
    assert result.overall_drift == pytest_approx(0.0)


def test_pose_checker_fist_vs_open_hand_fails() -> None:
    open_hand = synthetic_hand(curl=0.0)
    fist = synthetic_hand(curl=0.9)
    checker = PoseChecker(soft_threshold=0.1)
    result = checker.check_hand(open_hand, fist)

    assert result.verdict in (PoseVerdict.SOFT_FAIL, PoseVerdict.HARD_FAIL)
    assert result.overall_drift > 0.0
    assert result.worst_chain is not None
    assert len(result.chain_checks) == 5  # one per finger


def test_pose_checker_body_arm_raise_detected() -> None:
    arms_down = synthetic_body(arm_raise=0.0)
    arms_up = synthetic_body(arm_raise=1.0)
    checker = PoseChecker(soft_threshold=0.01)
    result = checker.check_body(arms_down, arms_up)

    assert result.verdict in (PoseVerdict.SOFT_FAIL, PoseVerdict.HARD_FAIL)
    assert result.worst_chain in ("left_arm", "right_arm")


def test_pose_checker_correction_vector_points_toward_reference() -> None:
    reference = synthetic_hand(curl=0.0)
    generated = synthetic_hand(curl=0.8)
    checker = PoseChecker()
    result = checker.check_hand(reference, generated)

    assert result.correction_vector is not None
    assert result.correction_vector.shape[0] == 17  # feature dim for hand


def test_pose_check_result_serializes() -> None:
    reference = synthetic_body(arm_raise=0.0)
    generated = synthetic_body(arm_raise=0.5)
    checker = PoseChecker()
    result = checker.check_body(reference, generated)
    d = result.to_dict()

    assert d["pose_type"] == "body"
    assert "overall_drift" in d
    assert "verdict" in d
    assert isinstance(d["chain_checks"], list)


def test_ue5_bridge_raises_when_no_server() -> None:
    bridge = UE5Bridge(port=7699, timeout=0.3, auto_reconnect=False)
    try:
        bridge.connect()
        assert False, "expected UE5BridgeError"
    except UE5BridgeError:
        pass


def test_ue5_bridge_ping_pong_via_stub_server() -> None:
    """Start a minimal stub server, send a ping, verify pong."""
    port = _find_free_port()
    server = _StubUE5Server(port)
    server.start()
    time.sleep(0.05)

    try:
        bridge = UE5Bridge(port=port, timeout=2.0, auto_reconnect=False)
        bridge.connect()
        resp = bridge.ping()
        assert resp.status == "ok"
        assert resp.latency_ms >= 0
    finally:
        server.stop()
        bridge.close()


def test_ue5_bridge_send_correction_via_stub() -> None:
    port = _find_free_port()
    server = _StubUE5Server(port)
    server.start()
    time.sleep(0.05)

    try:
        bridge = UE5Bridge(port=port, timeout=2.0)
        bridge.connect()
        sig = CorrectionSignal(
            frame_index=5,
            aggregate_drift=2.8,
            cost_signal=1.618 ** (2.8**2),
            axis_corrections={"motion": -1.2, "depth": -0.3},
            latent_nudge=None,
            condition_signal={
                "severity": "moderate",
                "ue5": {
                    "rerender_priority": 2,
                    "apply_motion_blur_correction": True,
                    "apply_depth_correction": False,
                    "suggest_keyframe": False,
                },
            },
            severity="moderate",
        )
        resp = bridge.send_correction(sig)
        assert resp.status == "ok"
        assert server.last_received["type"] == "correction"
        assert server.last_received["payload"]["frame"] == 5
    finally:
        server.stop()
        bridge.close()


def test_ue5_bridge_send_pose_check_via_stub() -> None:
    port = _find_free_port()
    server = _StubUE5Server(port)
    server.start()
    time.sleep(0.05)

    try:
        bridge = UE5Bridge(port=port, timeout=2.0)
        bridge.connect()
        checker = PoseChecker()
        result = checker.check_hand(synthetic_hand(curl=0.0), synthetic_hand(curl=0.8))
        resp = bridge.send_pose_check(result)
        assert resp.status == "ok"
        assert server.last_received["type"] == "pose_check"
        payload = server.last_received["payload"]
        assert payload["pose_type"] == "hand"
        assert "verdict" in payload
    finally:
        server.stop()
        bridge.close()


# ------------------------------------------------------------------
# Stub UE5 server for testing (no unreal dependency)
# ------------------------------------------------------------------


class _StubUE5Server:
    def __init__(self, port: int) -> None:
        self.port = port
        self.last_received: dict = {}
        self._sock: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def start(self) -> None:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("127.0.0.1", self.port))
        self._sock.listen(2)
        self._sock.settimeout(0.5)
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._sock:
            self._sock.close()

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                conn, _ = self._sock.accept()
            except OSError:
                break
            self._serve(conn)

    def _serve(self, conn: socket.socket) -> None:
        buf = b""
        conn.settimeout(1.0)
        try:
            while not self._stop.is_set():
                try:
                    chunk = conn.recv(4096)
                except OSError:
                    break
                if not chunk:
                    break
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    if not line.strip():
                        continue
                    try:
                        msg = json.loads(line.decode())
                    except json.JSONDecodeError:
                        continue
                    self.last_received = msg
                    seq = msg.get("seq", -1)
                    resp = json.dumps({"status": "ok", "seq": seq, "msg": "stub_ok"}) + "\n"
                    conn.sendall(resp.encode())
        finally:
            conn.close()


def _find_free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_world_feature_vector_changes_when_world_changes() -> None:
    world = demo_world()
    v1 = _world_feature_vector(world)
    world.move_entity("hero", dx=1, dy=0)
    v2 = _world_feature_vector(world)
    assert not np.allclose(v1, v2), "feature vector should change on entity move"
    assert v1.shape == v2.shape


def test_world_feature_vector_is_fixed_length_across_worlds() -> None:
    world_a = demo_world()
    world_b = demo_world()
    world_b.move_entity("hero", dx=2, dy=1)
    assert _world_feature_vector(world_a).shape == _world_feature_vector(world_b).shape


def test_world_director_apply_delta_move() -> None:
    world = demo_world()
    director = WorldDirector.__new__(WorldDirector)
    director.model = "stub"
    initial_x = world.entities["hero"].x
    initial_y = world.entities["hero"].y

    from src.video_lattice.gpt_world import WorldCommand, WorldDelta

    delta = WorldDelta(
        commands=[WorldCommand(type="move", data={"entity_id": "hero", "dx": 1, "dy": 0})],
        narrative="The hero steps east.",
        model="stub",
        raw_response="{}",
    )
    director.apply_delta(world, delta)
    assert world.entities["hero"].x == initial_x + 1
    assert world.entities["hero"].y == initial_y


def test_world_director_apply_delta_skips_solid_moves() -> None:
    world = demo_world()
    director = WorldDirector.__new__(WorldDirector)
    director.model = "stub"

    from src.video_lattice.gpt_world import WorldCommand, WorldDelta

    # hero is at (2,2); wall is at (0,y) — move hero left until wall
    delta = WorldDelta(
        commands=[WorldCommand(type="move", data={"entity_id": "hero", "dx": -3, "dy": 0})],
        narrative="Hero charges at the wall.",
        model="stub",
        raw_response="{}",
    )
    skipped = director.apply_delta(world, delta)
    # Either blocked by solid tile or out of bounds — either way skipped is populated
    # or hero stays >= 1 (wall at x=0)
    assert world.entities["hero"].x >= 1


def test_world_director_score_delta_no_op_is_zero() -> None:
    world = demo_world()
    director = WorldDirector.__new__(WorldDirector)
    director.model = "stub"

    from src.video_lattice.gpt_world import WorldDelta

    delta = WorldDelta(commands=[], narrative="Nothing happens.", model="stub", raw_response="{}")
    drift = director.score_delta(world, delta)
    assert drift == pytest_approx(0.0)


def test_world_director_score_delta_move_is_positive() -> None:
    world = demo_world()
    director = WorldDirector.__new__(WorldDirector)
    director.model = "stub"

    from src.video_lattice.gpt_world import WorldCommand, WorldDelta

    delta = WorldDelta(
        commands=[WorldCommand(type="move", data={"entity_id": "hero", "dx": 1, "dy": 0})],
        narrative="Hero moves.",
        model="stub",
        raw_response="{}",
    )
    drift = director.score_delta(world, delta)
    assert drift > 0.0


def test_round_table_director_picks_most_coherent() -> None:
    """Mock two directors: one no-op (drift=0) and one large move (drift>0).
    Round table should pick the no-op."""
    from src.video_lattice.gpt_world import WorldCommand, WorldDelta

    class _NoOpDirector(WorldDirector):
        def __init__(self):
            self.model = "stub-noop"
            self.temperature = 0.0
            self.max_tokens = 64
            self._api_key = None
            self._client = None

        def step(self, world, note=""):
            return WorldDelta(commands=[], narrative="Nothing.", model=self.model, raw_response="{}")

    class _MoveDirector(WorldDirector):
        def __init__(self):
            self.model = "stub-mover"
            self.temperature = 0.0
            self.max_tokens = 64
            self._api_key = None
            self._client = None

        def step(self, world, note=""):
            return WorldDelta(
                commands=[WorldCommand(type="move", data={"entity_id": "hero", "dx": 1, "dy": 0})],
                narrative="Hero moves.",
                model=self.model,
                raw_response="{}",
            )

    world = demo_world()
    table = RoundTableDirector([_MoveDirector(), _NoOpDirector()])
    best_delta, report = table.step(world, "what happens?")

    assert report.winner_model == "stub-noop"
    assert report.winner_drift == pytest_approx(0.0)
    assert len(report.all_results) == 2


def test_pocket_drawing_tutor_writes_trace_artifacts(tmp_path) -> None:
    from scripts.video_lattice.pocket_drawing_tutor import run_lesson

    payload = run_lesson("hand", "open", Path(tmp_path))

    assert payload["lesson"] == "hand open"
    assert Path(payload["target_svg"]).exists()
    assert Path(payload["attempt_svg"]).exists()
    assert Path(payload["target_png"]).exists()
    assert Path(payload["attempt_png"]).exists()
    assert payload["score"]["pose_type"] == "hand"
    assert payload["score"]["worst_chain"] in {"thumb", "index", "middle", "ring", "pinky"}
    assert "Repair one thing" in payload["repair"]


def test_pocket_video_gen_writes_animation_and_reduces_drift(tmp_path) -> None:
    from scripts.video_lattice.pocket_video_gen import run_generation

    manifest = run_generation("hand", "fist", frames=5, out_dir=Path(tmp_path), duration_ms=20)

    gif_path = Path(manifest["animation_gif"])
    assert gif_path.exists()
    assert gif_path.suffix == ".gif"
    assert manifest["frame_count"] == 5
    assert len(manifest["frames"]) == 5
    assert manifest["frames"][0]["drift"] > manifest["frames"][-1]["drift"]
    assert manifest["frames"][-1]["verdict"] == "pass"


# ------------------------------------------------------------------
# Intent anchor — trijective audit triangle tests
# ------------------------------------------------------------------


def test_intent_anchor_no_drift_when_aligned() -> None:
    tracker = TemporalTracker(MultiLattice(dim=4, correction_threshold=5.0), intent_threshold=0.5)
    anchor_vec = np.array([0.3, 0.1, -0.2, 0.4])
    tracker.set_intent_anchor({LatticeAxis.IDENTITY: anchor_vec}, description="test pose")
    # Observing the same vector as the anchor — intent drift must be zero
    state = tracker.observe({LatticeAxis.IDENTITY: anchor_vec})
    assert LatticeAxis.IDENTITY in state.intent_drift_by_axis
    assert state.intent_drift_by_axis[LatticeAxis.IDENTITY] == pytest_approx(0.0, abs=1e-9)
    assert state.intent_violated is False


def test_intent_anchor_detects_violation_on_large_shift() -> None:
    tracker = TemporalTracker(MultiLattice(dim=4, correction_threshold=5.0), intent_threshold=0.1)
    anchor = np.array([0.1, 0.0, 0.0, 0.0])
    shifted = np.array([5.0, 5.0, 5.0, 5.0])
    tracker.set_intent_anchor({LatticeAxis.IDENTITY: anchor}, description="closed fist")
    state = tracker.observe({LatticeAxis.IDENTITY: shifted})
    assert state.intent_violated is True
    assert state.intent_drift_by_axis[LatticeAxis.IDENTITY] > 0.1
    assert len(tracker.intent_violations()) == 1
    assert tracker.summary()["intent_violations"] == 1
    assert tracker.summary()["intent_anchor"] == "closed fist"


def test_intent_anchor_cleared_stops_reporting() -> None:
    tracker = TemporalTracker(MultiLattice(dim=4, correction_threshold=5.0), intent_threshold=0.1)
    anchor = np.array([0.1, 0.0, 0.0, 0.0])
    tracker.set_intent_anchor({LatticeAxis.IDENTITY: anchor})
    # Observe a shifted frame while anchor is set — should report drift
    state_with = tracker.observe({LatticeAxis.IDENTITY: np.array([5.0, 5.0, 5.0, 5.0])})
    assert LatticeAxis.IDENTITY in state_with.intent_drift_by_axis
    # Remove anchor
    tracker.clear_intent_anchor()
    assert tracker.intent_anchor is None
    # Next observation must have no intent drift
    state_without = tracker.observe({LatticeAxis.IDENTITY: np.array([5.0, 5.0, 5.0, 5.0])})
    assert state_without.intent_drift_by_axis == {}
    assert state_without.intent_violated is False


def test_intent_anchor_surfaced_in_correction_signal() -> None:
    from src.video_lattice.frame_corrector import FrameCorrector

    tracker = TemporalTracker(MultiLattice(dim=4, correction_threshold=5.0), intent_threshold=0.1)
    corrector = FrameCorrector(tracker)
    anchor = np.array([0.1, 0.0, 0.0, 0.0])
    tracker.set_intent_anchor({LatticeAxis.IDENTITY: anchor}, description="closed fist")
    state = tracker.observe({LatticeAxis.IDENTITY: np.array([5.0, 5.0, 5.0, 5.0])})
    sig = corrector.correct(state)

    assert sig.intent_violated is True
    assert sig.intent_drift > 0.0
    assert sig.intent_description == "closed fist"
    assert sig.condition_signal["intent"]["violated"] is True
    assert sig.condition_signal["intent"]["description"] == "closed fist"
    assert sig.condition_signal["intent"]["max_drift"] > 0.0
    # UE5 dict exposes the intent flag
    ue5 = sig.to_ue5_dict()
    assert ue5["intent_violated"] is True
    assert ue5["intent_drift"] > 0.0


def pytest_approx(value: float, abs: float = 1e-9):
    import pytest

    return pytest.approx(value, rel=1e-9, abs=abs)
