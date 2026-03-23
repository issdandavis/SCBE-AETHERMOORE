# Launcher Matrix

Use this file only when the emulator launcher needs options, tuning, or recovery detail.

## Canonical Scripts

- Repo launcher: `C:\Users\issda\SCBE-AETHERMOORE\scripts\system\start_polly_pad_emulator.ps1`
- Repo recovery: `C:\Users\issda\SCBE-AETHERMOORE\scripts\system\stop_polly_pad_emulator.ps1`
- Phone mode only: `C:\Users\issda\SCBE-AETHERMOORE\scripts\system\start_aether_phone_mode.ps1`

## Common Launch Shapes

Default:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/system/start_polly_pad_emulator.ps1
```

Preview only:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/system/start_polly_pad_emulator.ps1 -PreviewOnly
```

Attach to existing booted emulator:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/system/start_polly_pad_emulator.ps1 -SkipEmulatorLaunch
```

Reading preset:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/system/start_polly_pad_emulator.ps1 `
  -ScreenPreset reading `
  -RuntimeDensity 340 `
  -FontScale 1.12
```

Persist more virtual resources:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/system/start_polly_pad_emulator.ps1 `
  -PersistCpuCores 6 `
  -PersistRamMB 4096 `
  -ColdBoot
```

## Known Failure Modes

- `emu-last-feature-flags.protobuf.lock`
  - Usually stale emulator/qemu state, not missing files.
  - Use the stop script, then relaunch.

- `Running multiple emulators with the same AVD`
  - There is already a live emulator/qemu process for this AVD.
  - Check `adb devices -l` before assuming failure.

- Launcher timeout while `adb devices -l` shows `emulator-5554`
  - The wrapper false-failed; attach to the live emulator instead of relaunching.

- Chrome `FirstRunActivity`
  - Browser route opened, but Chrome’s one-time setup blocks the real page.
  - Complete the one-time flow, then rerun the route launch.

## Evidence Files

- `C:\Users\issda\SCBE-AETHERMOORE\artifacts\kindle\emulator\`
- `C:\Users\issda\SCBE-AETHERMOORE\artifacts\system\aether_phone_mode_pids.json`
