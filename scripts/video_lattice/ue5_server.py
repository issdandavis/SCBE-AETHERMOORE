"""
UE5 server — paste and run inside UE5's Python console.

  Window → Developer Tools → Python Console
  >>> exec(open(r"C:\\Users\\issda\\SCBE-AETHERMOORE\\scripts\\video_lattice\\ue5_server.py").read())

Listens on 127.0.0.1:7621 for correction and pose-check signals from UE5Bridge.
Runs as a background daemon thread so the UE5 editor stays responsive.

Message types handled:
  ping        → reply ok
  reset       → clear accumulated correction state
  correction  → apply FrameCorrector signal to camera/render settings
  pose_check  → log drift and optionally re-pose selected skeleton
  raw         → execute arbitrary unreal Python expression (DEBUG only)

SECURITY: bind to 127.0.0.1 only. Do NOT expose this port externally.
          "raw" type is disabled in production mode (set ALLOW_RAW = False).
"""
from __future__ import annotations

import json
import socket
import threading
import traceback

# ------------------------------------------------------------------ #
#  Config — edit these before running
# ------------------------------------------------------------------ #
HOST = "127.0.0.1"
PORT = 7621
ALLOW_RAW = False    # set True only during local development

# ------------------------------------------------------------------ #
#  UE5 API imports (only available inside UE5's Python interpreter)
# ------------------------------------------------------------------ #
try:
    import unreal
    _HAS_UNREAL = True
except ImportError:
    _HAS_UNREAL = False
    print("[ue5_server] WARNING: 'unreal' module not found. Running in stub mode.")

# ------------------------------------------------------------------ #
#  Correction state — accumulated between frames
# ------------------------------------------------------------------ #
_state: dict = {
    "frames_received": 0,
    "last_severity": "none",
    "last_drift": 0.0,
    "corrections_applied": 0,
}


def _console(cmd: str) -> None:
    """Execute a UE5 console command."""
    if _HAS_UNREAL:
        unreal.SystemLibrary.execute_console_command(None, cmd)
    else:
        print(f"[ue5_server stub] console: {cmd}")


def _log(msg: str) -> None:
    if _HAS_UNREAL:
        unreal.log(f"[ue5_bridge] {msg}")
    else:
        print(f"[ue5_server] {msg}")


# ------------------------------------------------------------------ #
#  Handlers
# ------------------------------------------------------------------ #

def _handle_ping(payload: dict) -> dict:
    return {"msg": f"pong — UE5 server alive, frames={_state['frames_received']}"}


def _handle_reset(payload: dict) -> dict:
    _state["frames_received"] = 0
    _state["corrections_applied"] = 0
    _state["last_severity"] = "none"
    _state["last_drift"] = 0.0
    return {"msg": "state reset"}


def _handle_correction(payload: dict) -> dict:
    """Apply a FrameCorrector correction signal to UE5 render settings."""
    _state["frames_received"] += 1
    severity = payload.get("severity", "none")
    drift = payload.get("drift", 0.0)
    _state["last_severity"] = severity
    _state["last_drift"] = drift

    ue5 = payload.get("ue5", {})
    msgs = []

    if ue5.get("apply_motion_blur_correction"):
        # Reduce motion blur strength when motion axis is drifting
        strength = max(0.0, 1.0 - min(drift * 0.3, 1.0))
        _console(f"r.MotionBlur.Amount {strength:.3f}")
        msgs.append(f"motion_blur={strength:.3f}")

    if ue5.get("apply_depth_correction"):
        # Increase DOF quality to compensate for depth drift
        _console("r.DepthOfFieldQuality 2")
        msgs.append("dof_quality=2")

    if ue5.get("suggest_keyframe"):
        # Mark this frame as a forced keyframe in the sequencer
        # In a real integration: unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(...)
        _log(f"[keyframe] forced at frame {payload.get('frame', '?')}, severity={severity}")
        msgs.append("keyframe_forced")

    prio = ue5.get("rerender_priority", 0)
    if prio >= 2:
        # Boost screen percentage for severe drift frames
        pct = 100 + prio * 25  # 2→150%, 3→175%
        _console(f"r.ScreenPercentage {pct}")
        msgs.append(f"screen_pct={pct}")
    elif _state["corrections_applied"] > 0:
        # Restore default after a correction frame passes
        _console("r.ScreenPercentage 100")

    if msgs:
        _state["corrections_applied"] += 1
        _log(f"correction applied: {', '.join(msgs)}")

    return {"msg": f"correction applied (severity={severity}, drift={drift:.4f})"}


def _handle_pose_check(payload: dict) -> dict:
    """Handle a PoseChecker result — log drift, optionally flag for review."""
    _state["frames_received"] += 1
    verdict = payload.get("verdict", "pass")
    drift = payload.get("overall_drift", 0.0)
    worst = payload.get("worst_chain", "unknown")
    pose_type = payload.get("pose_type", "?")

    _log(f"pose_check [{pose_type}] verdict={verdict} drift={drift:.4f} worst={worst}")

    if verdict in ("soft", "hard"):
        # In a full integration: find the skeletal mesh actor and call
        # actor.set_morph_target_value() or drive an AnimBlueprint variable.
        # Here we log the correction hint so a BP variable can pick it up.
        correction = payload.get("correction_vector")
        if correction:
            # Blueprint-accessible via a GameInstance variable set via Python
            if _HAS_UNREAL:
                try:
                    gi = unreal.GameplayStatics.get_game_instance(None)
                    if gi and hasattr(gi, "set_editor_property"):
                        gi.set_editor_property("last_pose_correction_drift", drift)
                except Exception:
                    pass  # editor context may not have a game instance

    if verdict == "hard":
        _console("r.ScreenPercentage 150")  # boost quality on hard failure

    return {"msg": f"pose_check logged (verdict={verdict}, drift={drift:.4f})"}


def _handle_raw(payload: dict) -> dict:
    """Execute arbitrary Python in the UE5 interpreter (DEBUG only)."""
    if not ALLOW_RAW:
        return {"msg": "raw disabled — set ALLOW_RAW=True to enable"}
    expr = payload.get("expr", "")
    try:
        result = eval(compile(expr, "<ue5_bridge>", "eval"))  # noqa: S307
        return {"msg": str(result)}
    except Exception:
        return {"msg": traceback.format_exc()}


_HANDLERS = {
    "ping": _handle_ping,
    "reset": _handle_reset,
    "correction": _handle_correction,
    "pose_check": _handle_pose_check,
    "raw": _handle_raw,
}


# ------------------------------------------------------------------ #
#  Server loop
# ------------------------------------------------------------------ #

def _serve_client(conn: socket.socket, addr: tuple) -> None:
    _log(f"client connected from {addr}")
    buf = b""
    try:
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                if not line.strip():
                    continue
                try:
                    msg = json.loads(line.decode("utf-8"))
                except json.JSONDecodeError as exc:
                    resp = {"status": "error", "seq": -1, "msg": f"JSON parse error: {exc}"}
                    conn.sendall((json.dumps(resp) + "\n").encode())
                    continue

                seq = msg.get("seq", -1)
                msg_type = msg.get("type", "unknown")
                handler = _HANDLERS.get(msg_type)
                try:
                    if handler is None:
                        result = {"msg": f"unknown type: {msg_type!r}"}
                        status = "error"
                    else:
                        result = handler(msg.get("payload", {}))
                        status = "ok"
                except Exception as exc:
                    result = {"msg": traceback.format_exc()}
                    status = "error"
                    _log(f"handler error ({msg_type}): {exc}")

                resp = {"status": status, "seq": seq, **result}
                conn.sendall((json.dumps(resp) + "\n").encode())
    except OSError:
        pass
    finally:
        conn.close()
        _log(f"client disconnected from {addr}")


def _server_loop(server_sock: socket.socket) -> None:
    _log(f"UE5 bridge listening on {HOST}:{PORT}")
    while True:
        try:
            conn, addr = server_sock.accept()
            t = threading.Thread(target=_serve_client, args=(conn, addr), daemon=True)
            t.start()
        except OSError:
            break


# ------------------------------------------------------------------ #
#  Entry point — called when exec()'d in UE5 Python console
# ------------------------------------------------------------------ #

def start_server(port: int = PORT) -> threading.Thread:
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((HOST, port))
    server_sock.listen(4)
    t = threading.Thread(target=_server_loop, args=(server_sock,), daemon=True)
    t.start()
    _log(f"server thread started (port={port})")
    return t


# Auto-start when exec()'d directly in the UE5 Python console
_server_thread = start_server()
print(f"[ue5_server] started on {HOST}:{PORT}  (thread={_server_thread.name})")
print(f"[ue5_server] from your Python session: bridge.connect() on port {PORT}")
