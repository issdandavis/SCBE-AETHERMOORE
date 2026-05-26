# Semantic Bus Scoring for Long Dialogue

Use this when the scene or passage has an AgentBus semantic decomposition attached.

## Expected Input Shape

The bus may expose semantic data in either camelCase or snake_case:

```json
{
  "semantic": {
    "atoms": [
      { "semanticId": "ANNOUNCE", "count": 1 },
      { "semanticId": "EXPAND", "count": 2 }
    ],
    "discourseProfile": "long_turn"
  },
  "discourse_profile": "long_turn"
}
```

Normalize:

- `profile = semantic.discourseProfile || discourse_profile`
- `atomIds = semantic.atoms[].semanticId`
- `atomCount[id] = semantic.atoms entry count`

## Atom-To-Rubric Map

The manual rubric remains authoritative. Semantic atoms provide evidence and warnings.

| Rubric dimension | Max | Helpful semantic evidence | Warning |
| --- | ---: | --- | --- |
| Reason to speak now | 2 | `ANNOUNCE`, `REQUEST`, `PIVOT` | No floor marker and no scene trigger |
| Concrete memory/example | 2 | `CARRY`, `EXPAND` | `CARRY` without a specific event is false confidence |
| Emotional pressure | 2 | `CARRY`, `PIVOT`, `BLOCK` | Atoms cannot prove wound; inspect prose |
| Listener reaction | 1 | `HOLD`, `REQUEST` | No `HOLD` and no gesture/silence in text |
| Physical anchor | 1 | Not reliably detectable | Must be manually checked |
| Controlled divergence | 1 | `PIVOT`, `EXPAND` | High pivot count without return phrase |
| Clean return/coda | 1 | `PIVOT` followed by resolution language | Must be manually checked |

## Profile Defaults

Start from these defaults, then adjust by reading the passage:

### `long_turn`

`ANNOUNCE + EXPAND`

- Turn management starts at 1/2.
- Controlled divergence starts at 1/1 if the examples are ordered.
- Listener reaction is not implied; still check for `HOLD` or physical response.

### `warranted_claim`

`CARRY`

- Concrete memory/example starts at 1/2.
- Emotional pressure may rise to 1/2 if the remembered event has cost.
- Upgrade to 2/2 only when the memory contains who/where/when/object/stakes.

### `floor_hold`

`REQUEST`

- Reason to speak now starts at 1/2.
- Listener pressure may rise to 1/1 if the passage shows the speaker noticing the listener.
- Too many permission tokens can sound apologetic or modern.

### `backchannel`

`HOLD` alone

- This is listener-only signal.
- Use it to preserve short responses like "Yes.", "I know.", "Mm.", "Go on."
- Do not expand backchannels into explanation unless the scene asks for it.

### `governance_steer`

`PIVOT + BLOCK`

- Treat as redirected argument, refusal, safety boundary, or institutional pressure.
- Useful for legal, sect, trial, administrative, or command scenes.
- Usually not enough for intimate long dialogue unless paired with `CARRY`.

## Density Warnings

Use atom counts to spot rhythm problems:

- `PIVOT >= 4`: likely over-steered; add a clean return or cut a branch.
- `EXPAND >= 4` with no `CARRY`: examples may feel generic.
- `REQUEST >= 3`: speaker may sound like they are asking permission too often.
- `ANNOUNCE` with no `EXPAND`: promised a long turn but did not develop it.
- `CARRY` with no object anchor in prose: memory is abstract, not embodied.
- No `HOLD` and no listener action: the other person may disappear.

## Assisted Scoring Procedure

1. Read the passage once without scoring.
2. Normalize the semantic atoms/profile if present.
3. Assign baseline hints from the profile defaults.
4. Manually inspect for:
   - object anchor
   - listener body
   - specific remembered event
   - return/coda
5. Produce:
   - total score out of 10
   - semantic profile
   - atom evidence
   - one most important fix

## Output Template

```text
Dialogue score: X/10
Semantic profile: long_turn
Atoms: ANNOUNCE x1, EXPAND x2, CARRY x1

What works:
- ...

Weakest dimension:
- Listener reaction: no HOLD atom and no visible listener body in the prose.

Fix:
- Add one silent listener beat after the memory lands: hand on cup, eyes moving to the door, refusal to answer.
```
