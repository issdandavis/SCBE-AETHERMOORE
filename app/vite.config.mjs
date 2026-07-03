import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';

export default defineConfig({
  plugins: [react()],
  base: './',
  server: { port: 3000, host: '127.0.0.1' },
  build: {
    outDir: path.resolve(__dirname, '../docs'),
    emptyOutDir: false,
    assetsDir: 'assets',
    sourcemap: false,
  },
});
