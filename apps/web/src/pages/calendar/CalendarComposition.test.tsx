/**
 * Page Calendrier — la planche §11 est complète, servie ou déclarée (LOT-A7).
 *
 * Invariants : treize modules dans le DOM, une seule dominante (l'agenda),
 * deux absences au motif fermé sans chiffre, un fuseau d'affichage EXPLICITE
 * (UTC, navigateur, fuseaux de place publiés) sans conversion implicite, un
 * prochain événement sans compte à rebours, un inspecteur par défaut (le
 * snapshot publié) remplacé par l'événement ouvert.
 */
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ABSENCE_REASONS } from '../../components/AbsentModule.tsx';
import { makeCalendarResponse, makeMarketsOverview, makeNotEntitledCalendarResponse } from '../../test/fixtures.ts';
import { renderApp } from '../../test/render.tsx';
import { CALENDAR_MODULES, absentCalendarModules } from './calendarModules.ts';

const fetchMock = vi.fn<typeof fetch>();

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

function servir(calendar: unknown = makeCalendarResponse()): void {
  fetchMock.mockImplementation((entree: unknown) => {
    const url = typeof entree === 'string' ? entree : String((entree as Request).url);
    if (url.includes('/v1/calendar')) {
      return Promise.resolve(jsonResponse(calendar));
    }
    return Promise.resolve(jsonResponse(makeMarketsOverview()));
  });
}

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

async function renderCalendar(path = '/calendar'): Promise<void> {
  renderApp(path);
  await screen.findByRole('heading', { level: 1, name: 'Calendrier' });
  await screen.findByTestId('calendar-grid');
}

const cellule = (id: string) => within(document.querySelector(`[data-module="${id}"]`) as HTMLElement);

describe('Page Calendrier — composition (LOT-A7)', () => {
  it('rend les TREIZE modules de la planche, chacun à sa place', async () => {
    servir();
    await renderCalendar();
    for (const module of CALENDAR_MODULES) {
      expect(document.querySelector(`[data-module="${module.id}"]`), `module ${module.id} absent du DOM`).not.toBeNull();
    }
  });

  it('une seule dominante : l’agenda, qui garde son témoin', async () => {
    servir();
    await renderCalendar();
    await screen.findByTestId('cal-agenda');
    const dominantes = document.querySelectorAll('.vx-main [data-rank="dominant"]');
    expect(dominantes).toHaveLength(1);
    expect(dominantes[0]?.closest('[data-module]')?.getAttribute('data-module')).toBe('agenda');
    expect(dominantes[0]?.querySelector('.vx-cal-agenda')).not.toBeNull();
  });

  it('les deux modules absents portent leur motif fermé, sans chiffre dans le corps', async () => {
    servir();
    await renderCalendar();
    for (const module of absentCalendarModules()) {
      const zone = cellule(module.id);
      expect(zone.getByRole('heading', { level: 3, name: module.title })).toBeDefined();
      expect(zone.getByText(ABSENCE_REASONS[module.status.reason].label)).toBeDefined();
      expect(zone.getByTestId('absent-body').textContent).not.toMatch(/\d/);
    }
  });

  it('le fuseau d’affichage est explicite : UTC, navigateur et fuseaux de place publiés ; `tz` dans l’URL le choisit', async () => {
    servir();
    await renderCalendar('/calendar?tz=UTC');
    const select = (await screen.findByTestId('cal-tz-select')) as HTMLSelectElement;
    expect(select.value).toBe('UTC');
    const options = [...select.options].map((option) => option.value);
    expect(options).toContain('UTC');
    // Le fuseau de place publié par les événements synthétiques est proposé.
    expect(options.some((zone) => zone !== 'UTC')).toBe(true);
    expect(screen.getByTestId('cal-next').textContent).toContain('UTC');
  });

  it('densité et exposition sont des dénombrements par journée UTC ; révisions et conflits, des comptes', async () => {
    servir();
    await renderCalendar();
    expect(await cellule('density').findByRole('list')).toBeDefined();
    expect(cellule('daily-exposure').getByRole('list')).toBeDefined();
    expect(screen.getByTestId('cal-revisions-count')).toBeDefined();
    expect(screen.getByTestId('cal-conflicts')).toBeDefined();
    expect(screen.getByTestId('cal-provenance')).toBeDefined();
    expect(screen.getByTestId('cal-counters')).toBeDefined();
    expect(screen.getByTestId('cal-importance-rule')).toBeDefined();
  });

  it('l’inspecteur porte le snapshot publié ; « Inspecter » ouvre l’événement ; « Fermer » y revient', async () => {
    const user = userEvent.setup();
    servir();
    await renderCalendar();
    expect(await screen.findByTestId('cal-snapshot-facts')).toBeDefined();
    expect(screen.getByRole('heading', { level: 2, name: 'Inspecteur — Snapshot publié' })).toBeDefined();
    const carte = await screen.findByTestId('cal-event-syn-ev-earnings-SYN-ENER-01');
    await user.click(within(carte).getByRole('button', { name: /^Inspecter/ }));
    const faits = await screen.findByTestId('cal-event-facts');
    expect(faits.textContent).toContain('SYN-ENER-01');
    expect(faits.textContent).toContain('non publiés');
    expect(screen.queryByTestId('cal-snapshot-facts')).toBeNull();
    await user.click(screen.getByRole('button', { name: 'Fermer' }));
    await waitFor(() => {
      expect(screen.queryByTestId('cal-event-facts')).toBeNull();
    });
    expect(await screen.findByTestId('cal-snapshot-facts')).toBeDefined();
  });

  it('agenda bloqué par refus de droit : la planche reste composée, la dominante porte le refus', async () => {
    servir(makeNotEntitledCalendarResponse());
    await renderCalendar();
    for (const module of CALENDAR_MODULES) {
      expect(document.querySelector(`[data-module="${module.id}"]`), `module ${module.id} absent du DOM`).not.toBeNull();
    }
    expect(cellule('agenda').getByTestId('cal-blocked')).toBeDefined();
    expect(screen.queryByTestId('cal-agenda')).toBeNull();
    expect(document.querySelectorAll('.vx-main [data-rank="dominant"]')).toHaveLength(1);
  });
});
