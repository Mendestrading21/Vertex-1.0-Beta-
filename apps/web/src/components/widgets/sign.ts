/**
 * AUTORITÉ UNIQUE DU SIGNE AFFICHÉ.
 *
 * Le signe n'est pas une décoration : c'est une AFFIRMATION FINANCIÈRE. Peindre
 * un P&L en vert dit « vous gagnez ». Le dire d'un `0.00` servi, c'est
 * fabriquer un gain — précisément ce que `.claude/rules/frontend.md` interdit
 * quand il exige que « valeur absente, zéro, [et] donnée réelle » restent
 * distincts.
 *
 * QUATRE RÈGLES CONCURRENTES COEXISTAIENT :
 *
 * 1. `signGroupOf` (`marketsView.ts`) — correcte, mais elle prend un
 *    `MarketsTicker` : inutilisable sur toute autre chaîne servie ;
 * 2. `signGroupOfText` (`KpiDelta.tsx`) — correcte, et c'est celle-ci qui est
 *    promue ici ; elle vivait dans un fichier de composant, où personne
 *    n'allait la chercher ;
 * 3. `signOf` (Portefeuille et Simulateur, deux copies) — testait `'-'` AVANT
 *    le zéro, donc un `-0.00` servi devenait une PERTE ;
 * 4. `startsWith('-') ? 'negative' : 'positive'` (table et inspecteur de
 *    Portefeuille, drawdown de Risques) — binaire, sans état neutre : un P&L
 *    latent servi `0.00` était peint EN VERT, et un vocabulaire
 *    `positive`/`negative` étranger au `up`/`down`/`flat`/`unknown` du reste du
 *    produit rendait la faute invisible aux feuilles de style partagées.
 *
 * CE QUE LA RÈGLE REFUSE DE TRANCHER. Une chaîne positive publiée SANS « + »
 * n'est pas « stable » : son signe n'est simplement pas publié. La classer
 * `flat` inventerait une stabilité, la classer `up` inventerait un gain. Elle
 * rend `null`, et l'appelant n'applique alors AUCUNE couleur de sens.
 */
import type { SignGroup } from '../markets/marketsView.ts';

/** Zéro servi, signé ou non, avec ou sans décimales, avec ou sans « % ». */
const ZERO = /^[+-]?0+([.,]0+)?\s*%?$/;
const SIGNED = /^([+-])/;

/**
 * Sens d'une chaîne SERVIE — ou `null` quand le signe n'est pas publié.
 *
 * L'ORDRE DES TESTS EST LA CORRECTION : le zéro est reconnu AVANT le signe,
 * sans quoi `-0.00` — un zéro que le serveur a signé — se lirait comme une
 * perte.
 */
export function signGroupOfText(value: string): SignGroup | null {
  const trimmed = value.trim();
  if (trimmed === '') {
    return null;
  }
  if (ZERO.test(trimmed)) {
    return 'flat';
  }
  const signe = SIGNED.exec(trimmed)?.[1];
  if (signe === '+') {
    return 'up';
  }
  if (signe === '-') {
    return 'down';
  }
  return null;
}

/** La même règle, tolérante à l'absence : `null` entre, `null` sort. */
export function signGroupOfServed(value: string | null | undefined): SignGroup | null {
  return value === null || value === undefined ? null : signGroupOfText(value);
}
