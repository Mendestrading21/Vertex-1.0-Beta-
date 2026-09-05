import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { GLYPH_NAMES, Glyph } from './Glyph.tsx';

describe('Glyph — le catalogue SVG approuvé, et rien d’autre', () => {
  it('le vocabulaire est FERMÉ et couvre les vingt et une icônes du catalogue', () => {
    // La liste est celle de `design-assets/icons/custom/`. L'y ajouter une
    // entrée sans le fichier casse la compilation ; l'inverse laisse une icône
    // inatteignable — ce compte le dit.
    expect(GLYPH_NAMES).toHaveLength(21);
    expect(new Set(GLYPH_NAMES).size).toBe(GLYPH_NAMES.length);
    expect(GLYPH_NAMES).toContain('attention-queue');
    expect(GLYPH_NAMES).toContain('volatility-smile');
  });

  it('l’icône est DÉCORATIVE : masque en `currentColor`, jamais un nom accessible', () => {
    render(<Glyph name="market-regime" />);
    const glyph = screen.getByTestId('glyph');
    expect(glyph.getAttribute('aria-hidden')).toBe('true');
    expect(glyph.textContent).toBe('');
    // La couleur vient du parent : aucune teinte financière n'est encodée ici.
    expect(glyph.style.backgroundColor).toBe('currentcolor');
  });

  it('chaque nom du catalogue résout une URL de masque (aucune case vide)', () => {
    for (const name of GLYPH_NAMES) {
      render(<Glyph name={name} />);
    }
    const glyphs = screen.getAllByTestId('glyph');
    expect(glyphs).toHaveLength(GLYPH_NAMES.length);
    for (const glyph of glyphs) {
      expect(glyph.style.mask === '' && glyph.style.webkitMask === '').toBe(false);
    }
  });
});
