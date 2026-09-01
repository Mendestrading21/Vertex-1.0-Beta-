/**
 * Redirections permanentes des destinations ABSORBÉES.
 *
 * Règle 5 de `docs/05-design/PAGE_ARBITRATION.md` : une route retirée est
 * remplacée par une redirection permanente, jamais par un 404. Sans ces
 * tests, un signet ou un lien profond existant casserait en silence.
 *
 * `routes.test.tsx` prouve la même chose sur le routeur mémoire ; ici c'est
 * le vrai navigateur, avec l'historique réel — le `replace` n'est
 * observable que là.
 */
import { expect, test } from './fixtures.ts';

const REDIRECTIONS = [
  { depuis: '/system', vers: '/sources-reports', titre: 'Sources & Rapports' },
  { depuis: '/performance', vers: '/portfolio', titre: 'Portefeuille' },
  { depuis: '/follow-up', vers: '/catalysts', titre: 'Catalyseurs' },
] as const;

test.describe('Destinations absorbées — redirections permanentes', () => {
  for (const { depuis, vers, titre } of REDIRECTIONS) {
    test(`${depuis} mène à ${vers} sans laisser d\u2019entrée d\u2019historique`, async ({
      page,
    }) => {
      await page.goto('/today');
      await page.goto(depuis);
      await expect(page).toHaveURL(new RegExp(`${vers}$`));
      await expect(page.getByRole('heading', { level: 1, name: titre })).toBeVisible();

      // `replace` : revenir en arrière depuis la destination absorbée doit
      // ramener à la page précédente, jamais reboucler sur l'ancienne route.
      await page.goBack();
      await expect(page).toHaveURL(/\/today$/);
    });
  }

  test('aucune ancienne route ne tombe sur la page introuvable', async ({ page }) => {
    for (const { depuis } of REDIRECTIONS) {
      await page.goto(depuis);
      await expect(page.getByRole('heading', { level: 1, name: 'Page introuvable' })).toHaveCount(
        0,
      );
    }
  });
});
