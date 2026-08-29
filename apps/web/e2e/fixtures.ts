/**
 * Fixtures E2E : contexte authentifié par les cookies de session réels créés
 * pendant global.setup.ts (transmis via process.env, jamais via un fichier).
 * L'axe helper filtre les violations critiques/sérieuses (seuil : zéro).
 */
import AxeBuilder from '@axe-core/playwright';
import { test as base, expect } from '@playwright/test';
import type { Page } from '@playwright/test';

export const test = base.extend({
  context: async ({ context }, use) => {
    const raw = process.env['VX_E2E_COOKIES'];
    if (raw === undefined) {
      throw new Error('VX_E2E_COOKIES absent : global.setup.ts n’a pas abouti.');
    }
    await context.addCookies(JSON.parse(raw) as Parameters<typeof context.addCookies>[0]);
    await use(context);
  },
});

export { expect };

export async function expectNoSeriousAxeViolations(page: Page): Promise<void> {
  const results = await new AxeBuilder({ page }).analyze();
  const blocking = results.violations.filter(
    (violation) => violation.impact === 'critical' || violation.impact === 'serious',
  );
  expect(
    blocking,
    `Violations axe critiques/sérieuses : ${JSON.stringify(
      blocking.map((violation) => ({
        id: violation.id,
        impact: violation.impact,
        nodes: violation.nodes.length,
      })),
    )}`,
  ).toEqual([]);
}

export function screenshotPath(name: string, projectName: string): string {
  return `e2e-artifacts/${name}-${projectName}.png`;
}
