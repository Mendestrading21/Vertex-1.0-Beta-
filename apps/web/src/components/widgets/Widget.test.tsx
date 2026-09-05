import { act, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { ModuleState } from '../moduleState.ts';
import { MODULE_STATES, Widget } from './Widget.tsx';

/**
 * Le conteneur du socle v2. Ce qu'il doit prouver :
 *   1. la surface n'est PAS redéclarée : le widget est un porteur d'état
 *      autour d'une `Card` (revue C0, point D1) ;
 *   2. un seul porteur de `data-rank` — la `Card` (revue C0, point 3) ;
 *   3. les ONZE états de `ModuleState`, pas huit : `auth-required` et
 *      `closed` existent et se rendent (revue C0, point D6) ;
 *   4. aucun `0`, aucun tiret ambigu quand la donnée manque ;
 *   5. la surbrillance d'une valeur mise à jour est UNIQUE et bornée.
 */

const SERVED = {
  asOf: '2026-09-03T08:40:00Z',
  ageSeconds: 4,
  snapshotVersion: 42290,
  population: 'REAL',
} as const;

function renderWidget(state: ModuleState, extra: Record<string, unknown> = {}) {
  return render(
    <Widget
      id="global-market"
      size="S"
      kicker="MARCHÉ"
      title="Marché global"
      titleId="w-global-market"
      state={state}
      served={SERVED}
      {...extra}
    >
      <p data-testid="contenu">contenu servi</p>
    </Widget>,
  );
}

describe('Widget — conteneur du socle v2', () => {
  it('ne redéclare aucune surface : la carte reste la seule surface', () => {
    const { container } = renderWidget('ready');
    const shell = container.querySelector('.vx-w2');
    expect(shell).not.toBeNull();
    expect(shell?.tagName).toBe('DIV');
    // La surface vient de `.vx-card` ; `.vx-w2` ne porte que la composition.
    expect(shell?.querySelector(':scope > .vx-card')).not.toBeNull();
    expect(shell?.getAttribute('data-module')).toBe('global-market');
    expect(shell?.getAttribute('data-size')).toBe('S');
  });

  it('un seul porteur de data-rank : la Card', () => {
    const { container } = renderWidget('ready', { rank: 'dominant' });
    expect(container.querySelectorAll('[data-rank]')).toHaveLength(1);
    expect(container.querySelector('.vx-card')?.getAttribute('data-rank')).toBe('dominant');
    expect(container.querySelector('.vx-w2')?.hasAttribute('data-rank')).toBe(false);
  });

  it('les ONZE états de ModuleState sont couverts, pas huit', () => {
    expect([...MODULE_STATES].sort()).toEqual(
      [
        'auth-required',
        'closed',
        'delayed',
        'empty',
        'error',
        'loading',
        'offline',
        'partial',
        'ready',
        'refreshing',
        'stale',
      ].sort(),
    );
  });

  it.each(MODULE_STATES)('état %s : en-tête et méta toujours visibles', (state) => {
    const { container, unmount } = renderWidget(state);
    expect(screen.getByRole('heading', { name: 'Marché global' })).toBeDefined();
    expect(container.querySelector('.vx-w2-meta')).not.toBeNull();
    expect(container.querySelector('.vx-w2')?.getAttribute('data-state')).toBe(state);
    unmount();
  });

  it.each(['loading', 'empty', 'error', 'auth-required', 'closed', 'offline'] as const)(
    'état %s : le contenu servi est MASQUÉ (jamais un zéro de remplacement)',
    (state) => {
      const { container, unmount } = renderWidget(state);
      expect(screen.queryByTestId('contenu')).toBeNull();
      const texte = container.textContent ?? '';
      expect(texte).not.toMatch(/(^|\s)0(\s|$)/);
      expect(texte).not.toMatch(/(^|\s)—(\s|$)/);
      unmount();
    },
  );

  it.each(['ready', 'refreshing', 'stale', 'partial', 'delayed'] as const)(
    'état %s : le contenu servi est visible',
    (state) => {
      const { unmount } = renderWidget(state);
      expect(screen.getByTestId('contenu')).toBeDefined();
      unmount();
    },
  );

  it('état loading : un squelette, jamais une valeur', () => {
    const { container } = renderWidget('loading');
    expect(container.querySelector('.vx-w2-skeleton')).not.toBeNull();
  });

  it('la conclusion n’existe que si elle est SERVIE, et elle est verbatim', () => {
    const { container, rerender } = render(
      <Widget id="m" size="S" title="T" state="ready" served={SERVED} conclusion={null}>
        <p>x</p>
      </Widget>,
    );
    expect(container.querySelector('.vx-w2-conclusion')).toBeNull();
    rerender(
      <Widget
        id="m"
        size="S"
        title="T"
        state="ready"
        served={SERVED}
        conclusion="Couverture sous le seuil : breadth non calculable."
      >
        <p>x</p>
      </Widget>,
    );
    expect(container.querySelector('.vx-w2-conclusion')?.textContent).toBe(
      'Couverture sous le seuil : breadth non calculable.',
    );
  });

  it('âge non publié et nature non déclarée sont DITS', () => {
    render(
      <Widget id="m" size="S" title="T" state="ready" served={{ asOf: null }}>
        <p>x</p>
      </Widget>,
    );
    expect(screen.getByText(/âge non publié/)).toBeDefined();
    expect(screen.getByText(/NATURE NON DÉCLARÉE/)).toBeDefined();
  });

  it('l’horodatage servi est porté par <time dateTime> et la version est affichée', () => {
    const { container } = renderWidget('ready');
    const time = container.querySelector('time');
    expect(time?.getAttribute('dateTime')).toBe('2026-09-03T08:40:00Z');
    expect(container.textContent).toContain('v42290');
  });
});

describe('Widget — surbrillance d’une valeur mise à jour', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it('data-updated est posé au changement de snapshot_version puis RETIRÉ', () => {
    const { container, rerender } = render(
      <Widget id="m" size="S" title="T" state="ready" served={{ ...SERVED, snapshotVersion: 1 }}>
        <p>x</p>
      </Widget>,
    );
    expect(container.querySelector('.vx-w2')?.hasAttribute('data-updated')).toBe(false);

    rerender(
      <Widget id="m" size="S" title="T" state="ready" served={{ ...SERVED, snapshotVersion: 2 }}>
        <p>x</p>
      </Widget>,
    );
    expect(container.querySelector('.vx-w2')?.getAttribute('data-updated')).toBe('true');

    act(() => {
      vi.advanceTimersByTime(1200);
    });
    expect(container.querySelector('.vx-w2')?.hasAttribute('data-updated')).toBe(false);
  });

  // LOT T6 — LES DEUX DURÉES, DISTINGUÉES. Le test existant avançait de
  // 1200 ms : il couvrait les deux cas sans jamais les séparer, donc la durée
  // longue n'était vérifiée par rien. Ces deux tests les distinguent.
  //
  // PRÉCISION QUI COMPTE : ils ne dépendent PAS du double `matchMedia` posé
  // dans `src/test/setup.ts` — le second pose le sien. Ce que le double
  // change, c'est le chemin par DÉFAUT, qui passait toujours par la trappe
  // `typeof !== 'function'`, et surtout les erreurs non capturées de
  // `fancy-canvas`. Ne pas confondre les deux preuves.
  it('mouvement normal : la surbrillance dure 600 ms, pas davantage', () => {
    const { container, rerender } = render(
      <Widget id="m" size="S" title="T" state="ready" served={{ ...SERVED, snapshotVersion: 1 }}>
        <p>x</p>
      </Widget>,
    );
    rerender(
      <Widget id="m" size="S" title="T" state="ready" served={{ ...SERVED, snapshotVersion: 2 }}>
        <p>x</p>
      </Widget>,
    );
    act(() => {
      vi.advanceTimersByTime(599);
    });
    expect(container.querySelector('.vx-w2')?.getAttribute('data-updated')).toBe('true');
    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(container.querySelector('.vx-w2')?.hasAttribute('data-updated')).toBe(false);
  });

  it('mouvement réduit : l’attribut TIENT PLUS LONGTEMPS, parce que la durée CSS tombe à zéro', () => {
    // Sous `prefers-reduced-motion`, la transition CSS ne dure plus rien : si
    // l'attribut partait au même instant, la mise à jour ne se verrait pas du
    // tout. Il reste donc posé plus longtemps et se lit comme un contour
    // statique (`docs/05-design/MOTION_AND_MICROINTERACTIONS.md`).
    const reel = window.matchMedia;
    window.matchMedia = ((requete: string) =>
      ({
        media: requete,
        matches: requete.includes('prefers-reduced-motion'),
        onchange: null,
        addEventListener: () => undefined,
        removeEventListener: () => undefined,
        addListener: () => undefined,
        removeListener: () => undefined,
        dispatchEvent: () => false,
      }) as MediaQueryList) as typeof window.matchMedia;
    try {
      const { container, rerender } = render(
        <Widget id="m" size="S" title="T" state="ready" served={{ ...SERVED, snapshotVersion: 1 }}>
          <p>x</p>
        </Widget>,
      );
      rerender(
        <Widget id="m" size="S" title="T" state="ready" served={{ ...SERVED, snapshotVersion: 2 }}>
          <p>x</p>
        </Widget>,
      );
      act(() => {
        vi.advanceTimersByTime(600);
      });
      // Durée normale écoulée : sous mouvement réduit, l'attribut TIENT.
      expect(container.querySelector('.vx-w2')?.getAttribute('data-updated')).toBe('true');
      act(() => {
        vi.advanceTimersByTime(400);
      });
      expect(container.querySelector('.vx-w2')?.hasAttribute('data-updated')).toBe(false);
    } finally {
      window.matchMedia = reel;
    }
  });

  it('aucune animation infinie : un seul minuteur, pas d’intervalle', () => {
    const spy = vi.spyOn(globalThis, 'setInterval');
    const { rerender } = render(
      <Widget id="m" size="S" title="T" state="ready" served={{ ...SERVED, snapshotVersion: 1 }}>
        <p>x</p>
      </Widget>,
    );
    rerender(
      <Widget id="m" size="S" title="T" state="ready" served={{ ...SERVED, snapshotVersion: 2 }}>
        <p>x</p>
      </Widget>,
    );
    expect(spy).not.toHaveBeenCalled();
    spy.mockRestore();
  });

  it('sans provenance passée, AUCUNE ligne de méta n’est écrite', () => {
    /**
     * Un module de soutien partage la source de la dominante, déjà datée au
     * même écran. Rendre sa méta y écrivait « âge non publié · instantané non
     * daté · version non publiée · NATURE NON DÉCLARÉE » — quatre absences
     * pour une provenance que personne n'avait demandée, et le bruit
     * l'emportait sur la donnée dans une carte d'une colonne.
     */
    const { container } = render(
      <Widget id="m" size="S" title="Sans provenance" state="ready">
        <p>contenu servi</p>
      </Widget>,
    );
    expect(container.querySelector('.vx-w2-meta')).toBeNull();
    expect(container.textContent).not.toContain('non publié');
    expect(container.textContent).toContain('contenu servi');
  });
});
