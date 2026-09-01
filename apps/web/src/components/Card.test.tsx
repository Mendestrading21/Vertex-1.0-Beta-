/**
 * `Card` — la primitive unique des douze destinations.
 *
 * Ces tests protègent l'ANATOMIE, pas l'apparence : kicker, titre, corps, pied
 * de provenance, et le rang qui décide de la lumière. Une page choisit un
 * rang ; elle ne choisit jamais une apparence.
 */
import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { Card } from './Card.tsx';

describe('Card — une anatomie, trois rangs', () => {
  it('rend kicker, titre et corps dans cet ordre', () => {
    const { container } = render(
      <Card kicker="Priorité publiée" title="File d’attention">
        <p>corps</p>
      </Card>,
    );
    expect(screen.getByText('Priorité publiée')).toBeDefined();
    expect(screen.getByRole('heading', { name: 'File d’attention' })).toBeDefined();
    expect(screen.getByText('corps')).toBeDefined();
    const carte = container.querySelector('.vx-card');
    expect(carte).not.toBeNull();
    // L'ordre du DOM est l'ordre de lecture : la nature du module se lit avant
    // son contenu, y compris au lecteur d'écran.
    const classes = Array.from(carte!.children).map((n) => n.className);
    expect(classes).toEqual(['vx-card-head', 'vx-card-body']);
  });

  it('le pied de provenance est rendu APRÈS le corps, jamais avant', () => {
    // « Microcopie et provenance proches de la donnée ». Une provenance lue
    // avant la valeur ne qualifie rien : elle annonce.
    const { container } = render(
      <Card title="T" footer={<>source · as_of</>}>
        <p>corps</p>
      </Card>,
    );
    const classes = Array.from(container.querySelector('.vx-card')!.children).map(
      (n) => n.className,
    );
    expect(classes).toEqual(['vx-card-head', 'vx-card-body', 'vx-card-foot']);
  });

  it('le rang est porté par un attribut, jamais par une classe d’apparence', () => {
    const { container, rerender } = render(<Card title="T">c</Card>);
    expect(container.querySelector('.vx-card')?.getAttribute('data-rank')).toBe('default');
    rerender(
      <Card title="T" rank="dominant">
        c
      </Card>,
    );
    expect(container.querySelector('.vx-card')?.getAttribute('data-rank')).toBe('dominant');
    rerender(
      <Card title="T" rank="quiet">
        c
      </Card>,
    );
    expect(container.querySelector('.vx-card')?.getAttribute('data-rank')).toBe('quiet');
  });

  it('la classe fournie par la page S’AJOUTE et ne remplace jamais `vx-card`', () => {
    // Le piège exact que la primitive existe pour fermer : une page qui
    // écraserait la classe reprendrait la main sur l'apparence, et l'écart
    // reviendrait module par module.
    const { container } = render(
      <Card title="T" className="vx-today-queue">
        c
      </Card>,
    );
    const carte = container.querySelector('section');
    expect(carte?.className).toBe('vx-card vx-today-queue');
  });

  it('le titre est adressable pour `aria-labelledby`', () => {
    const { container } = render(
      <Card title="Instantané publié" titleId="vx-t">
        c
      </Card>,
    );
    const carte = container.querySelector('.vx-card');
    expect(carte?.getAttribute('aria-labelledby')).toBe('vx-t');
    expect(within(carte as HTMLElement).getByRole('heading').getAttribute('id')).toBe('vx-t');
  });

  it('sans titre adressable, aucun `aria-labelledby` fantôme', () => {
    // Un `aria-labelledby` pointant sur un identifiant inexistant est une
    // violation d'accessibilité silencieuse : la région perd son nom.
    const { container } = render(<Card title="T">c</Card>);
    expect(container.querySelector('.vx-card')?.hasAttribute('aria-labelledby')).toBe(false);
  });
});
