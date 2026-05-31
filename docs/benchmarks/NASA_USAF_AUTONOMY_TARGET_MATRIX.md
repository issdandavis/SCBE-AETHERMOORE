# NASA/USAF Autonomy Target Matrix

Generated: 2026-05-29T23:01:35.270069+00:00
Decision: `TARGETS_REQUIRED`

## Summary

- Targets: 8
- Pass: 0
- Partial: 4
- Fail: 4

Highest-value next targets:
- DAA-lite ownship/traffic encounter benchmark
- runtime assurance control-signal substitution fixture
- SCBE Autonomy Reference Interface conformance suite
- requirements-to-test trace matrix

## Target Matrix

| Target | Status | Gap | Next Target |
| --- | --- | --- | --- |
| NASA-style software assurance and traceability | PARTIAL | Strong tests and receipts exist, but there is no NASA-style requirements-to-test trace matrix, independent review lane, safety classification map, or formal inspection record. | Add a requirements trace matrix keyed by module/test/artifact and a generated IV&V-style readiness report with owners, hazards, verification method, and residual risk. |
| DAA well-clear detection, alerting, and maneuver guidance | FAIL | SCBE has geometric drift gates and video/pose lattices, but no ownship/traffic kinematics, well-clear thresholds, aircraft envelopes, or batch DAA encounter replay. | Build a deterministic DAA-lite fixture: ownship plus intruder tracks, time-to-boundary, alert tier, recovery band, and maneuver recommendation. Score it against DAIDALUS-style cases. |
| UTM/BVLOS traffic-management service interoperability | PARTIAL | Agent bus and Spiralverse fleet docs model coordination, but there is no UTM service API, airspace volume model, BVLOS operation plan, or multi-operator deconfliction benchmark. | Add an airspace-volume conflict benchmark with multiple planned routes, time windows, authorization state, and deconfliction decisions. |
| Flight-software framework readiness | FAIL | Repo has governance, fleet, and bus abstractions, but no cFS/F Prime/ROS2 adapter, command/telemetry dictionary, flight-app lifecycle model, or safety-critical runtime profile. | Create a non-flight, simulation-only adapter target: command packet, telemetry packet, app lifecycle, fault event, and deterministic replay. |
| Geofence, flight-envelope, navigation-command, and coordinated maneuver checks | FAIL | SCBE can gate commands semantically, but it does not yet simulate geofence polygons, vehicle dynamics, control limits, flight envelope constraints, or coordinated maneuver timing. | Add a geofence/envelope benchmark: command accepted only if route stays inside permitted polygons, speed/turn/altitude bounds, and coordinated maneuver separation limits. |
| Open modular autonomy architecture | PARTIAL | Agent-bus tool registry and model lanes are a good software-first start, but the repo lacks a vehicle/autonomy interface contract, versioned simulation harness, and cross-vendor conformance tests. | Define an SCBE Autonomy Reference Interface with plan, observe, command, veto, explain, and receipt messages, then run two independent mock providers through the same conformance suite. |
| Ground-control and autonomy-integration readiness | FAIL | Current harnesses are CLI/software tests. There is no ground-control UI contract, avionics/propulsion sim boundary, hardware abstraction, or operator intervention loop. | Add a simulation-only ground-control contract with operator command, autonomy recommendation, veto, telemetry stream, and fault-injection transcript. |
| Runtime assurance safety filter for AI control outputs | PARTIAL | SCBE has ALLOW/DENY/QUARANTINE and correction signals, but does not yet prove control-signal substitution against a vehicle/satellite dynamics model. | Extend runtime gate fixtures with proposed-control, safety-filtered-control, substituted-control, environment-state-before/after, and hazard-avoidance proof. |

## Sources

- `NASA-SWE-ASSURANCE`: [NASA Software Engineering Procedural Requirements and Software Assurance Resources](https://www.nasa.gov/intelligent-systems-division/software-management-office/nasa-software-engineering-procedural-requirements-standards-and-related-resources/)
  - NPR 7150.2, NASA-STD-8739.8, IV&V, formal inspections, secure coding, and the NASA Software Engineering Handbook as agency-wide safe/reliable software guidance.
- `NASA-DAIDALUS`: [DAIDALUS Detect and Avoid Alerting Logic for Unmanned Systems](https://nasa.github.io/daidalus/)
  - Reference implementation of RTCA DO-365/DO-365A detect-and-avoid functional requirements with well-clear thresholds, alerting, maneuver guidance, recovery bands, sensor uncertainty mitigation, and batch encounter simulation tools.
- `NASA-UTM`: [UAS Traffic Management Project](https://www.nasa.gov/directorates/armd/past-armd-projects/utm-project/)
  - BVLOS low-altitude UAS integration through field demonstrations with FAA, industry, and academia for traffic management, airspace access, and deconfliction services.
- `NASA-CFS-JSC`: [JSC Software and Autonomous Subsystems](https://www.nasa.gov/reference/jsc-software-autonomous-subsystems/)
  - CMMI Level 3 organization using human-rated open-source Class A Core Flight Software framework, safety criticality assessments, standards, process requirements, and COFR.
- `USAF-SKYBORG-ACS`: [Skyborg Autonomy Core System First Flight](https://www.af.mil/News/Features/Article/2596671/skyborg-autonomy-core-system-has-successful-first-flight/)
  - Flight-tested autonomy core system demonstrating navigation commands, geofence reaction, flight-envelope adherence, coordinated maneuvering, and monitored C2.
- `USAF-AGRA-CCA`: [Air Force validates open architecture, expands Collaborative Combat Aircraft ecosystem](https://www.af.mil/News/Article-Display/Article/4405471/air-force-validates-open-architecture-expands-collaborative-combat-aircraft-eco/)
  - Government-owned Autonomy Government Reference Architecture across multiple platforms and vendors, decoupling mission software from vehicle hardware with modular open systems.
- `USAF-CCA-GROUND-TEST`: [DAF begins ground testing for Collaborative Combat Aircraft](https://www.af.mil/News/Article-Display/Article/4171208/daf-begins-ground-testing-for-collaborative-combat-aircraft-selects-beale-afb-a/)
  - Ground testing evaluates propulsion systems, avionics, autonomy integration, and ground control interfaces before flight testing.
- `AFRL-STARS-RTA`: [Safe Trusted Autonomy for Responsible Spacecraft (STARS)](https://afresearchlab.com/wp-content/uploads/2024/03/AFRL_STARS_FS_240318.1.pdf)
  - Runtime assurance safety filter for AI control outputs, reinforcement-learning multi-satellite control, close-proximity operations, and human-autonomy interfaces.
