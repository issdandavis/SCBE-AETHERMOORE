import type { CapacitorConfig } from '@capacitor/cli';

// Build target: set AETHERCODE_TARGET=kindle for Amazon Appstore builds
const target = (process.env.AETHERCODE_TARGET || '').toLowerCase();
const variant = (process.env.AETHERCODE_APP_VARIANT || '').toLowerCase();
const isKindle = target === 'kindle';
const isAetherBrowse = variant === 'aetherbrowse';
const appId = isAetherBrowse ? 'com.issdandavis.aetherbrowse' : 'com.issdandavis.aethercode';
const appName = isAetherBrowse ? 'AetherBrowse' : 'AetherCode';

const config: CapacitorConfig = {
  appId,
  appName,
  webDir: 'www',
  server: {
    androidScheme: 'https',
    allowNavigation: [
      '*',
    ],
  },
  android: {
    // Kindle Fire 7th gen = API 22, but Capacitor 7 needs 23+
    minSdkVersion: 23,
    targetSdkVersion: 35,
    allowMixedContent: true,
    // Debug in dev, disable in release
    webContentsDebuggingEnabled: !isKindle,
  },
  plugins: {
    SplashScreen: {
      launchShowDuration: 2000,
      backgroundColor: '#070b12',
      showSpinner: false,
      launchAutoHide: true,
      splashImmersive: true,
    },
    StatusBar: {
      style: 'DARK',
      backgroundColor: '#070b12',
    },
  },
};

export default config;
