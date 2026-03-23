# Verification Checklist

Use this checklist for future verifiable results.

## Packet Checks

1. Validate canonical tongue order: `KO, AV, RU, CA, UM, DR`.
2. Validate `tongue_mix` sums to `1.0` within tolerance.
3. Validate all timbre fields exist:
- `warmth`
- `brightness`
- `weight`
- `grain`
- `openness`
- `tension`
- `softness`
- `silence_affinity`
4. Validate `breath_plan` kinds are one of:
- `micro`
- `soft`
- `full`
- `shaken`

## Code Checks

If `scripts/voice_gen_hf.py` changes:

```powershell
python -m py_compile C:\Users\issda\SCBE-AETHERMOORE\scripts\voice_gen_hf.py
```

## Skill Validator

```powershell
python C:\Users\issda\.codex\skills\scbe-voice-render-verification\scripts\validate_voice_packet.py <packet.json>
```

## Reporting Standard

Return:

- files changed
- validator result
- whether packet mode was `minimal` or `layer14`
- remaining renderer gaps
