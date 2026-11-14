import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    host: '0.0.0.0',
    port: 5173,
    allowedHosts: true,
    fs: { allow: ['..'] }, // shared game logic lives in ../functions/src
  },
  build: {
    target: 'es2020',
    chunkSizeWarningLimit: 2000,
  },
});
