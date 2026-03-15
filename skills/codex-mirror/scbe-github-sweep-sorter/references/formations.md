# HYDRA Formations

These formations are derived from the SCBE/HYDRA coordination notes and are intended for software collaboration, not literal military automation.

## Scatter

Use when:
- sweeping many repos
- classifying many issues or alerts
- doing first-pass discovery

Strengths:
- broad coverage
- low initial coupling
- good for inventory and triage

Weaknesses:
- weak for ordered approvals
- weak for shared-file implementation

## Hexagonal Ring

Default six-tongue collaborative formation.

Use when:
- one shared codebase needs parallel thought with explicit ownership
- multiple roles are active at once
- the team needs balanced collaboration rather than serial handoff

Strengths:
- symmetric
- easy to visualize
- good for balanced coding, docs, review, and governance

Weaknesses:
- not ideal when a strict temporal attestation path is required

## Tetrahedral

Use when:
- the packet is smaller
- risk is higher
- fewer roles should touch the work

Suggested roles:
- KO architecture
- CA implementation
- UM security
- DR release memory

Strengths:
- tight and focused
- useful for risky refactors

Weaknesses:
- less breadth than the full six-tongue ring

## Ring

Use when:
- order matters
- chain of custody matters
- the action is critical or destructive

Suggested order:
- `KO -> AV -> RU -> CA -> UM -> DR`

This is the right formation for:
- release approvals
- security exceptions
- privileged tool actions
- critical governance decisions
