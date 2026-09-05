import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { ActivityFeed } from './ActivityFeed.tsx';
import type { FeedGroup } from './ActivityFeed.tsx';

const GROUPS: readonly FeedGroup[] = [
  {
    dayIso: '2026-09-03',
    dayLabel: 'mercredi 3 septembre 2026 (Europe/Zurich)',
    items: [
      {
        id: 'a',
        timeIso: '2026-09-03T08:40:00Z',
        timeLabel: '10:40 Europe/Zurich',
        title: 'Dépêche relayée',
        amount: '+1250.00 USD',
        sign: 'up' as const,
      },
      {
        id: 'b',
        timeIso: '2026-09-03T07:10:00Z',
        timeLabel: '09:10 Europe/Zurich',
        title: 'Fait de position déclaré',
        amount: null,
      },
    ],
  },
];

function renderFeed(groups = GROUPS) {
  return render(
    <MemoryRouter>
      <ActivityFeed groups={groups} ariaLabel="Journal" />
    </MemoryRouter>,
  );
}

describe('ActivityFeed — journal groupé par jour SERVI', () => {
  it('un groupe par jour, dans l’ordre SERVI, avec <time dateTime>', () => {
    const { container } = renderFeed();
    const jours = container.querySelectorAll('.vx-w2-feed-day');
    expect(jours).toHaveLength(1);
    const tetes = container.querySelectorAll('.vx-w2-feed-day-head time');
    expect(tetes[0]?.getAttribute('dateTime')).toBe('2026-09-03');
    expect(container.querySelectorAll('.vx-w2-feed-item')).toHaveLength(2);
    expect(container.querySelectorAll('.vx-w2-feed-time time')[0]?.getAttribute('dateTime')).toBe(
      '2026-09-03T08:40:00Z',
    );
  });

  it('le libellé de jour SERVI est rendu verbatim, fuseau compris', () => {
    renderFeed();
    expect(screen.getByText(/mercredi 3 septembre 2026 \(Europe\/Zurich\)/)).toBeDefined();
  });

  it('un libellé RELATIF est refusé : aucune horloge navigateur ne le justifie', () => {
    renderFeed([{ ...GROUPS[0]!, dayLabel: "Aujourd'hui" }]);
    expect(screen.queryByText(/Aujourd’hui|Aujourd'hui/)).toBeNull();
    // Repli sur la date ISO servie, et le refus est DIT.
    expect(screen.getByText('2026-09-03')).toBeDefined();
    expect(screen.getByText(/libellé relatif refusé/)).toBeDefined();
  });

  it('le montant servi garde son signe dans le TEXTE, la couleur ne dit jamais seule', () => {
    const { container } = renderFeed();
    const montant = container.querySelector('.vx-w2-feed-amount') as HTMLElement;
    expect(montant.getAttribute('data-sign')).toBe('up');
    expect(montant.textContent).toContain('+1250.00 USD');
    expect(montant.textContent).toContain('▲');
  });

  it('un montant absent est DIT « montant non publié », jamais 0', () => {
    const { container } = renderFeed();
    const montants = container.querySelectorAll('.vx-w2-feed-amount');
    expect(montants[1]?.textContent).toContain('montant non publié');
    expect(montants[1]?.getAttribute('data-sign')).toBe('unknown');
  });

  it('aucun groupe : l’absence est DITE', () => {
    renderFeed([]);
    expect(screen.getByRole('status').textContent).toContain('Aucun événement publié');
  });

  it('un lien d’item pointe vers la route servie', () => {
    renderFeed([
      {
        ...GROUPS[0]!,
        items: [{ ...GROUPS[0]!.items[0]!, to: '/analysis/AEHL' }],
      },
    ]);
    expect(screen.getByRole('link', { name: /Dépêche relayée/ }).getAttribute('href')).toBe(
      '/analysis/AEHL',
    );
  });
});
