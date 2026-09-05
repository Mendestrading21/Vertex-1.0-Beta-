import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

/**
 * LOT T6 — `matchMedia` MANQUAIT À L'ENVIRONNEMENT, ET DES ERREURS NON
 * CAPTURÉES EN SORTAIENT.
 *
 * jsdom n'implémente pas `window.matchMedia`. Toute bibliothèque qui l'appelle
 * sans se protéger explose — et `fancy-canvas`, dépendance de Lightweight
 * Charts, l'appelle dans une MICRO-TÂCHE, donc APRÈS que le fichier de test a
 * rendu la main et que la fenêtre a été détruite. Résultat mesuré :
 * `vitest run` rapportait « 7 unhandled errors » à côté de 955 tests verts,
 * avec l'avertissement de Vitest lui-même — « This might cause false positive
 * tests ». Une suite verte accompagnée d'erreurs non capturées n'est pas une
 * preuve.
 *
 * CE QUE CE DOUBLE EST, ET CE QU'IL N'EST PAS. C'est un comblement de TROU
 * D'ENVIRONNEMENT, pas un contournement de test : dans tout navigateur réel,
 * `matchMedia` existe TOUJOURS. Il répond `matches: false` à chaque requête —
 * exactement ce que répond un navigateur sans préférence déclarée, qui est le
 * défaut. Aucune requête n'est interprétée, aucune n'est privilégiée : le
 * double ne simule pas un état de média, il rend la fonction appelable.
 *
 * Conséquence voulue : `prefersReducedMotion()` (`Widget.tsx`) cesse de sortir
 * par sa trappe `typeof !== 'function'` et exerce enfin sa vraie branche.
 */
if (typeof window !== 'undefined' && typeof window.matchMedia !== 'function') {
  window.matchMedia = (query: string): MediaQueryList => {
    const liste: MediaQueryList = {
      media: query,
      matches: false,
      onchange: null,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      // Les deux formes historiques : certaines bibliothèques n'ont jamais
      // migré vers `addEventListener`, et une absence les ferait échouer.
      addListener: () => undefined,
      removeListener: () => undefined,
      dispatchEvent: () => false,
    };
    return liste;
  };
}

afterEach(() => {
  cleanup();
  // Les tests de design (environnement node) n'ont pas de `window`.
  if (typeof window !== 'undefined') {
    window.localStorage.clear();
  }
});
