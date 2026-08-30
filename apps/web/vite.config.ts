/// <reference types="vitest/config" />
import { fileURLToPath } from 'node:url';

import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

const WEB_ROOT = fileURLToPath(new URL('.', import.meta.url));
const DESIGN_ASSETS_ROOT = fileURLToPath(new URL('../../design-assets', import.meta.url));

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
    fs: {
      // Les glyphes audités vivent dans le catalogue partagé du dépôt.
      allow: [WEB_ROOT, DESIGN_ASSETS_ROOT],
    },
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
