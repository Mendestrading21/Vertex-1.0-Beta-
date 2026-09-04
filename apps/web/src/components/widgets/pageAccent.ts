import type { PageAccentToken } from '../../design/tokens.ts';

/**
 * TEINTE SÉMANTIQUE SECONDAIRE PAR PAGE — ADR-017.
 *
 * UNE famille par page, choisie parmi le vocabulaire typé `pageAccent`
 * (`src/design/tokens.ts`), jamais un hex. L'ambre (`signal`) reste la seule
 * lumière de la dominante ; `positive` et `negative` restent réservés au SIGNE
 * financier servi et ne sont donc pas éligibles.
 *
 * POURQUOI CETTE TABLE EXISTE AVANT LE PREMIER CONSOMMATEUR. `--vx-page-accent`
 * n'a AUCUNE valeur par défaut dans `:root` (par construction, `generate-css.ts`) :
 * une page qui poserait `data-page-accent` sans déclaration rendrait la
 * variable invalide à la valeur calculée, et un `fill` SVG retomberait
 * silencieusement sur sa valeur initiale — le noir, explicitement interdit.
 * La porte `catalog.test.ts` précède donc toute primitive qui consomme la
 * teinte (ADR-017, « Preuves d'application », réserve 5 de la revue C0).
 *
 * `null` = la page n'a PAS de teinte secondaire. C'est une décision, pas un
 * oubli : les douze destinations figurent toutes ici.
 *
 * `warning` est ÉLIGIBLE dans les tokens et le RESTE : la réserve 3 de la revue
 * C0 a été tranchée au lot V2. `warning` et `signal-bright` ne diffèrent plus
 * d'au plus 4/255 par canal — la prudence a quitté l'ambre de marque pour une
 * orange franche, mesurée à ΔE 26,9 de `signal`. La porte de `catalog.test.ts`
 * ne l'interdit donc plus ; elle mesure l'écart et se RÉARME d'elle-même si
 * quelqu'un ramenait un jour les deux jetons l'un vers l'autre.
 *
 * Les trois pages qui l'auraient reçu — Opportunités, Catalyseurs, Sources &
 * Rapports — restent néanmoins SANS TEINTE aujourd'hui. C'est une décision
 * distincte : donner une teinte à une page relève de son propre lot de refonte,
 * qui compose sa planche et sait ce que la couleur doit y signifier. Lever un
 * blocage n'est pas une raison de peindre.
 */
export const PAGE_ACCENTS: Readonly<Record<string, PageAccentToken | null>> = {
  // `macro` = contexte : la page décrit un environnement, jamais un verdict.
  markets: 'macro',
  charts: 'macro',
  risks: 'macro',
  // `option` = domaine des options, la seule page qui a le droit de le porter,
  // plus le simulateur qui ne travaille que sur des structures d'options.
  options: 'option',
  simulator: 'option',
  // Sans teinte secondaire : la dominante suffit, et rien ne justifierait une
  // seconde famille sur ces planches.
  today: null,
  analysis: null,
  portfolio: null,
  calendar: null,
  // Réserve 3 de la revue C0 (voir ci-dessus) : `warning` suspendu.
  opportunities: null,
  catalysts: null,
  'sources-reports': null,
};

/**
 * Attributs à poser sur le `<article className="vx-page">` d'une destination.
 *
 * POURQUOI UN HELPER PLUTÔT QU'UN ATTRIBUT ÉCRIT À LA MAIN. Avant le lot P3a,
 * la table déclarait cinq teintes et UNE SEULE page posait l'attribut — et
 * elle l'écrivait en dur (`data-page-accent="macro"`), donc sans lien avec la
 * table. Une déclaration que personne ne lit n'est pas une décision, c'est un
 * commentaire. Le catalogue redevient le propriétaire unique.
 *
 * Une page sans teinte ne pose RIEN : `--vx-page-accent` n'a aucune valeur par
 * défaut, et un attribut posé à vide rendrait la variable invalide à la valeur
 * calculée.
 */
export function pageAccentAttrs(page: string): Record<string, string> {
  const famille = PAGE_ACCENTS[page];
  return famille === null || famille === undefined ? {} : { 'data-page-accent': famille };
}
