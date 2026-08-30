/**
 * Propriétaire unique du téléchargement d'un texte servi par l'API.
 *
 * Il en existait TROIS copies (`PerformancePage.tsx`, `LedgerPanel.tsx`,
 * `MarketsTable.tsx`), portant toutes le même défaut. La première exécution
 * réelle des trois moteurs de rendu l'a mesuré : sur WebKit, l'export
 * « CSV + manifeste » de la page Performance ne produisait qu'UN fichier sur
 * deux. Les 659 autres tests passaient.
 *
 * DEUX CAUSES, corrigées ici :
 *
 * 1. `URL.revokeObjectURL(url)` était appelé SYNCHRONEMENT après `click()`.
 *    Le clic ne fait qu'ORDONNANCER le téléchargement ; WebKit lit l'URL
 *    ensuite, et la trouvait déjà révoquée. Chromium tolère la course, pas
 *    WebKit. La révocation est donc différée — l'URL objet est libérée à la
 *    tâche suivante, ce qui laisse le moteur la lire.
 * 2. Deux `click()` dans la même tâche : le second écrasait le premier. Les
 *    appelants rendent maintenant la main entre deux enregistrements via
 *    `yieldToBrowser()`.
 *
 * NON VÉRIFIÉ LOCALEMENT : les binaires Firefox et WebKit ne sont pas
 * téléchargeables depuis l'environnement de développement. Cette correction
 * ne peut être prouvée que par `.github/workflows/nightly.yml`.
 */

/** Délai avant révocation. Assez long pour que le moteur ait lu l'URL. */
const REVOCATION_DELAY_MS = 60_000;

/** Rend la main au navigateur, le temps qu'il ordonnance un téléchargement. */
export function yieldToBrowser(): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, 0);
  });
}

/** Déclenche le téléchargement navigateur d'un texte servi par l'API. */
export function saveTextAsFile(text: string, filename: string, mediaType: string): void {
  const blob = new Blob([text], { type: mediaType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  // JAMAIS de révocation synchrone ici : voir la cause 1 ci-dessus.
  window.setTimeout(() => {
    URL.revokeObjectURL(url);
  }, REVOCATION_DELAY_MS);
}
