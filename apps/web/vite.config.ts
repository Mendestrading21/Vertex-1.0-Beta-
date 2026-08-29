/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

/**
 * Proxy `/api` → API locale (loopback uniquement) pour les serveurs de
 * développement et de prévisualisation Vite. Aucun rôle en production : le
 * build livré ne contient aucun proxy ni aucune adresse.
 */
const LOCAL_API_PROXY = {
  '/api': {
    target: 'http://127.0.0.1:8000',
    changeOrigin: false,
  },
} as const;

export default defineConfig({
  plugins: [react()],
  build: {
    target: 'es2022',
  },
  server: {
    proxy: LOCAL_API_PROXY,
  },
  preview: {
    proxy: LOCAL_API_PROXY,
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
    css: false,
  },
});
