# Polly Pad Emulator Lane

`scripts/system/start_polly_pad_emulator.ps1` turns the Android emulator into a repeatable SCBE phone lane instead of a one-off QA target.

It handles:

- launching the `SCBE_Pixel_6_API35` AVD
- starting local phone mode on `8088`
- tuning the emulator for AI/operator use
- installing or launching `AetherCode`
- opening Polly Pad or Chat routes through `10.0.2.2`
- sideloading extra APKs from local disk
- optionally persisting CPU, RAM, and display changes into the AVD profile

## Basic

```powershell
powershell -ExecutionPolicy Bypass -File scripts/system/start_polly_pad_emulator.ps1
```

Default behavior:

- uses the Pixel 6 API 35 AVD
- starts `start_aether_phone_mode.ps1` with emulator host bridge `10.0.2.2`
- launches the AVD with `-no-snapshot-load -gpu auto -skin 540x1200 -no-boot-anim`
- applies the `roomy` preset (`wm density 360`, `font_scale 1.08`)
- launches `AetherCode`
- opens `http://10.0.2.2:8088/polly-pad.html`

## Bigger UI

```powershell
powershell -ExecutionPolicy Bypass -File scripts/system/start_polly_pad_emulator.ps1 `
  -ScreenPreset reading `
  -RuntimeDensity 340 `
  -FontScale 1.12
```

Use runtime density and font scale when the goal is larger touch targets and easier reading inside the current booted emulator.

## More Power

```powershell
powershell -ExecutionPolicy Bypass -File scripts/system/start_polly_pad_emulator.ps1 `
  -PersistCpuCores 6 `
  -PersistRamMB 4096 `
  -ColdBoot
```

These settings patch the AVD config on disk:

- `hw.cpu.ncore`
- `hw.ramSize`
- `vm.heapSize`

They improve the virtual device profile, but real performance still depends on the host machine and emulator acceleration.

## Bigger Virtual Device

```powershell
powershell -ExecutionPolicy Bypass -File scripts/system/start_polly_pad_emulator.ps1 `
  -PersistWidth 1440 `
  -PersistHeight 3120 `
  -PersistDensity 420 `
  -ColdBoot
```

This changes the AVD profile itself, not just the current boot session.

## Polly Pad + Chat

```powershell
powershell -ExecutionPolicy Bypass -File scripts/system/start_polly_pad_emulator.ps1 `
  -LaunchRoutes @('/polly-pad.html','/chat.html')
```

If Chrome has never been opened on that emulator before, Android may stop at `FirstRunActivity`. Complete that one-time screen once, then rerun the route launch.

## Sideload More Apps

```powershell
powershell -ExecutionPolicy Bypass -File scripts/system/start_polly_pad_emulator.ps1 `
  -ExtraApkPaths @(
    'C:\path\to\termux.apk',
    'C:\path\to\chrome.apk'
  )
```

The current Pixel 6 AVD has `PlayStore.enabled=false`, so extra apps should be installed by APK path unless you rebuild the AVD with a Play Store image.

## Preview Only

```powershell
powershell -ExecutionPolicy Bypass -File scripts/system/start_polly_pad_emulator.ps1 -PreviewOnly
```

This resolves the SDK, AVD, routes, and status file without launching the emulator or touching ADB.

## Recovery

If you see `.protobuf.lock` or a stale emulator that is no longer visible to ADB:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/system/stop_polly_pad_emulator.ps1 -StopPhoneMode -StopAdbServer
```

Then relaunch cleanly:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/system/start_polly_pad_emulator.ps1
```
