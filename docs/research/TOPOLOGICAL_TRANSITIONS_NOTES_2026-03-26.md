# Topological Transitions Notes

Saved: 2026-03-26
Status: Research note
Intent: Preserve the current idea for later implementation without overstating what exists in the code today.

## Working definition

A topological transition in SCBE should mean an explicit, audited rewrite of the governed semantic region graph.

Not:
- vague foam-language by itself
- raw model weights magically reorganizing
- metaphor-only physics claims

Instead:
- change region connectivity
- change corridor ownership
- change which semantic regions can hand off to each other
- do so under measurable conditions

## Practical state model

Use a region-graph state:

```text
S_t = (R, E, M, T, N, G)
```

Where:
- `R` = semantic regions / bubbles
- `E` = adjacency edges / borders
- `M` = support or mass per region
- `T` = tension / boundary cost
- `N` = null-space / structured-absence profile
- `G` = governance state

Suggested region representation:
- centroid `c_i`
- radius `r_i`
- support count
- average tongue vector
- null profile
- drift score
- harmonic cost
- route permissions

## Transition operators

Only four are needed initially:

1. `merge(i, j)`
- two regions become one

2. `split(i)`
- one region separates into two

3. `pop(i)`
- remove or quarantine a low-value or unstable region

4. `reroute(i, j, k)`
- redirect allowed handoff paths between regions

This is the concrete form of the so-called `string operator`:
- deterministic rewrite over the region graph

## Trigger conditions

### Merge

```text
merge(i,j) if
hyperbolic_distance(c_i, c_j) is small
and null_profile_disagreement(i,j) is low
and governance_conflict(i,j) is low
and total_energy decreases enough
```

Interpretation:
- semantically close
- absence patterns compatible
- governance compatible
- merge actually improves the system

### Split

```text
split(i) if
internal_variance(i) is high
and clusterability(i) is high
and null-space behavior bifurcates over time
```

Interpretation:
- one region is pretending to be one thing but is really two

### Pop

```text
pop(i) if
support(i) is low
and utility(i) is low
and boundary_cost(i) is high
and removing it lowers total energy
```

Interpretation:
- dead, redundant, unstable, or malicious region

### Reroute

```text
reroute(i,j,k) if
edge_tension(i,j) is high
and an alternate path has lower total cost
and governance allows the new path
```

Interpretation:
- the old corridor is unstable and a better route exists

## Energy function

A transition engine needs one score to reduce:

```text
E = α·boundary_tension
  + β·null_disagreement
  + γ·session_drift
  + δ·harmonic_cost
  + λ·complexity_penalty
```

Possible meanings:
- boundary tension = unstable borders
- null disagreement = incompatible structured-absence profiles
- session drift = temporal suspicion accumulation
- harmonic cost = unsafe movement toward edge / unsafe region
- complexity penalty = too many regions or edges

Rule:
- transitions only commit if they lower `E` enough

## Hysteresis and stability

Do not fire transitions on one spike.

Require:
- threshold exceeded for multiple windows
- cooldown period after a transition
- rollback or rejection if post-transition metrics worsen

Example policy:

```text
if proposal_score > threshold for k consecutive windows:
    commit transition
else:
    continue observing
```

This prevents chatter and fake oscillation.

## Where this fits in current SCBE

Best first integration layer:
- embeddings
- routing corridors
- governance regions
- agent handoff graph

Not first target:
- raw neural weight tensor
- literal soap-film PDE optimization
- literal string-net topological phase machinery

Use current observables as transition inputs:
- tongue coordinates
- null-space signatures
- session suspicion
- harmonic cost
- drift
- governance disagreement

Operational flow:

```text
prompt
-> 14-layer observables
-> region assignment
-> transition proposal engine
-> invariant check
-> commit / reject
-> route execution
```

## Honest mapping for current terminology

Current honest meanings:
- `popping` = removing or quarantining a region/corridor whose support is low and instability is high
- `merging` = collapsing two semantically equivalent safe regions into one governed region
- `membrane` = decision boundary / handoff boundary
- `bubble` = tracked semantic/governance region
- `string operator` = audited graph rewrite rule

## Best first experiment

Build a synthetic transition lab with 6-12 regions.

For each step:
- update support
- update null profile
- update harmonic cost
- evaluate merge / split / pop / reroute proposals
- commit only energy-reducing transitions
- log accepted transitions

Success criteria:
- total energy trends downward
- false transitions stay low
- low-support unstable regions get popped or quarantined
- duplicate safe regions merge
- reroutes reduce corridor instability

## Important boundary

This idea is currently best treated as:
- research guidance
- architecture refinement
- future control-layer design

It is not yet a literal statement of shipped implementation.

## Clean summary sentence

`Topological transitions in SCBE should be implemented as audited graph rewrites over hyperbolic semantic regions, triggered by energy reduction, structured-absence signals, and governance invariants.`

## Next implementation candidates

1. `minimal_topology_lab.py`
- synthetic regions, operators, and energy tracking

2. `TOPOLOGICAL_TRANSITIONS.md`
- fuller research spec with diagrams and operator definitions

3. tests for:
- merge guard conditions
- split detection under sustained bifurcation
- pop of unstable low-support regions
- reroute under lower-cost alternate path
