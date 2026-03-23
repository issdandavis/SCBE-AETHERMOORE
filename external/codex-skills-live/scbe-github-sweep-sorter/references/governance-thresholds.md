# Governance Thresholds

Use risk-tiered thresholds for repo and GitHub sweep actions.

## Thresholds

- `3/6`
  - low-risk discovery
  - sorting
  - inventory
  - report generation

- `4/6`
  - medium-risk code or workflow changes
  - CI fixes
  - integration wiring
  - config edits

- `5/6`
  - destructive actions
  - security-sensitive changes
  - release or deploy gates
  - permission and secrets surfaces

## Ordered Attestation

When the action needs chain of custody, use ordered signoff:

- `KO -> AV -> RU -> CA -> UM -> DR`

Use this for:
- release gating
- privileged tool execution
- approval on security exceptions
- destructive repo surgery

## Language Discipline

Prefer:
- `BFT-informed threshold governance`
- `risk-tiered quorum`
- `ordered attestation path`

Avoid:
- claiming one universal quorum for every action
- calling governance-path diversity a cryptographic multiplier
