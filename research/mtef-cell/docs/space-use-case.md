# Space and Exercise-Equipment Use Case

## Best positioning

M-TEF should be framed as a **distributed recovery layer**, not a station-scale power plant.

Bad framing:

> “Replace solar arrays.”

Better framing:

> “Recover small amounts of local mechanical energy to power sensors, health telemetry, wake-up circuits, micro-actuators, and emergency reserves.”

## Why exercise equipment is attractive

Astronaut exercise systems already exist, already move, and already dissipate mechanical energy. That makes them a high-value testbed because the harvester can be tied to an existing operational need.

Useful outputs:

- sensor-node power
- rep counting
- force curve measurement
- fatigue/health telemetry
- emergency trickle charging
- condition monitoring of exercise hardware

## Why space may help the triboelectric channel

The research bundle argues that vacuum can increase triboelectric charge density by reducing atmospheric breakdown and humidity losses. This makes the target environment potentially favorable for the TENG subsystem.

## Why microgravity may help the fluidic channel

In microgravity, buoyancy-driven separation weakens and surface tension becomes more dominant. That can make droplet/channel geometry and magnetic control more important than “up/down” orientation.

## First credible mission profile

A practical early target is not a full ISS operational integration. It is a small sealed test article:

- CubeLab-like form factor
- controlled vibration or pressure input
- isolated fluid stack
- independent EM and TENG measurement circuits
- telemetry downlink of voltage/current/temperature/pressure/cycle count

## Success condition

A space-relevant demo is useful only after ground hardware proves the combined architecture. The correct sequence is:

```text
bench EM → bench TENG → combined bench → vacuum chamber → relevant flight demo
```
