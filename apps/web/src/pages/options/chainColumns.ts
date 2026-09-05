import type { OptionChainContract } from '../../api/client.ts';
import { IV_ABSENT_REASONS_FR, blockString, deltaOf, quoteViewOf } from './optionsView.ts';

/**
 * VOCABULAIRE DE COLONNES DE LA CHAÎNE — ce que le SERVEUR publie, et rien d'autre.
 *
 * POURQUOI CE FICHIER EXISTE. La chaîne rendait quatre colonnes par côté — bid,
 * ask, IV, delta — alors que le contrat en publie DOUZE. `bid_size`, `ask_size`,
 * `volume`, `open_interest` et six sensibilités voyageaient jusqu'au navigateur
 * et étaient jetées. Un desk d'options se lit sur la liquidité autant que sur le
 * prix : une chaîne sans taille de carnet ni open interest ne dit pas si le
 * strike est négociable.
 *
 * CE QUE LE CONTRAT NE PUBLIE PAS, ET QUI NE SERA DONC PAS AFFICHÉ.
 *
 *   - SPREAD. Aucun champ `spread` n'existe. Le calculer ici — `ask` moins
 *     `bid` — serait un calcul financier dans le navigateur : la Constitution
 *     l'interdit (article 8) et la porte `no-authoritative-calculation` le
 *     refuse. Un spread affiché ne peut venir que du worker.
 *   - LAST. Le worker ne relaie que `bid` et `ask` (`options.py:442-443`).
 *     Il n'y a pas de dernier échangé.
 *   - MID. Même raison que le spread : c'est une moyenne, donc un calcul.
 *   - MONEYNESS / ATM. Aucun champ ne classe un strike comme « à la monnaie ».
 *     Ranger un strike dans cette catégorie est un JUGEMENT, et il appartient
 *     au moteur. Ce que la table peut montrer honnêtement, c'est le SPOT SERVI
 *     à sa place dans l'échelle des strikes — une valeur publiée, positionnée
 *     sur un axe publié.
 *
 * Ces absences ne sont pas des oublis : ce sont des champs à gagner côté
 * serveur. Elles sont énumérées dans `COLONNES_NON_SERVIES` pour que
 * l'interface puisse le DIRE plutôt que de laisser croire à un manque de place.
 */

/** Une colonne de côté (CALL ou PUT). Chaque valeur est lue verbatim. */
export interface ChainColumn {
  readonly key: string;
  /** En-tête court. */
  readonly label: string;
  /** Unité ou nature, rendue sous l'en-tête. Jamais dans un seul infobulle. */
  readonly unit: string;
  /** Ce que la colonne répond, pour l'infobulle de définition. */
  readonly definition: string;
  /**
   * Valeur SERVIE, verbatim, ou `null`. Aucune fonction de cette table ne
   * calcule : elles lisent un champ et le rendent tel quel.
   */
  readonly read: (contract: OptionChainContract) => string | null;
  /** Motif d'absence SERVI, quand `read` rend `null` et que la cause est publiée. */
  readonly absentReason?: (contract: OptionChainContract) => string | null;
  /**
   * Traduction française du motif typé, quand elle existe.
   *
   * ELLE N'EST PAS DÉCORATIVE. Le code serveur (`crossed_quote`) reste affiché
   * verbatim — c'est lui qui fait foi — mais un lecteur qui ne connaît pas le
   * vocabulaire du worker ne saurait pas ce qu'il désigne. Le nom accessible
   * porte donc les deux : la phrase et le code. Une première version générique
   * de la cellule avait perdu cette traduction, et un test l'a rattrapée.
   */
  readonly explain?: (reason: string | null) => string | undefined;
  /** Groupe d'affichage, pour ranger le sélecteur de colonnes. */
  readonly group: 'cotation' | 'liquidité' | 'sensibilité';
}

const entier = (valeur: number | null): string | null => (valeur === null ? null : String(valeur));

export const CHAIN_COLUMNS: readonly ChainColumn[] = [
  {
    key: 'bid',
    label: 'Bid',
    unit: 'prime',
    definition: 'Meilleur cours demandé publié, côté demande. Cotation observée, jamais une intention.',
    group: 'cotation',
    read: (c) => quoteViewOf(c).bid,
    absentReason: (c) => quoteViewOf(c).status,
  },
  {
    key: 'ask',
    label: 'Ask',
    unit: 'prime',
    definition: 'Meilleur cours proposé publié, côté offre. Cotation observée, jamais une intention.',
    group: 'cotation',
    read: (c) => quoteViewOf(c).ask,
    absentReason: (c) => quoteViewOf(c).status,
  },
  {
    key: 'bid_size',
    label: 'Taille bid',
    unit: 'contrats',
    definition: 'Profondeur publiée du côté demande. Dit si le strike est réellement traité.',
    group: 'liquidité',
    read: (c) => entier(quoteViewOf(c).bidSize),
    absentReason: (c) => quoteViewOf(c).status,
  },
  {
    key: 'ask_size',
    label: 'Taille ask',
    unit: 'contrats',
    definition: 'Profondeur publiée du côté offre.',
    group: 'liquidité',
    read: (c) => entier(quoteViewOf(c).askSize),
    absentReason: (c) => quoteViewOf(c).status,
  },
  {
    key: 'volume',
    label: 'Volume',
    unit: 'contrats',
    definition: 'Volume publié sur la séance. Servi par le contrat et jamais affiché jusqu’ici.',
    group: 'liquidité',
    read: (c) => entier(c.volume),
  },
  {
    key: 'open_interest',
    label: 'Open interest',
    unit: 'contrats',
    definition: 'Positions ouvertes publiées. Son STATUT est servi séparément et affiché avec elle.',
    group: 'liquidité',
    read: (c) => entier(c.open_interest),
    absentReason: (c) => c.open_interest_status,
  },
  {
    key: 'iv',
    label: 'IV',
    unit: 'théorique',
    definition: 'Volatilité implicite calculée par le worker. Absente si la cotation a été refusée.',
    group: 'sensibilité',
    read: (c) => blockString(c.iv, 'value'),
    absentReason: (c) => blockString(c.iv, 'reason'),
    explain: (reason) => (reason === null ? undefined : IV_ABSENT_REASONS_FR[reason]),
  },
  {
    key: 'delta',
    label: 'Delta',
    unit: '/ spot',
    definition: 'Variation de prime par unité de sous-jacent. Calculé par le worker.',
    group: 'sensibilité',
    read: (c) => deltaOf(c),
    absentReason: (c) => blockString(c.greeks, 'reason'),
    explain: (reason) => (reason === null ? undefined : IV_ABSENT_REASONS_FR[reason]),
  },
  {
    key: 'gamma',
    label: 'Gamma',
    unit: '/ spot',
    definition: 'Variation de delta par unité de sous-jacent.',
    group: 'sensibilité',
    read: (c) => blockString(c.greeks, 'gamma'),
    absentReason: (c) => blockString(c.greeks, 'reason'),
    explain: (reason) => (reason === null ? undefined : IV_ABSENT_REASONS_FR[reason]),
  },
  {
    key: 'vega',
    label: 'Vega',
    unit: '/ point vol.',
    definition: 'Sensibilité à la volatilité, exprimée par point de volatilité entier.',
    group: 'sensibilité',
    read: (c) => blockString(c.greeks, 'vega'),
    absentReason: (c) => blockString(c.greeks, 'reason'),
    explain: (reason) => (reason === null ? undefined : IV_ABSENT_REASONS_FR[reason]),
  },
  {
    key: 'theta_per_calendar_day',
    label: 'Theta / jour',
    unit: '/ jour',
    definition: 'Érosion par jour calendaire. Le worker publie aussi le theta annuel.',
    group: 'sensibilité',
    read: (c) => blockString(c.greeks, 'theta_per_calendar_day'),
    absentReason: (c) => blockString(c.greeks, 'reason'),
    explain: (reason) => (reason === null ? undefined : IV_ABSENT_REASONS_FR[reason]),
  },
  {
    key: 'rho_per_bp',
    label: 'Rho / bp',
    unit: '/ bp',
    definition: 'Sensibilité au taux, par point de base.',
    group: 'sensibilité',
    read: (c) => blockString(c.greeks, 'rho_per_bp'),
    absentReason: (c) => blockString(c.greeks, 'reason'),
    explain: (reason) => (reason === null ? undefined : IV_ABSENT_REASONS_FR[reason]),
  },
];

/**
 * Sélection par défaut : ce qu'un analyste lit en premier sur un desk.
 *
 * Elle n'est PAS « toutes les colonnes ». Douze colonnes par côté font
 * vingt-quatre colonnes de nombres, ce qui rend la comparaison d'un strike à
 * l'autre impossible — l'objet même de la chaîne. Le programme le dit :
 * « toutes ne doivent pas être visibles simultanément ».
 */
export const CHAIN_COLUMNS_DEFAULT: readonly string[] = ['bid', 'ask', 'iv', 'delta'];

/**
 * POURQUOI QUATRE, ET PAS SIX.
 *
 * Le défaut a d'abord porté `volume` et `open_interest` — les deux champs
 * servis qui n'étaient jamais affichés. La mesure a tranché autrement : à
 * 1440 px, l'espace de la chaîne fait 879 px une fois l'inspecteur en place,
 * et six colonnes par côté demandent environ 1 100 px. La chaîne s'ouvrait
 * donc en débordant, strike hors du champ — or le strike est l'AXE de lecture,
 * il ne peut pas être ce qu'on doit aller chercher.
 *
 * Quatre colonnes par côté tiennent EXACTEMENT : mesuré en navigateur,
 * largeur de table 879 px pour un conteneur de 879 px, sans défilement
 * horizontal. `volume`, `open interest`, les tailles de carnet et les cinq
 * autres sensibilités sont à UN CLIC, annoncées par le libellé du sélecteur —
 * « 4 sur 12 servies ». Elles ne sont plus jetées ; elles ne sont simplement
 * plus imposées, et au-delà de quatre le conteneur défile avec le strike
 * collant, comme sur un desk.
 */

/** Nombre maximal de colonnes affichables par côté, pour que la chaîne reste lisible. */
export const CHAIN_COLUMNS_MAX = 7;

/**
 * Ce que le contrat NE PUBLIE PAS, avec la raison.
 *
 * Rendu à l'écran sous le sélecteur : sans cela, un utilisateur qui cherche le
 * spread conclut que Vertex a oublié une colonne, alors que le champ n'existe
 * pas et que le fabriquer serait un calcul interdit.
 */
export const COLONNES_NON_SERVIES: ReadonlyArray<{ readonly nom: string; readonly motif: string }> = [
  {
    nom: 'Spread',
    motif:
      'aucun champ servi — l’écart entre les deux cours n’est publié nulle part, et le produire ici serait un calcul financier dans le navigateur, interdit par l’article 8 de la Constitution',
  },
  {
    nom: 'Mid',
    motif: 'aucun champ servi — une moyenne de cotations est un calcul, il appartient au worker',
  },
  {
    nom: 'Dernier échangé',
    motif: 'le worker ne relaie que bid et ask ; aucun dernier prix n’est publié',
  },
  {
    nom: 'Moneyness / ATM',
    motif:
      'aucun champ ne classe un strike à la monnaie — ce rangement est un jugement, il appartient au moteur ; la table montre à la place le SPOT SERVI à sa position dans l’échelle des strikes',
  },
];

export function columnByKey(key: string): ChainColumn | undefined {
  return CHAIN_COLUMNS.find((colonne) => colonne.key === key);
}
