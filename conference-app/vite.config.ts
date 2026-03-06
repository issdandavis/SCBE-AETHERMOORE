import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  root: 'src/frontend',
  resolve: {
    alias: {
      '@shared': path.resolve(__dirname, 'src/shared'),
      '@api': path.resolve(__dirname, 'src/api'),
      '@frontend': path.resolve(__dirname, 'src/frontend'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:3001',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: '../../dist/frontend',
  },
});
