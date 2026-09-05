import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ABSENCE_NATURES, AbsentCell, absenceLabel } from './absence.tsx';

describe('absenceLabel — le vocabulaire FERMÉ des absences de valeur', () => {
  it('nomme CE QUI manque, jamais un « non publié » orphelin', () => {
    expect(absenceLabel('input_hash', 'not_published', null)).toBe('input_hash non publié');
  });

  it('accorde en genre : une mesure féminine ne se lit pas au masculin', () => {
    expect(absenceLabel('IV', 'not_computed', null, undefined, 'f')).toBe('IV non calculée');
  });

  it('le code SERVEUR reste verbatim, même quand une traduction existe', () => {
    // Deux assertions e2e/unitaires cherchent le code brut dans le nom
    // accessible (`getAllByLabelText(/crossed_quote/)`). Une traduction qui
    // REMPLACERAIT le code les casserait — et les rattraper en assouplissant
    // la regex serait exactement l'affaiblissement interdit.
    const label = absenceLabel('IV', 'not_computed', 'crossed_quote', 'quote croisée', 'f');
    expect(label).toBe('IV non calculée (quote croisée : crossed_quote)');
    expect(label).toContain('crossed_quote');
  });

  it('sans traduction, le code seul — jamais inventé, jamais tu', () => {
    expect(absenceLabel('IV', 'not_computed', 'crossed_quote', undefined, 'f')).toBe(
      'IV non calculée (crossed_quote)',
    );
  });

  it('le vocabulaire est FERMÉ : cinq natures, et « sans objet » en fait partie', () => {
    // « sans objet » n'est PAS « non publié » : le serveur n'a rien omis, la
    // question ne se pose pas pour cette ligne. Les confondre introduirait un
    // reproche au serveur là où il n'a rien à se reprocher.
    expect(Object.keys(ABSENCE_NATURES).sort()).toEqual(
      ['not_applicable', 'not_computed', 'not_entered', 'not_published', 'not_recognised'].sort(),
    );
  });
});

describe('AbsentCell — le SEUL rendu du dépôt qui a le droit d’écrire « — »', () => {
  it('porte un nom accessible RÉEL : `role="img"`, pas un span muet', () => {
    // `aria-label` sur le rôle implicite `generic` d'un <span> est ignoré par
    // plusieurs technologies d'assistance ; `title` seul ne fournit pas un nom
    // accessible fiable. C'est `role="img"` qui le donne.
    render(<AbsentCell quoi="IV" nature="not_computed" reason="crossed_quote" accord="f" />);
    const cell = screen.getByRole('img');
    expect(cell.getAttribute('aria-label')).toBe('IV non calculée (crossed_quote)');
    expect(cell.getAttribute('title')).toBe('IV non calculée (crossed_quote)');
    expect(cell.textContent).toBe('—');
  });

  it('le motif SERVI est exposé en donnée, pas seulement en texte', () => {
    render(<AbsentCell quoi="IV" nature="not_computed" reason="crossed_quote" accord="f" />);
    const cell = screen.getByRole('img');
    expect(cell.getAttribute('data-absent')).toBe('true');
    expect(cell.getAttribute('data-reason')).toBe('crossed_quote');
  });

  it('REFUS — sans motif servi, aucun attribut de motif n’est inventé', () => {
    render(<AbsentCell quoi="input_hash" nature="not_published" reason={null} />);
    const cell = screen.getByRole('img');
    expect(cell.getAttribute('data-reason')).toBeNull();
    expect(cell.getAttribute('aria-label')).toBe('input_hash non publié');
  });
});
