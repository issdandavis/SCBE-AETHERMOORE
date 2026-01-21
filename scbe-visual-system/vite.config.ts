import path from 'path';
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

/**
 * SCBE Visual System - Vite Configuration
 *
 * This is the unified interface for SCBE-AETHERMOORE.
 * The visual computer serves as the OS, with SCBE providing security.
 */
export default defineConfig(({ mode }) => {
    const env = loadEnv(mode, '.', '');
    return {
      server: {
        port: 5173,
        host: '0.0.0.0',
        // Proxy API requests to SCBE Python backend
        proxy: {
          '/api': {
            target: 'http://localhost:8000',
            changeOrigin: true,
          },
        },
      },
      plugins: [react()],
      define: {
        'process.env.API_KEY': JSON.stringify(env.GEMINI_API_KEY),
        'process.env.GEMINI_API_KEY': JSON.stringify(env.GEMINI_API_KEY),
        'process.env.SCBE_VERSION': JSON.stringify('3.0.0'),
      },
      resolve: {
        alias: {
          '@': path.resolve(__dirname, '.'),
          '@scbe': path.resolve(__dirname, '../src'),
        }
      },
      build: {
        outDir: 'dist',
        sourcemap: true,
      }
    };
});
