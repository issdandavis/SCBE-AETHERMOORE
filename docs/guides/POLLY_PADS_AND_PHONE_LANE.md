# Polly Pads And Phone Lane

This guide covers governed workspaces, HOT/SAFE execution zones, and the Android hand.

## Core Files

- `src/fleet/polly-pad-runtime.ts`
- `src/browser/hydra_android_hand.py`
- `scripts/system/hydra_android_control.py`
- `scripts/system/start_polly_pad_emulator.ps1`
- `scripts/system/stop_polly_pad_emulator.ps1`
- `kindle-app/www/`

## What Polly Pads Are

Polly Pads are governed workspaces for units, agents, or tasks. Each pad starts in a `HOT` exploratory zone and promotes to `SAFE` only when the SCBE thresholds allow it.

## Android Hand CLI

```powershell
python scripts/system/hydra_android_control.py status
python scripts/system/hydra_android_control.py launch-reader
python scripts/system/hydra_android_control.py observe --name phone-check
```

Example gestures:

```powershell
python scripts/system/hydra_android_control.py tap --x 500 --y 1200
python scripts/system/hydra_android_control.py swipe --x1 500 --y1 1400 --x2 500 --y2 400
```

## Pad Runtime Role

- `HOT`: exploratory, plan-heavy, reduced tool set
- `SAFE`: approved execution, stronger tool access
- quorum and SCBE decisions control promotion and demotion

## When To Use This Lane

- You want governed execution per mode or per unit.
- You are reading or testing mobile surfaces.
- You need the Android emulator as an operator device rather than a separate toy environment.
