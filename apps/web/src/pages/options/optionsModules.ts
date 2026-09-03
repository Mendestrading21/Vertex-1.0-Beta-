/**
 * Catalogue de la planche §5 (Options) — `pages-05-06-options-simulator.png`,
 * moitié gauche. Chaque module est SERVI par un contrat existant ou DÉCLARÉ
 * absent avec le motif mesuré ; aucun n'est simulé (article 17).
 *
 * Le snapshot `option_chain/{underlying}` publie : le spot observé, les
 * hypothèses du calcul d'IV (taux, dividende, côté de quote, âge maximal),
 * les groupes (expiration, trading_class) avec leurs contrats — quote
 * verbatim, IV et Greeks THÉORIQUES ou leur raison d'absence — le budget de
 * lignes et la couverture. Le dossier d'analyse du sous-jacent apporte la
 * série de clôtures ; Marchés, la variation 1 j. Ce que la planche montre
 * au-delà — mouvement attendu, IV de référence, rang d'IV, métriques de
 * stratégie — n'a ni source ni contrat ; le composeur et le profil de payoff
 * vivent sur Simulateur, joints par l'unique action de l'inspecteur.
 */
import type { AbsenceReason } from '../../components/AbsentModule.tsx';
import type { WidgetSize, WidgetVariant } from '../../components/widgets/Widget.tsx';

export type OptionsModuleStatus =
  | { readonly kind: 'served'; readonly contract: string }
  | { readonly kind: 'absent'; readonly reason: AbsenceReason; readonly note: string };

export interface OptionsModule {
  readonly id: string;
  /** Span de composition sur la planche — jamais une apparence (ADR-017). */
  readonly size: WidgetSize;
  /** Variante visuelle du vocabulaire fermé de WIDGET_LIBRARY.md. */
  readonly variant: WidgetVariant;
  readonly title: string;
  readonly question: string;
  readonly status: OptionsModuleStatus;
}

const CHAIN = 'GET /api/v1/options/{underlying}/chain';

export const OPTIONS_MODULES: readonly OptionsModule[] = [
  {
    id: 'underlying',
    size: 'M',
    variant: 'support',
    title: 'Sous-jacent',
    question: 'Quelle est la dernière clôture publiée du sous-jacent, sa variation, sa série ?',
    status: { kind: 'served', contract: 'GET /api/v1/markets/overview — ticker ; GET /api/v1/analysis/{instrument} — bars' },
  },
  {
    id: 'identity-strip',
    size: 'M',
    variant: 'support',
    title: 'Snapshot de chaîne',
    question: 'Quel snapshot, quelles références, quelle couverture et quel budget ?',
    status: { kind: 'served', contract: `${CHAIN} — snapshot_version, as_of, coverage, row_budget, value_nature` },
  },
  {
    id: 'spot',
    size: 'S',
    variant: 'support',
    title: 'Spot publié',
    question: 'À quel spot observé le calcul d’IV a-t-il été fait ?',
    status: { kind: 'served', contract: `${CHAIN} — spot` },
  },
  {
    id: 'expected-move',
    size: 'S',
    variant: 'support',
    title: 'Mouvement attendu',
    question: 'Quel mouvement le marché d’options implique-t-il jusqu’à l’échéance ?',
    status: {
      kind: 'absent',
      reason: 'SERVER_CONTRACT_MISSING',
      note: 'Un mouvement implicite se dérive d’une IV ATM et d’une maturité ; aucun contrat ne le publie, et le dériver ici serait le calcul financier interdit en TypeScript.',
    },
  },
  {
    id: 'iv-reference',
    size: 'S',
    variant: 'support',
    title: 'IV de référence',
    question: 'Quelle IV « au niveau du spot » résume la chaîne ?',
    status: {
      kind: 'absent',
      reason: 'SERVER_CONTRACT_MISSING',
      note: 'Choisir le strike de référence est une décision de calcul ; le worker publie une IV par contrat, jamais une IV résumée.',
    },
  },
  {
    id: 'iv-rank',
    size: 'S',
    variant: 'support',
    title: 'Rang d’IV',
    question: 'L’IV actuelle est-elle haute ou basse par rapport à son histoire ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Aucun historique d’IV n’est collecté ; un rang sans historique serait une valeur inventée.',
    },
  },
  {
    id: 'dividend',
    size: 'S',
    variant: 'support',
    title: 'Dividende (hypothèse)',
    question: 'Quel rendement de dividende le calcul d’IV a-t-il supposé ?',
    status: { kind: 'served', contract: `${CHAIN} — assumptions.dividend_yield` },
  },
  {
    id: 'rate',
    size: 'S',
    variant: 'support',
    title: 'Taux (hypothèse)',
    question: 'Quel taux sans risque le calcul d’IV a-t-il supposé ?',
    status: { kind: 'served', contract: `${CHAIN} — assumptions.rate, quote_side_for_iv, max_quote_age_seconds` },
  },
  {
    id: 'vol-structure',
    size: 'M',
    variant: 'support',
    title: 'Structure par échéance',
    question: 'Comment les IV publiées se répartissent-elles d’une échéance à l’autre ?',
    status: { kind: 'served', contract: `${CHAIN} — expirations[].contracts[].iv (petits multiples)` },
  },
  {
    id: 'underlying-series',
    size: 'M',
    variant: 'support',
    title: 'Série du sous-jacent',
    question: 'Comment le sous-jacent a-t-il clôturé sur les dernières séances ?',
    status: { kind: 'served', contract: 'GET /api/v1/analysis/{instrument} — bars' },
  },
  {
    id: 'iv-smile',
    size: 'M',
    variant: 'support',
    title: 'Sourire d’IV',
    question: 'Comment l’IV publiée varie-t-elle avec le strike, calls et puts, sur le groupe affiché ?',
    status: { kind: 'served', contract: `${CHAIN} — expirations[].contracts[].iv (géométrie seule)` },
  },
  {
    id: 'chain',
    size: 'XL',
    variant: 'dominant',
    title: 'Chaîne d’options',
    question: 'Quels contrats sont réellement exploitables et quels risques portent-ils ?',
    status: { kind: 'served', contract: `${CHAIN} — expirations[].contracts[]` },
  },
  {
    id: 'strategy-builder',
    size: 'S',
    variant: 'support',
    title: 'Composeur de stratégie',
    question: 'Quelle structure déclarer à partir de ce contrat ?',
    status: {
      kind: 'absent',
      reason: 'DECISION_PENDING',
      note: 'Le composeur vit sur Simulateur, joint par l’unique action de l’inspecteur (« Envoyer au Simulateur ») ; le dupliquer ici créerait une seconde saisie de la même structure.',
    },
  },
  {
    id: 'payoff-profile',
    size: 'S',
    variant: 'support',
    title: 'Profil de payoff',
    question: 'Que vaut la structure à l’expiration selon le spot ?',
    status: {
      kind: 'absent',
      reason: 'DECISION_PENDING',
      note: 'Le payoff est calculé par le serveur pour une structure DÉCLARÉE sur Simulateur ; aucun payoff n’existe pour un contrat seul non déclaré.',
    },
  },
  {
    id: 'strategy-metrics',
    size: 'M',
    variant: 'support',
    title: 'Métriques de stratégie',
    question: 'Probabilité de profit, espérance, ratio : que valent-ils ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Aucune probabilité calibrée ni espérance n’est publiée ; le Simulateur ne publie que des grilles THÉORIQUES et des breakevens certifiés.',
    },
  },
];

export function absentOptionsModules(): readonly (OptionsModule & {
  readonly status: Extract<OptionsModuleStatus, { kind: 'absent' }>;
})[] {
  return OPTIONS_MODULES.flatMap((module) =>
    module.status.kind === 'absent' ? [{ ...module, status: module.status }] : [],
  );
}

export function optionsModule(id: string): OptionsModule {
  const module = OPTIONS_MODULES.find((candidate) => candidate.id === id);
  if (module === undefined) {
    throw new Error(`Unknown options module: ${id}`);
  }
  return module;
}
