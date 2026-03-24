"""
HYDRA Android Hand — ADB-first control loop for emulator and phone operation.

This mirrors the browser-native HYDRA hand with a device-native lane:
    KO — orchestration and status
    AV — launch/navigation
    RU — key events / recovery
    CA — captures and observation
    UM — motion / scrolling
    DR — UI dump / structuring

The primary target is webtoon previewing inside the Android shell, with
deterministic screenshot and UI-dump artifacts under:
    artifacts/kindle/control_loop/<session_id>/
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from src.browser.hydra_hand import Proximity, TONGUE_PROXIMITY, TONGUE_WEIGHT, Tongue


DEFAULT_PACKAGE = "com.issdandavis.aethercode"
DEFAULT_READER_ROUTE = "http://10.0.2.2:8088/polly-pad.html"

ADB_FALLBACKS = (
    os.environ.get("ANDROID_SDK_ROOT", ""),
    os.environ.get("ANDROID_HOME", ""),
    r"C:\Users\issda\AppData\Local\Android\Sdk",
    r"C:\Users\issda\android-sdk",
)

ADB_DEVICE_LINE_RE = re.compile(r"^(?P<serial>\S+)\s+(?P<state>\S+)(?:\s+(?P<meta>.+))?$")
WM_DIMENSION_RE = re.compile(r"(?P<width>\d+)x(?P<height>\d+)")
TOP_ACTIVITY_RE = re.compile(r"([A-Za-z0-9_.]+)/([A-Za-z0-9_.$]+)")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp_slug() -> str:
    return _utc_now().strftime("%Y%m%dT%H%M%SZ")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_artifact_root() -> Path:
    return _repo_root() / "artifacts" / "kindle" / "control_loop"


def _android_user_root() -> Path:
    return _repo_root().parent


def _safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return cleaned.strip("._") or "artifact"


def resolve_adb_path() -> str:
    adb_from_path = shutil.which("adb")
    if adb_from_path:
        return adb_from_path

    for root in ADB_FALLBACKS:
        if not root:
            continue
        candidate = Path(root) / "platform-tools" / "adb.exe"
        if candidate.exists():
            return str(candidate)

    raise RuntimeError("adb not found. Set ANDROID_SDK_ROOT/ANDROID_HOME or install platform-tools.")


def parse_adb_devices(output: str) -> List[Dict[str, Any]]:
    devices: List[Dict[str, Any]] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("List of devices attached"):
            continue
        if line.startswith("* daemon"):
            continue

        match = ADB_DEVICE_LINE_RE.match(line)
        if not match:
            continue

        meta_tokens = match.group("meta") or ""
        metadata: Dict[str, Any] = {}
        extras: List[str] = []
        for token in meta_tokens.split():
            if ":" in token:
                key, value = token.split(":", 1)
                metadata[key] = value
            else:
                extras.append(token)
        if extras:
            metadata["extras"] = extras

        serial = match.group("serial")
        state = match.group("state")
        devices.append(
            {
                "serial": serial,
                "state": state,
                "ready": state == "device",
                "is_emulator": serial.startswith("emulator-"),
                "metadata": metadata,
            }
        )
    return devices


def pick_primary_serial(devices: Sequence[Dict[str, Any]], preferred: str = "") -> str:
    if preferred:
        for device in devices:
            if device.get("serial") == preferred and device.get("ready"):
                return preferred

    ready = [device for device in devices if device.get("ready")]
    if not ready:
        return ""

    emulator = next((device for device in ready if device.get("is_emulator")), None)
    if emulator:
        return str(emulator["serial"])
    return str(ready[0]["serial"])


def parse_wm_size(output: str) -> Dict[str, Optional[Dict[str, int]]]:
    result: Dict[str, Optional[Dict[str, int]]] = {"physical": None, "override": None}
    for raw_line in output.splitlines():
        line = raw_line.strip()
        match = WM_DIMENSION_RE.search(line)
        if not match:
            continue
        dims = {"width": int(match.group("width")), "height": int(match.group("height"))}
        lowered = line.lower()
        if lowered.startswith("override"):
            result["override"] = dims
        elif lowered.startswith("physical"):
            result["physical"] = dims
    return result


def parse_wm_density(output: str) -> Dict[str, Optional[int]]:
    result: Dict[str, Optional[int]] = {"physical": None, "override": None}
    for raw_line in output.splitlines():
        line = raw_line.strip()
        match = re.search(r"(\d+)", line)
        if not match:
            continue
        value = int(match.group(1))
        lowered = line.lower()
        if lowered.startswith("override"):
            result["override"] = value
        elif lowered.startswith("physical"):
            result["physical"] = value
    return result


def encode_input_text(text: str) -> str:
    encoded: List[str] = []
    for char in text:
        if char.isspace():
            encoded.append("%s")
        elif char in r"&|<>;()[]{}\"'":
            encoded.append("\\" + char)
        else:
            encoded.append(char)
    return "".join(encoded)


def parse_top_activity(output: str) -> str:
    for raw_line in output.splitlines():
        match = TOP_ACTIVITY_RE.search(raw_line)
        if match:
            return f"{match.group(1)}/{match.group(2)}"
    return ""


def build_webtoon_preview_plan(
    width: int,
    height: int,
    steps: int = 4,
    capture_prefix: str = "preview",
    swipe_duration_ms: int = 240,
) -> List[Dict[str, Any]]:
    if steps < 1:
        raise ValueError("steps must be at least 1")

    mid_x = max(1, width // 2)
    start_y = max(1, int(height * 0.78))
    end_y = max(1, int(height * 0.32))

    tasks: List[Dict[str, Any]] = [{"tongue": "CA", "action": "screencap", "name": f"{capture_prefix}_00"}]
    for index in range(1, steps):
        tasks.append(
            {
                "tongue": "UM",
                "action": "swipe",
                "x1": mid_x,
                "y1": start_y,
                "x2": mid_x,
                "y2": end_y,
                "duration_ms": swipe_duration_ms,
            }
        )
        tasks.append({"tongue": "CA", "action": "screencap", "name": f"{capture_prefix}_{index:02d}"})
    return tasks


@dataclass
class AndroidActionResult:
    tongue: Tongue
    action: str
    ok: bool
    serial: str
    elapsed_ms: float
    artifact_path: str = ""
    stdout: str = ""
    stderr: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["tongue"] = self.tongue.value
        return payload


@dataclass
class AndroidFinger:
    tongue: Tongue
    hand: "HydraAndroidHand"

    @property
    def proximity(self) -> Proximity:
        return TONGUE_PROXIMITY[self.tongue]

    @property
    def weight(self) -> float:
        return TONGUE_WEIGHT[self.tongue]

    def tap(self, x: int, y: int) -> AndroidActionResult:
        return self.hand.tap(x, y, tongue=self.tongue)

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 250) -> AndroidActionResult:
        return self.hand.swipe(x1, y1, x2, y2, duration_ms=duration_ms, tongue=self.tongue)

    def screencap(self, name: str = "screen") -> AndroidActionResult:
        return self.hand.screencap(name=name, tongue=self.tongue)

    def dump_ui(self, name: str = "ui") -> AndroidActionResult:
        return self.hand.dump_ui(name=name, tongue=self.tongue)


class HydraAndroidHand:
    def __init__(
        self,
        head_id: str = "android-alpha",
        serial: str = "",
        package_name: str = DEFAULT_PACKAGE,
        adb_path: str = "",
        artifact_root: Optional[Path] = None,
    ):
        self.head_id = head_id
        self.serial = serial
        self.package_name = package_name
        self._adb_path_override = adb_path
        self._resolved_adb_path = ""
        self._open = False
        self.repo_root = _repo_root()
        self.artifact_root = artifact_root or _default_artifact_root()
        self.session_id = f"{_safe_name(head_id)}-{_timestamp_slug()}"
        self.session_dir = self.artifact_root / self.session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.action_count = 0
        self.fingers: Dict[Tongue, AndroidFinger] = {
            tongue: AndroidFinger(tongue=tongue, hand=self) for tongue in Tongue
        }

    @staticmethod
    def _throttle_delay(proximity: Proximity) -> float:
        return {
            Proximity.ROCK: 0.0,
            Proximity.VOICE: 0.05,
            Proximity.KNOCK: 0.1,
            Proximity.GHOST: 0.15,
            Proximity.FORGE: 0.2,
            Proximity.OWL: 0.25,
        }.get(proximity, 0.1)

    @property
    def adb_path(self) -> str:
        if self._resolved_adb_path:
            return self._resolved_adb_path
        self._resolved_adb_path = self._adb_path_override or resolve_adb_path()
        return self._resolved_adb_path

    def _run(
        self,
        args: Sequence[str],
        *,
        binary: bool = False,
        check: bool = True,
        timeout_sec: int = 30,
    ) -> subprocess.CompletedProcess:
        cmd = [str(arg) for arg in args]
        android_user_root = _android_user_root()
        android_user_home = android_user_root / ".android"
        android_user_home.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env["USERPROFILE"] = str(android_user_root)
        env["HOME"] = str(android_user_root)
        env["ANDROID_SDK_HOME"] = str(android_user_root)
        env["ANDROID_USER_HOME"] = str(android_user_home)
        completed = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=not binary,
            encoding=None if binary else "utf-8",
            errors=None if binary else "replace",
            timeout=timeout_sec,
            env=env,
        )
        if check and completed.returncode != 0:
            stderr = completed.stderr.decode("utf-8", errors="replace") if binary else completed.stderr
            stdout = completed.stdout.decode("utf-8", errors="replace") if binary else completed.stdout
            detail = stderr.strip() or stdout.strip() or f"exit={completed.returncode}"
            raise RuntimeError(detail)
        return completed

    def _adb(self, *args: str, use_serial: bool = False, **kwargs: Any) -> subprocess.CompletedProcess:
        cmd = [self.adb_path]
        if use_serial:
            if not self.serial:
                self.refresh_serial()
            if not self.serial:
                raise RuntimeError("No online Android device found.")
            cmd.extend(["-s", self.serial])
        cmd.extend(args)
        return self._run(cmd, **kwargs)

    def list_devices(self) -> List[Dict[str, Any]]:
        completed = self._adb("devices", "-l", use_serial=False)
        return parse_adb_devices(completed.stdout)

    def refresh_serial(self) -> str:
        self._adb("start-server", use_serial=False)
        devices = self.list_devices()
        self.serial = pick_primary_serial(devices, preferred=self.serial)
        return self.serial

    def wait_until_ready(self, timeout_sec: int = 60) -> str:
        deadline = time.monotonic() + timeout_sec
        serial = self.refresh_serial()
        if not serial:
            raise RuntimeError("No online Android device found.")

        while time.monotonic() < deadline:
            completed = self._adb("shell", "getprop", "sys.boot_completed", use_serial=True, check=False)
            if completed.returncode == 0 and completed.stdout.strip() == "1":
                self._open = True
                return self.serial
            time.sleep(1.5)

        raise RuntimeError(f"Timed out waiting for Android device {self.serial} to boot.")

    def open(self, timeout_sec: int = 60) -> str:
        return self.wait_until_ready(timeout_sec=timeout_sec)

    def close(self) -> None:
        self._open = False

    def ensure_open(self) -> str:
        if self._open and self.serial:
            return self.serial
        return self.open()

    def _artifact_path(self, stem: str, suffix: str) -> Path:
        return self.session_dir / f"{_safe_name(stem)}{suffix}"

    def _make_result(
        self,
        *,
        tongue: Tongue,
        action: str,
        started_at: float,
        artifact_path: Path | None = None,
        completed: Optional[subprocess.CompletedProcess] = None,
        ok: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
        capture_streams: bool = True,
    ) -> AndroidActionResult:
        stdout = ""
        stderr = ""
        if completed is not None and capture_streams:
            if isinstance(completed.stdout, bytes):
                stdout = completed.stdout.decode("utf-8", errors="replace")
            else:
                stdout = completed.stdout or ""
            if isinstance(completed.stderr, bytes):
                stderr = completed.stderr.decode("utf-8", errors="replace")
            else:
                stderr = completed.stderr or ""

        self.action_count += 1
        return AndroidActionResult(
            tongue=tongue,
            action=action,
            ok=ok,
            serial=self.serial,
            elapsed_ms=(time.monotonic() - started_at) * 1000,
            artifact_path=str(artifact_path) if artifact_path else "",
            stdout=stdout.strip(),
            stderr=stderr.strip(),
            metadata=metadata or {},
        )

    def wake(self, tongue: Tongue = Tongue.RU) -> AndroidActionResult:
        started = time.monotonic()
        self.ensure_open()
        completed = self._adb("shell", "input", "keyevent", "KEYCODE_WAKEUP", use_serial=True)
        self._adb("shell", "wm", "dismiss-keyguard", use_serial=True, check=False)
        return self._make_result(tongue=tongue, action="wake", started_at=started, completed=completed)

    def launch_app(self, tongue: Tongue = Tongue.AV) -> AndroidActionResult:
        started = time.monotonic()
        self.ensure_open()
        self.wake(tongue=Tongue.RU)
        completed = self._adb(
            "shell",
            "monkey",
            "-p",
            self.package_name,
            "-c",
            "android.intent.category.LAUNCHER",
            "1",
            use_serial=True,
        )
        return self._make_result(
            tongue=tongue,
            action="launch_app",
            started_at=started,
            completed=completed,
            metadata={"package_name": self.package_name},
        )

    def open_url(self, url: str, tongue: Tongue = Tongue.AV) -> AndroidActionResult:
        started = time.monotonic()
        self.ensure_open()
        completed = self._adb(
            "shell",
            "am",
            "start",
            "-W",
            "-a",
            "android.intent.action.VIEW",
            "-d",
            url,
            use_serial=True,
        )
        return self._make_result(
            tongue=tongue,
            action="open_url",
            started_at=started,
            completed=completed,
            metadata={"url": url},
        )

    def launch_reader(
        self,
        route_url: str = DEFAULT_READER_ROUTE,
        *,
        use_browser: bool = False,
        tongue: Tongue = Tongue.AV,
    ) -> AndroidActionResult:
        if use_browser:
            return self.open_url(route_url, tongue=tongue)
        return self.launch_app(tongue=tongue)

    def keyevent(self, keycode: str, tongue: Tongue = Tongue.RU) -> AndroidActionResult:
        started = time.monotonic()
        self.ensure_open()
        completed = self._adb("shell", "input", "keyevent", keycode, use_serial=True)
        return self._make_result(
            tongue=tongue,
            action="keyevent",
            started_at=started,
            completed=completed,
            metadata={"keycode": keycode},
        )

    def input_text(self, text: str, tongue: Tongue = Tongue.RU) -> AndroidActionResult:
        started = time.monotonic()
        self.ensure_open()
        completed = self._adb("shell", "input", "text", encode_input_text(text), use_serial=True)
        return self._make_result(
            tongue=tongue,
            action="input_text",
            started_at=started,
            completed=completed,
            metadata={"text_length": len(text)},
        )

    def tap(self, x: int, y: int, tongue: Tongue = Tongue.CA) -> AndroidActionResult:
        started = time.monotonic()
        self.ensure_open()
        completed = self._adb("shell", "input", "tap", str(x), str(y), use_serial=True)
        return self._make_result(
            tongue=tongue,
            action="tap",
            started_at=started,
            completed=completed,
            metadata={"x": x, "y": y},
        )

    def swipe(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        *,
        duration_ms: int = 250,
        tongue: Tongue = Tongue.UM,
    ) -> AndroidActionResult:
        started = time.monotonic()
        self.ensure_open()
        completed = self._adb(
            "shell",
            "input",
            "swipe",
            str(x1),
            str(y1),
            str(x2),
            str(y2),
            str(duration_ms),
            use_serial=True,
        )
        return self._make_result(
            tongue=tongue,
            action="swipe",
            started_at=started,
            completed=completed,
            metadata={"x1": x1, "y1": y1, "x2": x2, "y2": y2, "duration_ms": duration_ms},
        )

    def screencap(self, name: str = "screen", tongue: Tongue = Tongue.CA) -> AndroidActionResult:
        started = time.monotonic()
        self.ensure_open()
        artifact_path = self._artifact_path(name, ".png")
        completed = self._adb("exec-out", "screencap", "-p", use_serial=True, binary=True)
        artifact_path.write_bytes(completed.stdout)
        return self._make_result(
            tongue=tongue,
            action="screencap",
            started_at=started,
            artifact_path=artifact_path,
            completed=completed,
            capture_streams=False,
        )

    def dump_ui(self, name: str = "ui", tongue: Tongue = Tongue.DR) -> AndroidActionResult:
        started = time.monotonic()
        self.ensure_open()
        remote_path = f"/sdcard/Download/{_safe_name(name)}.xml"
        artifact_path = self._artifact_path(name, ".xml")
        self._adb("shell", "uiautomator", "dump", remote_path, use_serial=True)
        pull_completed = self._adb("pull", remote_path, str(artifact_path), use_serial=True)
        self._adb("shell", "rm", "-f", remote_path, use_serial=True, check=False)
        metadata = {"remote_path": remote_path}
        return self._make_result(
            tongue=tongue,
            action="dump_ui",
            started_at=started,
            artifact_path=artifact_path,
            completed=pull_completed,
            metadata=metadata,
        )

    def get_display_metrics(self) -> Dict[str, Any]:
        self.ensure_open()
        size = parse_wm_size(self._adb("shell", "wm", "size", use_serial=True).stdout)
        density = parse_wm_density(self._adb("shell", "wm", "density", use_serial=True).stdout)
        effective = size.get("override") or size.get("physical") or {"width": 0, "height": 0}
        return {
            "size": size,
            "density": density,
            "width": effective["width"],
            "height": effective["height"],
        }

    def status(self) -> Dict[str, Any]:
        devices = self.list_devices()
        selected = pick_primary_serial(devices, preferred=self.serial)
        payload: Dict[str, Any] = {
            "head_id": self.head_id,
            "open": self._open,
            "serial": selected or self.serial,
            "package_name": self.package_name,
            "session_id": self.session_id,
            "session_dir": str(self.session_dir),
            "action_count": self.action_count,
            "devices": devices,
            "fingers": {
                tongue.value: {
                    "proximity": finger.proximity.value,
                    "weight": finger.weight,
                }
                for tongue, finger in self.fingers.items()
            },
        }
        if selected:
            self.serial = selected
            boot = self._adb("shell", "getprop", "sys.boot_completed", use_serial=True, check=False).stdout.strip()
            model = self._adb("shell", "getprop", "ro.product.model", use_serial=True, check=False).stdout.strip()
            activity = parse_top_activity(
                self._adb("shell", "dumpsys", "activity", "top", use_serial=True, check=False).stdout
            )
            payload["boot_completed"] = boot == "1"
            payload["model"] = model
            payload["top_activity"] = activity
        return payload

    def observe(
        self,
        name: str = "observation",
        *,
        include_ui_dump: bool = True,
        tongue: Tongue = Tongue.CA,
    ) -> Dict[str, Any]:
        screenshot = self.screencap(name=name, tongue=tongue)
        payload: Dict[str, Any] = {
            "screenshot": screenshot.to_dict(),
        }
        if include_ui_dump:
            ui_dump = self.dump_ui(name=f"{name}_ui", tongue=Tongue.DR)
            payload["ui_dump"] = ui_dump.to_dict()
        payload["status"] = self.status()
        return payload

    def multi_action(self, tasks: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        self.ensure_open()
        results: List[Dict[str, Any]] = []
        for task in tasks:
            tongue_raw = str(task.get("tongue", "CA")).upper()
            try:
                tongue = Tongue(tongue_raw)
            except ValueError:
                tongue = Tongue.CA

            delay_sec = task.get("delay_sec")
            if delay_sec is None:
                delay_sec = self._throttle_delay(self.fingers[tongue].proximity)
            if delay_sec and delay_sec > 0:
                time.sleep(float(delay_sec))

            action = str(task.get("action", "status")).lower()
            if action == "launch_app":
                result = self.launch_app(tongue=tongue)
                results.append(result.to_dict())
            elif action == "launch_reader":
                result = self.launch_reader(
                    route_url=str(task.get("route_url", DEFAULT_READER_ROUTE)),
                    use_browser=bool(task.get("use_browser", False)),
                    tongue=tongue,
                )
                results.append(result.to_dict())
            elif action == "open_url":
                result = self.open_url(str(task["url"]), tongue=tongue)
                results.append(result.to_dict())
            elif action == "tap":
                result = self.tap(int(task["x"]), int(task["y"]), tongue=tongue)
                results.append(result.to_dict())
            elif action == "swipe":
                result = self.swipe(
                    int(task["x1"]),
                    int(task["y1"]),
                    int(task["x2"]),
                    int(task["y2"]),
                    duration_ms=int(task.get("duration_ms", 250)),
                    tongue=tongue,
                )
                results.append(result.to_dict())
            elif action == "keyevent":
                result = self.keyevent(str(task["keycode"]), tongue=tongue)
                results.append(result.to_dict())
            elif action == "text":
                result = self.input_text(str(task["text"]), tongue=tongue)
                results.append(result.to_dict())
            elif action == "screencap":
                result = self.screencap(name=str(task.get("name", "screen")), tongue=tongue)
                results.append(result.to_dict())
            elif action == "dump_ui":
                result = self.dump_ui(name=str(task.get("name", "ui")), tongue=tongue)
                results.append(result.to_dict())
            elif action == "observe":
                results.append(
                    self.observe(
                        name=str(task.get("name", "observation")),
                        include_ui_dump=bool(task.get("include_ui_dump", True)),
                        tongue=tongue,
                    )
                )
            elif action == "sleep":
                seconds = float(task.get("seconds", 0.5))
                time.sleep(max(0.0, seconds))
                results.append(
                    AndroidActionResult(
                        tongue=tongue,
                        action="sleep",
                        ok=True,
                        serial=self.serial,
                        elapsed_ms=seconds * 1000,
                        metadata={"seconds": seconds},
                    ).to_dict()
                )
            elif action == "status":
                results.append({"action": "status", "tongue": tongue.value, "payload": self.status()})
            else:
                raise ValueError(f"Unknown Android hand action: {action}")
        return results

    def preview_loop(
        self,
        *,
        steps: int = 4,
        settle_ms: int = 700,
        include_ui_dump: bool = False,
        launch_reader: bool = True,
        route_url: str = DEFAULT_READER_ROUTE,
        use_browser: bool = False,
    ) -> Dict[str, Any]:
        self.ensure_open()

        session_payload: Dict[str, Any] = {
            "ok": True,
            "session_id": self.session_id,
            "session_dir": str(self.session_dir),
            "serial": self.serial,
            "package_name": self.package_name,
            "steps": steps,
            "settle_ms": settle_ms,
            "launch_reader": launch_reader,
            "use_browser": use_browser,
            "results": [],
        }

        if launch_reader:
            session_payload["results"].append(
                self.launch_reader(route_url=route_url, use_browser=use_browser, tongue=Tongue.AV).to_dict()
            )
            time.sleep(max(0.2, settle_ms / 1000.0))

        metrics = self.get_display_metrics()
        session_payload["display_metrics"] = metrics
        plan = build_webtoon_preview_plan(
            width=metrics["width"],
            height=metrics["height"],
            steps=steps,
            capture_prefix="webtoon_preview",
        )
        session_payload["plan"] = plan

        for task in plan:
            result_list = self.multi_action([dict(task, delay_sec=0.0)])
            session_payload["results"].extend(result_list)
            if task["action"] == "swipe":
                time.sleep(max(0.0, settle_ms / 1000.0))
            elif include_ui_dump and task["action"] == "screencap":
                name = str(task.get("name", "observation"))
                session_payload["results"].append(self.dump_ui(name=f"{name}_ui", tongue=Tongue.DR).to_dict())

        summary_path = self._artifact_path(f"{self.session_id}_summary", ".json")
        summary_path.write_text(json.dumps(session_payload, indent=2), encoding="utf-8")
        session_payload["summary_path"] = str(summary_path)
        return session_payload
