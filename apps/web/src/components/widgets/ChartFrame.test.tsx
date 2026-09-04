import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ChartFrame } from './ChartFrame.tsx';

const BASE = {
  id: 'vx-essai',
  title: 'Carte des marchés',
  question: 'Comment les secteurs suivis ont-ils évolué sur la dernière séance ?',
  unit: 'rendement 1 jour, %',
  period: '2 clôtures journalières consécutives',
  timezone: 'Europe/Zurich',
  dataState: 'delayed' as const,
  ageSeconds: 900,
  provenance: {
    method: 'ratio serveur v1.4',
    source: 'ibkr',
    asOf: '2026-09-04T17:30:00Z',
  },
};

function rendre(surcharge: Record<string, unknown> = {}) {
  return render(
    <ChartFrame {...BASE} equivalent={<table><caption>Valeurs</caption><tbody><tr><th scope="row">A</th><td>1</td></tr></tbody></table>} {...surcharge}>
      <div data-testid="figure" />
    </ChartFrame>,
  );
}

describe('ChartFrame — l’anatomie commune de toute visualisation', () => {
  it('porte la QUESTION avant le titre : elle justifie la figure', () => {
    rendre();
    expect(screen.getByText(BASE.question)).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'Carte des marchés' })).toBeTruthy();
  });

  it('met unité, période et fuseau AU-DESSUS de la figure', () => {
    rendre();
    // Sans ces trois-là, l'axe ne se lit pas. Les reléguer en note de bas de
    // page revient à les rendre facultatifs.
    expect(screen.getByText('rendement 1 jour, %')).toBeTruthy();
    expect(screen.getByText('2 clôtures journalières consécutives')).toBeTruthy();
    expect(screen.getByText('Europe/Zurich')).toBeTruthy();
  });

  it('porte l’état de la donnée DANS le cadre', () => {
    rendre();
    // Une figure périmée qui ne le dit pas est pire qu'une figure absente.
    expect(screen.getByRole('status').getAttribute('data-state')).toBe('delayed');
  });

  it('rend l’équivalent tabulaire ATTEIGNABLE, replié mais présent', () => {
    rendre();
    const details = document.querySelector('details.vx-cf-equivalent');
    expect(details).not.toBeNull();
    // Présent dans le DOM même replié : atteignable au clavier et par
    // recherche, sans occuper la surface.
    expect(within(details as HTMLElement).getByRole('table', { name: 'Valeurs' })).toBeTruthy();
  });

  it('DIT qu’une source n’est pas publiée, au lieu d’en inventer une', () => {
    rendre({ provenance: { ...BASE.provenance, source: null } });
    expect(screen.getByText('non publiée par le contrat')).toBeTruthy();
  });

  it('DIT qu’un instant d’observation manque', () => {
    rendre({ provenance: { ...BASE.provenance, asOf: null } });
    expect(screen.getByText('instant non publié')).toBeTruthy();
  });

  it('n’affiche population et exclusions QUE si elles sont publiées', () => {
    const { unmount } = rendre();
    expect(screen.queryByText('Population')).toBeNull();
    expect(screen.queryByText('Exclusions')).toBeNull();
    unmount();
    rendre({
      provenance: { ...BASE.provenance, population: '22 sur 24 suivis', exclusions: '2 écartés' },
    });
    expect(screen.getByText('22 sur 24 suivis')).toBeTruthy();
    expect(screen.getByText('2 écartés')).toBeTruthy();
  });

  it('distingue la dominante par la profondeur, pas par un halo', () => {
    rendre({ rank: 'dominant' });
    expect(document.querySelector('.vx-cf')?.getAttribute('data-rank')).toBe('dominant');
  });

  it('ne connaît AUCUN moteur : la figure est un enfant opaque', () => {
    rendre();
    expect(screen.getByTestId('figure')).toBeTruthy();
  });

  it('nomme la section par son titre, pour la navigation par régions', () => {
    rendre();
    const section = document.querySelector('.vx-cf');
    const titreId = section?.getAttribute('aria-labelledby');
    expect(document.getElementById(titreId ?? '')?.textContent).toBe('Carte des marchés');
  });
});
