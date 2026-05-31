# Robotics And Simulator Control Adapter Map

Date: 2026-05-30

Purpose: map SCBE/HYDRA command-line control into real simulator control surfaces first, then into robot and drone adapters behind safety envelopes. This is a later-build note, not a direct vehicle-control implementation.

## Core Position

The useful abstraction is not "AI drives robot." It is:

```text
keyboard / CLI / AI intent
  -> normalized control intent
  -> safety governor
  -> simulator adapter
  -> telemetry feedback
  -> receipt ledger
```

Real robot or drone control should use the same packet shape only after simulator training, operator confirmation, and hardware-specific failsafes.

## HYDRA Mapping

HYDRA is the SCBE subsystem layer for multi-agent coordination. In this repo, the full runtime has moved to `scbe-agents`, while compatibility/grid/ledger pieces remain under `hydra/`.

| HYDRA role | Control-system meaning | Repo/local anchor |
|---|---|---|
| Spine | mission state, timing, command arbitration | `packages/agent-bus`, reaction chains, runtime gate |
| Heads | competing planners or model lanes | Hermes, star path, free-first router |
| Limbs | tool/simulator/robot adapters | browser adapter, future sim adapters |
| Ledger | movement receipt and replay trail | agent life ledger, HYDRA ledger |
| Lattice | environment, obstacle, permission, security fields | board fields, vector-field nav, octree/quadtree |
| Librarian/shared pad | state packets and squad memory | Polly Pad / field tablet surface |

## Normalized Control Intent

All simulator and robot adapters should consume this kind of normalized packet:

```json
{
  "intent_id": "ctrl-2026-05-30T00-00-00Z-001",
  "mode": "sim.flight",
  "operator": "human|agent|chain",
  "frame": "local_body|world_ned|screen_xy|road_lane|octree_cell",
  "axes": {
    "forward": 0.0,
    "strafe": 0.0,
    "vertical": 0.0,
    "yaw": 0.0,
    "pitch": 0.0,
    "roll": 0.0
  },
  "buttons": {
    "hold": false,
    "stop": false,
    "return_home": false,
    "land": false,
    "handbrake": false
  },
  "limits": {
    "max_speed_mps": 1.0,
    "max_yaw_rate_dps": 30,
    "max_altitude_m": 2.0,
    "geofence_id": "sim-box-01"
  },
  "receipt": {
    "policy_hash": "sha256:...",
    "adapter": "carla|airsim|ros2|px4|ardupilot|msfs|xplane",
    "decision": "ALLOW_SIM|HOLD|DENY_REAL"
  }
}
```

## Flight Simulator Adapter

Flight simulators are the safest first training lane for drone and aircraft-style movement because they expose the same control concepts as real flight systems without touching hardware.

| SCBE axis | Flight sim control | Drone analogue |
|---|---|---|
| `forward` | throttle / airspeed command | velocity x |
| `vertical` | climb/descent or collective | velocity z / altitude setpoint |
| `yaw` | rudder / yaw rate | yaw rate |
| `pitch` | elevator / pitch attitude | pitch or forward acceleration |
| `roll` | aileron / bank angle | roll or lateral acceleration |
| `hold` | pause/autopilot hold | position hold |
| `return_home` | nav/autopilot route | RTL |
| `land` | landing sequence | land mode |

Adapter targets:

- X-Plane: datarefs and commands for joystick axes, throttle, flight controls, and telemetry.
- Microsoft Flight Simulator: SimConnect events and variables for aircraft control and state.
- PX4 simulation: Offboard setpoints, with strict keepalive/failsafe behavior.
- ArduPilot SITL: Guided-mode MAVLink position, velocity, and attitude setpoints.

Safety rule: flight adapters default to simulator-only. Real PX4/ArduPilot adapters must refuse to arm unless an explicit hardware profile, geofence, operator confirmation, and deadman channel are present.

## Driving Simulator Adapter

Driving simulators are the safest first training lane for ground robots, warehouse bots, field rovers, and browser-like navigation under partial information.

| SCBE axis/button | Driving sim control | Ground robot analogue |
|---|---|---|
| `forward` | throttle | linear velocity x |
| `yaw` or `strafe` | steering | angular velocity z |
| `stop` | brake | zero command / emergency stop |
| `handbrake` | hand brake | hard stop / hold brake |
| `reverse` | reverse gear | negative linear velocity |
| `frame` | road lane / map tile | occupancy grid / octree cell |

Adapter targets:

- CARLA: `VehicleControl` with throttle, steer, brake, hand_brake, reverse, manual_gear_shift, gear.
- AirSim car mode: steering, throttle, brake, handbrake, and manual gear controls.
- ROS 2 ground robots: `cmd_vel` via `geometry_msgs/Twist`, often produced by keyboard/gamepad teleop layers.

Safety rule: ground adapters default to low-speed simulation. Real robot adapters require speed caps, obstacle state, heartbeat, and emergency stop.

## Training Lanes

The first serious benchmark should be simulator-first:

| Lane | Environment | Goal | Score |
|---|---|---|---|
| keyboard flight | X-Plane/MSFS or mock adapter | take off, waypoint, hold, land | completion, violations, smoothness |
| drone offboard | PX4 SITL / ArduPilot SITL | local waypoint loop under keepalive | completion, failsafe events |
| driving city | CARLA / AirSim | navigate route with obstacles | route success, collisions, rule violations |
| fog-of-war rover | SCBE vector-field nav | unknown maze / occupancy grid | solve rate, step cost, unsafe moves |
| mixed-command | CLI plus AI planner | convert natural command to safe controls | plan validity, auditability |

## HYDRA Expansion Points

These are the modules worth building later:

1. `control-intent.ts`: typed command packet, axis clamps, button schema.
2. `sim-adapter-flight.ts`: mock flight adapter plus X-Plane/MSFS shape.
3. `sim-adapter-driving.ts`: mock driving adapter plus CARLA/AirSim shape.
4. `robot-safety-governor.ts`: deadman, geofence, heartbeat, emergency stop.
5. `control-replay.ts`: receipt replay and deterministic command audit.
6. `polly-field-pad.ts`: personal/squad control surface for live status, fog of war, and fallback headless commands.

## Patent-Provenance Framing

This should be claimed as a governed cross-domain control compiler, not as a raw autopilot:

```text
human/agent intent
  -> semantic command packet
  -> lattice/field safety scoring
  -> simulator/robot adapter
  -> telemetry receipt
  -> route correction
```

The technical contribution is the auditable translation and safety loop across domains: text, keyboard, simulator, robot, drone, browser, and file-system operations all become typed moves on a governed board.

## External References Checked

- ROS 2 `teleop_twist_keyboard`: keyboard teleoperation publishes Twist/TwistStamped velocity commands. <https://docs.ros.org/en/rolling/p/teleop_twist_keyboard/>
- ROS 2 `diff_drive_controller`: accepts velocity commands, applies limits, publishes odometry, and stops on timeout. <https://control.ros.org/master/doc/ros2_controllers/diff_drive_controller/doc/userdoc.html>
- PX4 Offboard mode: external setpoints require continuous proof-of-life and trigger failsafe on loss. <https://docs.px4.io/main/en/flight_modes/offboard.html>
- ArduPilot Guided mode: MAVLink setpoint commands for local/global position, velocity, and attitude. <https://ardupilot.org/dev/docs/mavlink-rover-commands.html>
- CARLA vehicle control: throttle, steer, brake, hand brake, reverse, gear. <https://carla.readthedocs.io/en/latest/python_api/#carla.VehicleControl>
- AirSim car controls: steering, throttle, brake, handbrake, manual gear. <https://microsoft.github.io/AirSim/apis/#car-apis>
- MSFS SimVars and key events: simulator state variables and code-driven control events. <https://microsoft.github.io/msfs-avionics-mirror/docs/interacting-with-msfs/simvars/> and <https://microsoft.github.io/msfs-avionics-mirror/docs/interacting-with-msfs/key-events/>
- X-Plane developer datarefs/commands: simulator control and telemetry surface. <https://developer.x-plane.com/datarefs/> and <https://developer.x-plane.com/sdk/XPLMCommand/>
