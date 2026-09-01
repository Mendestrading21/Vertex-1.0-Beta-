import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it } from 'vitest';

import { INSPECTOR_SLOT_ID } from '../shell/inspector.tsx';
import { makeAttentionItem } from '../test/fixtures.ts';
import { AttentionQueue, snapshotAgeSeconds } from './AttentionQueue.tsx';

const AS_OF = '2026-08-25T12:00:00+00:00';

/**
 * Le panneau se monte par PORTAIL dans le nœud d'accueil du shell. Un test de
 * composant ne rend pas le shell : il fournit donc ce nœud, exactement comme
 * `AppShell` le fait. Sans lui, `InspectorPanel` ne rend rien — et le test
 * passerait en vérifiant l'absence de ce qu'il veut voir.
 */
function monterAvecInspecteur(): HTMLElement {
  // Le nœud d'accueil est retiré entre les tests : `document.getElementById`
  // renverrait sinon celui d'un test précédent, et le portail viserait un
  // panneau orphelin. Le premier essai de ce harnais avait exactement ce
  // défaut, et l'assertion de focus le révélait.
  document.getElementById(INSPECTOR_SLOT_ID)?.remove();
  const racine = document.createElement('div');
  const accueil = document.createElement('aside');
  accueil.id = INSPECTOR_SLOT_ID;
  document.body.append(racine, accueil);
  return racine;
}

afterEach(() => {
  document.getElementById(INSPECTOR_SLOT_ID)?.remove();
});

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

  it('inspecteur : provenance complète, focus entrant, Échap referme et rend le focus', async () => {
    // LOT-13 : le détail n'est plus un dialogue modal, c'est un panneau de
    // l'inspecteur du shell. Le contenu et les propriétés clavier qui
    // comptaient sont identiques ; ce qui change est asséré au test suivant.
    const user = userEvent.setup();
    const items = [makeAttentionItem(0), makeAttentionItem(1)];
    render(<AttentionQueue items={items} asOf={AS_OF} />, { container: monterAvecInspecteur() });

    const trigger = screen.getAllByRole('button')[0]!;
    await user.click(trigger);

    const panneau = document.querySelector('.vx-inspector-panel');
    expect(panneau).not.toBeNull();
    const panel = panneau as HTMLElement;
    expect(within(panel).getByText('syn-cluster-0')).toBeDefined();
    expect(within(panel).getByText('syn-item-00-event-1')).toBeDefined();
    expect(within(panel).getByText('syn-item-00-event-2')).toBeDefined();
    expect(within(panel).getByText('SYNTHETIC')).toBeDefined(); // droits
    expect(within(panel).getByText('SYN0')).toBeDefined(); // instrument_ref

    // CONSERVÉ : le focus entre dans le panneau à l'ouverture.
    const closeButton = within(panel).getByRole('button', { name: 'Fermer' });
    expect(document.activeElement).toBe(closeButton);

    // CONSERVÉ : Échap referme et restitue le focus au déclencheur.
    await user.keyboard('{Escape}');
    expect(document.querySelector('.vx-inspector-panel')).toBeNull();
    expect(document.activeElement).toBe(trigger);
  });

  it('le panneau n’est PLUS un dialogue modal et ne piège plus le clavier', async () => {
    // Le piège de focus était CORRECT pour un dialogue modal, où le reste de
    // la page est inerte. Sur un panneau non modal il serait un DÉFAUT : il
    // enfermerait l'utilisateur hors de sa propre page. Cette assertion
    // remplace donc l'ancienne, et elle est plus forte — elle prouve que la
    // page reste opérable au clavier.
    const user = userEvent.setup();
    render(<AttentionQueue items={[makeAttentionItem(0), makeAttentionItem(1)]} asOf={AS_OF} />, {
      container: monterAvecInspecteur(),
    });

    await user.click(screen.getAllByRole('button')[0]!);
    const panel = document.querySelector('.vx-inspector-panel') as HTMLElement;
    expect(panel).not.toBeNull();

    // Ni rôle de dialogue, ni modalité déclarée.
    expect(document.querySelector('[role="dialog"]')).toBeNull();
    expect(document.querySelector('[aria-modal]')).toBeNull();

    // Depuis le dernier élément focusable du panneau, la tabulation SORT vers
    // le reste de la page — elle ne reboucle pas dans le panneau.
    const focusables = Array.from(
      panel.querySelectorAll<HTMLElement>('button, a[href], [tabindex]:not([tabindex="-1"])'),
    );
    expect(focusables.length).toBeGreaterThan(0);
    focusables[focusables.length - 1]!.focus();
    await user.tab();
    expect(panel.contains(document.activeElement)).toBe(false);
  });

  it('état vide : aucune ligne fabriquée', () => {
    render(<AttentionQueue items={[]} asOf={null} />);
    expect(screen.queryAllByRole('listitem')).toHaveLength(0);
  });
});
