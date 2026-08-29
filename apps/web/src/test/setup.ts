import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

afterEach(() => {
  cleanup();
  // Les tests de design (environnement node) n'ont pas de `window`.
  if (typeof window !== 'undefined') {
    window.localStorage.clear();
  }
});
