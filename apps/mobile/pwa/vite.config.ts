import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

// https://vite.dev/config/
export default defineConfig({
  base: './',
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'icon-512.png'],
      manifest: {
        name: 'Aethermoor Bus',
        short_name: 'Aethermoor',
        description:
          'Mobile dashboard for SCBE-AETHERMOORE agents and the agent-bus event stream.',
        theme_color: '#08101a',
        background_color: '#08101a',
        display: 'standalone',
        orientation: 'portrait',
        start_url: '/',
        scope: '/',
        icons: [
          {
            src: 'icon-512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any',
          },
          {
            src: 'icon-512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable',
          },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,webmanifest}'],
        runtimeCaching: [
          {
            urlPattern: ({ url }) =>
              url.pathname.startsWith('/v1/') ||
              url.pathname.startsWith('/api/') ||
              url.pathname.startsWith('/health'),
            handler: 'NetworkFirst',
            options: {
              cacheName: 'aethermoor-api',
              networkTimeoutSeconds: 5,
              expiration: { maxEntries: 50, maxAgeSeconds: 300 },
            },
          },
        ],
      },
    }),
  ],
  server: { port: 5173, host: true },
  build: { outDir: 'dist', sourcemap: true },
});
