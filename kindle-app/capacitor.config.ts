import type { CapacitorConfig } from '@capacitor/cli';

// Build target: set AETHERCODE_TARGET=kindle for Amazon Appstore builds
const isKindle = process.env.AETHERCODE_TARGET === 'kindle';

const config: CapacitorConfig = {
  appId: 'com.issdandavis.aethercode',
  appName: 'AetherCode',
  webDir: 'www',
  server: {
    androidScheme: 'https',
    allowNavigation: [
      '34.134.99.90',
      'aethercode.issdandavis.com',
      '*.googleapis.com',
      '*.openai.com',
      '*.anthropic.com',
      '*.groq.com',
      '*.x.ai',
      '*.huggingface.co',
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
