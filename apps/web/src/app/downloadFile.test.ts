/**
 * La première exécution des trois moteurs de rendu a mesuré, sur WebKit,
 * qu'un export « CSV + manifeste » ne produisait qu'UN fichier sur deux.
 * Ces tests épinglent les deux causes pour qu'elles ne reviennent pas.
 *
 * Ce qu'ils NE prouvent PAS : ils tournent sur jsdom, pas sur WebKit. Ils
 * prouvent la FORME du correctif — la révocation est différée, l'ordre des
 * appels est celui attendu — pas que WebKit délivre bien deux fichiers. Seul
 * `.github/workflows/nightly.yml` peut le prouver.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { saveTextAsFile, yieldToBrowser } from './downloadFile.ts';

describe('saveTextAsFile', () => {
  let revoked: string[];
  let created: number;
  let clicks: number;

  beforeEach(() => {
    vi.useFakeTimers();
    revoked = [];
    created = 0;
    clicks = 0;
    vi.stubGlobal('URL', {
      ...URL,
      createObjectURL: () => {
        created += 1;
        return `blob:synthetique-${created}`;
      },
      revokeObjectURL: (url: string) => {
        revoked.push(url);
      },
    });
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {
      clicks += 1;
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('ne révoque PAS l’URL objet dans la même tâche que le clic', () => {
    saveTextAsFile('a;b\n', 'fichier.csv', 'text/csv');
    expect(clicks).toBe(1);
    // C'est LA cause du défaut WebKit : le clic ordonnance le téléchargement,
    // le moteur lit l'URL ensuite. Révoquée trop tôt, il ne trouve rien.
    expect(revoked).toEqual([]);
  });

  it('révoque l’URL objet plus tard, sans la laisser fuir', () => {
    saveTextAsFile('a;b\n', 'fichier.csv', 'text/csv');
    vi.advanceTimersByTime(60_000);
    expect(revoked).toEqual(['blob:synthetique-1']);
  });

  it('retire l’ancre du document après le clic', () => {
    saveTextAsFile('a;b\n', 'fichier.csv', 'text/csv');
    expect(document.querySelectorAll('a[download]')).toHaveLength(0);
  });

  it('pose bien le nom de fichier demandé', () => {
    let nom: string | null = null;
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (
      this: HTMLAnchorElement,
    ) {
      nom = this.download;
    });
    saveTextAsFile('{}', 'vertex-performance-7-manifest.json', 'application/json');
    expect(nom).toBe('vertex-performance-7-manifest.json');
  });

  it('deux enregistrements séparés par yieldToBrowser produisent deux clics', async () => {
    saveTextAsFile('a;b\n', 'un.csv', 'text/csv');
    const attente = yieldToBrowser();
    vi.advanceTimersByTime(0);
    await attente;
    saveTextAsFile('{}', 'deux-manifest.json', 'application/json');
    expect(clicks).toBe(2);
    expect(created).toBe(2);
  });
});
