import { render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { DATA_STATE_LABELS, DataStateBoundary } from './DataStateBoundary.tsx';

const CHILD_TEXT = 'contenu nominal daté';
const child = <p>{CHILD_TEXT}</p>;

afterEach(() => {
  vi.restoreAllMocks();
});

describe('DataStateBoundary — libellés français stables', () => {
  it('expose les 8 libellés canoniques', () => {
    expect(DATA_STATE_LABELS).toEqual({
      loading: 'Chargement',
      refreshing: 'Actualisation',
      empty: 'Aucune donnée',
      partial: 'Données partielles',
      delayed: 'Données différées',
      stale: 'Données périmées',
      offline: 'Hors ligne',
      error: 'Erreur de données',
    });
  });
});

describe('DataStateBoundary — 8 états + ready', () => {
  it("ready : rend les enfants sans message d'état", () => {
    render(<DataStateBoundary state="ready">{child}</DataStateBoundary>);
    expect(screen.getByText(CHILD_TEXT)).toBeDefined();
    expect(screen.queryByRole('status')).toBeNull();
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('loading : squelette seul, aucun contenu affiché', () => {
    render(<DataStateBoundary state="loading">{child}</DataStateBoundary>);
    const status = screen.getByRole('status');
    expect(status.getAttribute('aria-busy')).toBe('true');
    expect(screen.getByText('Chargement')).toBeDefined();
    expect(screen.queryByText(CHILD_TEXT)).toBeNull();
  });

  it("refreshing : l'ancien contenu reste visible avec sa date", () => {
    render(
      <DataStateBoundary state="refreshing" asOfLabel="14:32:05 UTC">
        {child}
      </DataStateBoundary>,
    );
    expect(screen.getByText('Actualisation')).toBeDefined();
    expect(screen.getByText(CHILD_TEXT)).toBeDefined();
    expect(screen.getByText('14:32:05 UTC')).toBeDefined();
  });

  it('empty : cause affichée, jamais une valeur zéro fabriquée', () => {
    render(
      <DataStateBoundary state="empty" detail="Aucune position déclarée pour ce compte.">
        {child}
      </DataStateBoundary>,
    );
    expect(screen.getByText('Aucune donnée')).toBeDefined();
    expect(screen.getByText('Aucune position déclarée pour ce compte.')).toBeDefined();
    expect(screen.queryByText(CHILD_TEXT)).toBeNull();
  });

  it('partial : contenu visible + couverture manquante annoncée', () => {
    render(
      <DataStateBoundary state="partial" detail="2 sources sur 3 disponibles.">
        {child}
      </DataStateBoundary>,
    );
    expect(screen.getByText('Données partielles')).toBeDefined();
    expect(screen.getByText('2 sources sur 3 disponibles.')).toBeDefined();
    expect(screen.getByText(CHILD_TEXT)).toBeDefined();
  });

  it('delayed : badge et retard annoncé, jamais « live »', () => {
    render(
      <DataStateBoundary state="delayed" detail="Cotations différées de 15 minutes.">
        {child}
      </DataStateBoundary>,
    );
    expect(screen.getByText('Données différées')).toBeDefined();
    expect(screen.getByText('Cotations différées de 15 minutes.')).toBeDefined();
    expect(screen.getByText(CHILD_TEXT)).toBeDefined();
  });

  it('stale : watermark avec heure exacte fournie par props', () => {
    render(
      <DataStateBoundary state="stale" asOfLabel="hier 21:59:00 UTC">
        {child}
      </DataStateBoundary>,
    );
    expect(screen.getByText('Données périmées')).toBeDefined();
    expect(screen.getByText('hier 21:59:00 UTC')).toBeDefined();
    expect(screen.getByText(CHILD_TEXT)).toBeDefined();
  });

  it('offline : snapshot local daté conservé', () => {
    render(
      <DataStateBoundary state="offline" asOfLabel="snapshot du 27/08 22:00 UTC">
        {child}
      </DataStateBoundary>,
    );
    expect(screen.getByText('Hors ligne')).toBeDefined();
    expect(screen.getByText('snapshot du 27/08 22:00 UTC')).toBeDefined();
    expect(screen.getByText(CHILD_TEXT)).toBeDefined();
  });

  it('error avec dernière donnée valide : alerte + diagnostic + contenu conservé', () => {
    render(
      <DataStateBoundary state="error" detail="Source indisponible (diagnostic transmis).">
        {child}
      </DataStateBoundary>,
    );
    expect(screen.getByRole('alert')).toBeDefined();
    expect(screen.getByText('Erreur de données')).toBeDefined();
    expect(screen.getByText('Source indisponible (diagnostic transmis).')).toBeDefined();
    expect(screen.getByText(CHILD_TEXT)).toBeDefined();
  });

  it('error sans contenu : message seul, pas de faux succès', () => {
    render(<DataStateBoundary state="error" detail="Flux interrompu." />);
    expect(screen.getByRole('alert')).toBeDefined();
    expect(screen.getByText('Erreur de données')).toBeDefined();
    expect(screen.getByText('Flux interrompu.')).toBeDefined();
  });
});

describe("DataStateBoundary — l'état vient des props, jamais de l'horloge", () => {
  it("ne lit jamais l'horloge du navigateur au rendu", () => {
    const nowSpy = vi.spyOn(Date, 'now');
    for (const state of [
      'ready',
      'loading',
      'refreshing',
      'empty',
      'partial',
      'delayed',
      'stale',
      'offline',
      'error',
    ] as const) {
      const { unmount } = render(
        <DataStateBoundary state={state} detail="détail" asOfLabel="12:00:00 UTC">
          {child}
        </DataStateBoundary>,
      );
      unmount();
    }
    expect(nowSpy).not.toHaveBeenCalled();
  });
});

describe('DataStateBoundary — le squelette a la FORME de ce qui vient', () => {
  it('rend le squelette fourni À LA PLACE du rectangle générique', () => {
    // Un rectangle de hauteur arbitraire fait SAUTER la page au moment où la
    // donnée arrive : la carte grandit ou rétrécit, et ce qu'on lisait plus bas
    // se déplace sous le curseur. Le squelette qui réserve la place réelle
    // supprime ce sursaut — c'est sa seule raison d'être.
    const { container } = render(
      <DataStateBoundary state="loading" skeleton={<div data-testid="forme-reelle" />}>
        <p>contenu</p>
      </DataStateBoundary>,
    );
    expect(screen.getByTestId('forme-reelle')).toBeDefined();
    expect(container.querySelector('.vx-dsb-skeleton')).toBeNull();
  });

  it('garde le rectangle générique quand aucune forme n’est déclarée', () => {
    // Le défaut reste sûr : mieux vaut un rectangle qu'un vide, et une page qui
    // n'a pas encore décidé de sa forme ne doit pas perdre son état d'attente.
    const { container } = render(<DataStateBoundary state="loading">contenu</DataStateBoundary>);
    expect(container.querySelector('.vx-dsb-skeleton')).not.toBeNull();
  });

  it('ne montre AUCUNE valeur pendant l’attente', () => {
    const { container } = render(
      <DataStateBoundary state="loading" skeleton={<div data-testid="forme-reelle" />}>
        <p>111,23 SYN</p>
      </DataStateBoundary>,
    );
    expect(container.textContent ?? '').not.toContain('111,23');
  });
});
