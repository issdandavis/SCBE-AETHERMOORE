# GeoSeal And Tongues

This guide covers the trust, tokenization, and identity layer.

## Core Files

- `six-tongues-cli.py`
- `src/geoseal.ts`
- `src/aaoe/agent_identity.py`
- `src/harmonic/`
- `src/governance/`

## What Each Piece Does

- `six-tongues-cli.py`: user-facing CLI for Sacred Tongues encoding, decoding, cross-translation, blending, and GeoSeal encrypt/decrypt flows.
- `src/geoseal.ts`: geometric trust kernel used by the TypeScript runtime.
- `src/aaoe/agent_identity.py`: GeoSeal identity, access tiers, governance score, and entry-token model for agents.

## Fast Commands

### Run the built-in self-test

```powershell
python six-tongues-cli.py
```

### Encode / decode payloads

```powershell
echo "hello" | python six-tongues-cli.py encode --tongue KO
echo "kor'a ..." | python six-tongues-cli.py decode --tongue KO
```

### Cross-translate a token stream

```powershell
python six-tongues-cli.py xlate --src KO --dst AV
```

### Inspect unified CLI routing into the tongues lane

```powershell
python scripts/scbe-system-cli.py tongues --help
```

## When To Use GeoSeal

- You need trust-aware routing or geometric risk scoring.
- You are moving bytes or records through Sacred Tongues.
- You need agent identity, access tiering, or governance history.
- You are building a task that should be sealed, attested, or routed by tongue.

## Mental Model

1. Sacred Tongues classify the domain of the task.
2. GeoSeal assigns geometric trust and context boundaries.
3. Agent identity and governance score determine who is allowed to do what.
4. The harmonic/governance layers convert that into ALLOW, QUARANTINE, ESCALATE, or DENY behavior.
