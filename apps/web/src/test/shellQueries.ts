/**
 * Aides de test pour les requêtes que fait LE SHELL, et pas la page.
 *
 * Depuis le LOT-14, le shell interroge `/api/v1/markets/overview` sur TOUTES
 * les destinations : c'est le ticker horizontal, point 4 de l'anatomie
 * canonique. Deux conséquences pour les tests de page qui posent un `fetch`
 * global, et ce fichier existe pour les rendre explicites plutôt que
 * mystérieuses :
 *
 * 1. une réponse UNIQUE programmée par la page est consommée par le ticker,
 *    qui part le premier. La page n'obtient alors rien, ou pire un corps de
 *    `Response` déjà lu. `withShellTicker` route par chemin : le ticker reçoit
 *    son instantané, la page reçoit le sien ;
 * 2. « aucune requête n'a été envoyée » n'est plus l'invariant testable. Il ne
 *    l'a jamais été vraiment : ce que ces tests protègent, c'est qu'AUCUNE
 *    requête MÉTIER ne part (aucune prévisualisation, aucun ordre d'analyse).
 *    `calledPaths` permet de l'asserter sur la route concernée — une propriété
 *    plus précise que le compte global, pas une plus faible.
 */
import type { MarketsOverview } from '../api/client.ts';
import { makeMarketsOverview } from './fixtures.ts';

/** Chemin interrogé par le ticker du shell sur chaque destination. */
export const SHELL_TICKER_PATH = '/api/v1/markets/overview';

function pathOf(input: RequestInfo | URL): string {
  if (typeof input === 'string') {
    return input;
  }
  if (input instanceof URL) {
    return input.pathname;
  }
  return input.url;
}

/** Chemins effectivement demandés, dans l'ordre d'appel. */
export function calledPaths(calls: readonly (readonly unknown[])[]): string[] {
  return calls.map((call) => pathOf(call[0] as RequestInfo | URL));
}

/**
 * Enveloppe un répondeur de page : la route du ticker reçoit un instantané
 * valide, tout le reste va au répondeur. Chaque appel fabrique une `Response`
 * NEUVE — un corps ne se lit qu'une fois, et le partager entre deux requêtes
 * en vide une des deux.
 */
export function withShellTicker(
  respond: (input: RequestInfo | URL, init?: RequestInit) => Response | Promise<Response>,
  overview: MarketsOverview = makeMarketsOverview(),
): (input: RequestInfo | URL, init?: RequestInit) => Promise<Response> {
  return async (input, init) => {
    if (pathOf(input).includes(SHELL_TICKER_PATH)) {
      return new Response(JSON.stringify(overview), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }
    return respond(input, init);
  };
}
