import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ServedNumber } from './ServedNumber.tsx';

describe('ServedNumber — borné au rendu, jamais arrondi', () => {
  it('rend la chaîne SERVIE telle quelle', () => {
    render(<ServedNumber value="4.413571428571428" />);
    // Aucune troncature dans le DOM : c'est le rendu qui borne, pas le texte.
    expect(screen.getByTitle('4.413571428571428').textContent).toBe('4.413571428571428');
  });

  it('porte TOUJOURS la valeur entière en recours, même courte', () => {
    // Faire dépendre le recours de la largeur rendue le ferait dépendre de la
    // taille de la fenêtre — donc de rien de fiable.
    render(<ServedNumber value="12" />);
    expect(screen.getByTitle('12')).toBeDefined();
  });

  it('n’est jamais une cellule de tableau', () => {
    // `inline-block` retire à un `<td>` son display tabulaire : le navigateur
    // enveloppe alors ses voisines dans des boîtes anonymes, et l'en-tête ne
    // tombe plus en face du corps. Le composant rend un `<code>`, point.
    const { container } = render(<ServedNumber value="1" />);
    expect(container.firstElementChild?.tagName).toBe('CODE');
  });

  it('accepte un plafond explicite, exprimé en caractères', () => {
    const { container } = render(<ServedNumber value="0.1848147947607191" maxChars={8} />);
    expect((container.firstElementChild as HTMLElement).style.maxWidth).toBe('8ch');
  });
});
