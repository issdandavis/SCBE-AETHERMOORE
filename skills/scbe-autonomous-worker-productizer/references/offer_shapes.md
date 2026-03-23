# Offer Shapes

Use one of these shapes as the packaging target.

## `pilot`

- Best when you need a paid proof-of-value engagement.
- Recommended repo surfaces:
  - `src/api/saas_routes.py`
  - `src/api/main.py`
  - `src/symphonic_cipher/scbe_aethermoore/flock_shepherd.py`
  - `tests/test_saas_api.py`
  - `tests/test_flock_shepherd.py`

## `workflow-pack`

- Best when you are selling automation deliverables rather than software access.
- Recommended repo surfaces:
  - `scripts/system/dispatch_monetization_swarm.py`
  - `scripts/system/monetization_connector_push.py`
  - `scripts/system/pilot_demo_to_decision.py`

## `saas`

- Best when you are packaging software access and governed workflow APIs.
- Recommended repo surfaces:
  - `src/api/saas_routes.py`
  - `src/api/main.py`
  - metering and audit routes

## `service`

- Best when delivery is still human-assisted and the software is the engine behind the scenes.
- Recommended repo surfaces:
  - flock dashboard and refresh flows
  - governance checks
  - connector scripts

## Output Fields

Every packet should define:

- `buyer`
- `problem`
- `promise`
- `worker_lanes`
- `connectors`
- `governance_gates`
- `repo_proof_surfaces`
- `delivery_artifacts`
- `next_build_steps`
