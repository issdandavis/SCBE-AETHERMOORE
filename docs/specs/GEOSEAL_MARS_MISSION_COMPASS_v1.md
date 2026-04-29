# GeoSeal Mars Mission Compass v1

Status: implementation scaffold

Purpose: make GeoSeal the single mission substrate an autonomous agent needs for terrain mapping, coding solutions, fault recovery, navigation home, and handoff.

## Contract

An agent does not need separate mission languages for maps, code, home routing, telemetry, and handoff. It needs one GeoSeal mission packet with three labeled layers:

1. semantic phrase: the mission goal and intent.
2. metric payload: compass, minimap, terrain routes, home route, risk, phase, and tongue routing.
3. transport packet: deterministic mission hash for replay, audit, and training.

GeoSeal is the mission substrate. Sensors, tools, code runners, radios, and files are inputs or outputs attached to that substrate.

## Software Capabilities We Want In GeoSeal

These are non-physical capabilities, so the agent should have them as routeable packet logic:

- visual-inertial odometry state slots
- terrain reconstruction from images, altitude, motion, radar, or map data
- slope, roughness, hazard, signal, energy, and thermal scoring
- geologic tags for layering, texture, albedo, mineral hints, and sample priority
- home/base route planning with governance bottleneck scores
- code-patch packet generation for mission software fixes
- fault stabilization and compressed handoff packets

## Physical Mini Manual

These are physical instruments or subsystems. The agent can request, model, document, or consume telemetry from them, but it must not pretend to possess measurements that were not supplied.

- navigation camera: visual odometry, hazard context, surface-relative motion, landing-zone checks
- stereo or zoom science camera: outcrop shape, layering, texture, color, stratigraphy, traverse scouting
- IMU, inclinometer, and altimeter: attitude, acceleration, slope, altitude, flight or drive stability
- environment sensors: wind, pressure, temperature, dust, humidity, thermal stress, flight envelope limits
- geochemistry or spectroscopy payload: elemental, mineral, and organic clues when rover-class instruments are available
- ground-penetrating radar: subsurface layering and buried geologic structure when available
- radio or relay link: handoff packets, command windows, map updates, health telemetry
- power and thermal system: battery, solar or radioisotope power budget, heater duty cycle, survival limits

## Research Grounding

NASA's public Mars 2020/Perseverance and Ingenuity materials support this split. Perseverance carries camera, spectroscopy, environmental, oxygen-production, and subsurface radar instruments; Ingenuity demonstrated aerial scouting with a navigation camera and laser altimeter; NASA has also described future Mars helicopters as scouts that may carry small science payloads.

Reference URLs:

- https://science.nasa.gov/mission/mars-2020-perseverance/science-instruments/
- https://science.nasa.gov/resource/bottom-of-ingenuity-mars-helicopter/
- https://science.nasa.gov/blog/driving-farther-and-faster-with-autonomous-navigation-and-helicopter-scouting/
- https://science.nasa.gov/resource/nasas-mars-helicopters-present-future-and-proposed/

## Required Mission Jobs

- map terrain from telemetry
- code or patch mission solutions
- stabilize faults and route anomalies
- navigate home or to base
- collect science or operational samples
- compress state for relay, recovery, or handoff

## Tongue Routing

- KO: terrain mapping, scanning, goal ordering
- AV: coding, automation, software patches
- RU: repair, recovery, debugging, verification
- CA: home routing, base navigation, safe return
- UM: science sampling, analysis, optimization
- DR: communication, compression, archive, handoff

## Runtime Anchor

The first implementation lives in `src/geoseal_mission_compass.py` and is reachable through:

```bash
python -m src.geoseal_cli mars-mission --input mission.json --json
```
