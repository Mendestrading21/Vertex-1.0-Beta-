import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { makeAttentionItem } from '../test/fixtures.ts';
import { AttentionQueue, snapshotAgeSeconds } from './AttentionQueue.tsx';

const AS_OF = '2026-08-25T12:00:00+00:00';

describe('snapshotAgeSeconds — différence de deux horodatages SERVEUR', () => {
  it('calcule la durée entre as_of et first_published_at', () => {
    expect(snapshotAgeSeconds(AS_OF, '2026-08-25T11:30:00+00:00')).toBe(1800);
  });

  it("l'absence reste une absence : null, jamais zéro", () => {
    expect(snapshotAgeSeconds(null, '2026-08-25T11:30:00+00:00')).toBeNull();
    expect(snapshotAgeSeconds(AS_OF, null)).toBeNull();
    expect(snapshotAgeSeconds(AS_OF, 'pas-une-date')).toBeNull();
  });
});

describe('AttentionQueue', () => {
  it('rend exactement les items reçus (15 max côté serveur) dans une liste', () => {
    const items = Array.from({ length: 15 }, (_, index) => makeAttentionItem(index));
    render(<AttentionQueue items={items} asOf={AS_OF} />);
    const list = screen.getByRole('list');
    expect(within(list).getAllByRole('listitem')).toHaveLength(15);
  });

  it('au plus 3 raisons de pertinence en badges texte par ligne', () => {
    const item = makeAttentionItem(0, {
      relevance_reasons: ['R1', 'R2', 'R3'],
    });
    render(<AttentionQueue items={[item]} asOf={AS_OF} />);
    const row = screen.getByRole('listitem');
    expect(within(row).getByText('R1')).toBeDefined();
    expect(within(row).getByText('R2')).toBeDefined();
    expect(within(row).getByText('R3')).toBeDefined();
    expect(row.querySelectorAll('.vx-badge-reason')).toHaveLength(3);
  });

  it('marqueur SYNTHÉTIQUE visible sur chaque item synthétique, absent sinon', () => {
    const synthetic = makeAttentionItem(0);
    const real = makeAttentionItem(1, { synthetic: false });
    render(<AttentionQueue items={[synthetic, real]} asOf={AS_OF} />);
    const rows = screen.getAllByRole('listitem');
    expect(within(rows[0]!).getByText('SYNTHÉTIQUE')).toBeDefined();
    expect(within(rows[1]!).queryByText('SYNTHÉTIQUE')).toBeNull();
  });

  it("l'âge affiché vient des horodatages serveur (as_of − first_published_at)", () => {
    const item = makeAttentionItem(0); // first_published_at à 11:30, as_of à 12:00
    render(<AttentionQueue items={[item]} asOf={AS_OF} />);
    expect(screen.getByText('il y a 30 min')).toBeDefined();
  });

  it('panneau latéral : provenance complète, focus piégé, Échap referme et rend le focus', async () => {
    const user = userEvent.setup();
    const items = [makeAttentionItem(0), makeAttentionItem(1)];
    render(<AttentionQueue items={items} asOf={AS_OF} />);

    const trigger = screen.getAllByRole('button')[0]!;
    await user.click(trigger);

    const dialog = screen.getByRole('dialog');
    expect(dialog.getAttribute('aria-modal')).toBe('true');
    expect(within(dialog).getByText('syn-cluster-0')).toBeDefined();
    expect(within(dialog).getByText('syn-item-00-event-1')).toBeDefined();
    expect(within(dialog).getByText('syn-item-00-event-2')).toBeDefined();
    expect(within(dialog).getByText('SYNTHETIC')).toBeDefined(); // droits
    expect(within(dialog).getByText('SYN0')).toBeDefined(); // instrument_ref

    // Le focus initial est dans le panneau (bouton Fermer).
    const closeButton = within(dialog).getByRole('button', { name: 'Fermer' });
    expect(document.activeElement).toBe(closeButton);

    // Piège de focus : Tab depuis le dernier élément focusable revient au premier.
    await user.tab();
    expect(dialog.contains(document.activeElement)).toBe(true);

    // Échap referme et restitue le focus au déclencheur.
    await user.keyboard('{Escape}');
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(document.activeElement).toBe(trigger);
  });

  it('état vide : aucune ligne fabriquée', () => {
    render(<AttentionQueue items={[]} asOf={null} />);
    expect(screen.queryAllByRole('listitem')).toHaveLength(0);
  });
});
