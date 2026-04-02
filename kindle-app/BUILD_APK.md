# Building AetherCode APK

## Prerequisites (one-time setup)

```powershell
# 1. Install Android Studio (for SDK + build tools)
#    https://developer.android.com/studio
#    During install, check: Android SDK, Android SDK Platform, Android Virtual Device

# 2. Set ANDROID_HOME (Android Studio installs SDK here by default)
$env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk"

# 3. Install Capacitor CLI (already in package.json)
cd kindle-app
npm install
```

## Build the APK

```powershell
cd C:\Users\issda\SCBE-AETHERMOORE\kindle-app

# 1. Sync web assets to Android project
npx cap sync android

# 2. Build debug APK (for testing on your phone)
cd android
.\gradlew assembleDebug

# APK output location:
# android/app/build/outputs/apk/debug/app-debug.apk
```

## Install on your phone

### Option A: USB cable
```powershell
# Connect phone via USB, enable USB debugging in Developer Options
adb install android/app/build/outputs/apk/debug/app-debug.apk
```

### Option B: Transfer the file
1. Copy `app-debug.apk` to your phone (email it, Google Drive, USB)
2. Tap the file on your phone
3. Allow "Install from unknown sources" when prompted
4. Done

### Option C: ADB over WiFi
```powershell
# Phone and PC on same WiFi
adb tcpip 5555
adb connect YOUR_PHONE_IP:5555
adb install android/app/build/outputs/apk/debug/app-debug.apk
```

## What the app does

- **Chat tab**: Talk to Polly (your HF model). Slash commands work without a token.
- **Code tab**: Write Python or JavaScript. Python runs on Polly Sandbox (HF Space). JS runs locally.
- **Explore tab**: Links to all SCBE surfaces — demos, enterprise, compliance, tests, GitHub.
- **"Ask AI to fix"**: When code errors, sends the error + code to Polly chat for explanation.

## Release build (for Google Play / sideload)

```powershell
cd android

# Generate signing key (one time)
keytool -genkeypair -v -keystore aethercode-release.keystore -alias aethercode -keyalg RSA -keysize 2048 -validity 10000

# Build release APK
.\gradlew assembleRelease

# APK: android/app/build/outputs/apk/release/app-release.apk
```

## Updating the app

After making changes to `www/`:
```powershell
cd kindle-app
npx cap sync android
cd android
.\gradlew assembleDebug
# Reinstall via ADB or file transfer
```
