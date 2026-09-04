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
 * `warning` est ÉLIGIBLE dans les tokens mais N'EST DÉCLARÉ PAR AUCUNE PAGE
 * tant que la réserve 3 de la revue C0 n'est pas tranchée : les valeurs de
 * `warning` et de `signal-bright` (lisibles dans `src/design/tokens.ts`)
 * diffèrent d'au plus 4/255 par canal, et des surfaces pleines de `warning`
 * rendraient « l'ambre est la seule lumière » invérifiable à l'œil. Les trois
 * pages qui l'auraient reçu (Opportunités, Catalyseurs, Sources & Rapports)
 * restent donc sans teinte.
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
