/**
 * Catalogue de la planche §4 (Analyse) —
 * `pages-03-04-opportunities-analysis.png`, moitié droite. Chaque module est
 * SERVI par un contrat existant ou DÉCLARÉ absent avec le motif mesuré ;
 * aucun n'est simulé (article 17).
 *
 * Le dossier `analysis/{instrument}` publie : barres OHLCV validées,
 * indicateurs (volatilité réalisée, ATR, force relative), rail evidence,
 * scénarios THÉORIQUES et l'`AdviceResult` de l'unique moteur. Le snapshot
 * Marchés apporte la variation 1 j et le secteur ; le calendrier, les
 * catalyseurs de l'instrument ; la route SEC, les faits officiels. Ce que la
 * planche montre au-delà — oscillateurs, régime, confiance du modèle,
 * valorisation, révisions d'analystes, niveaux, contradictions — n'a ni
 * source ni contrat.
 */
import type { AbsenceReason } from '../../components/AbsentModule.tsx';
import type { WidgetSize, WidgetVariant } from '../../components/widgets/Widget.tsx';

export type AnalysisModuleStatus =
  | { readonly kind: 'served'; readonly contract: string }
  | { readonly kind: 'absent'; readonly reason: AbsenceReason; readonly note: string };

export interface AnalysisModule {
  readonly id: string;
  /** Span de composition sur la planche — jamais une apparence (ADR-017). */
  readonly size: WidgetSize;
  /** Variante visuelle du vocabulaire fermé de WIDGET_LIBRARY.md. */
  readonly variant: WidgetVariant;
  readonly title: string;
  readonly question: string;
  readonly status: AnalysisModuleStatus;
}

const DOSSIER = 'GET /api/v1/analysis/{instrument}';

export const ANALYSIS_MODULES: readonly AnalysisModule[] = [
  {
    id: 'instrument-header',
    size: 'M',
    variant: 'support',
    title: 'Instrument',
    question: 'Quelle est la dernière clôture publiée, sa variation et sa série ?',
    status: { kind: 'served', contract: `${DOSSIER} — bars ; GET /api/v1/markets/overview — return_1d_pct` },
  },
  {
    id: 'identity-facts',
    size: 'M',
    variant: 'support',
    title: 'Identité',
    question: 'Quel instrument, quel secteur, quelle devise, quelle population ?',
    status: { kind: 'served', contract: `${DOSSIER} — bars.currency, population ; markets/overview — sector` },
  },
  {
    id: 'chart',
    size: 'XL',
    variant: 'dominant',
    title: 'Chandeliers et volume',
    question: 'Que disent les données certifiées sur cet instrument ?',
    status: { kind: 'served', contract: `${DOSSIER} — bars (Lightweight Charts™)` },
  },
  {
    id: 'indicators',
    size: 'S',
    variant: 'support',
    title: 'Indicateurs techniques',
    question: 'Quelles mesures le moteur a-t-il calculées sur la série ?',
    status: { kind: 'served', contract: `${DOSSIER} — indicators` },
  },
  {
    id: 'oscillators',
    size: 'S',
    variant: 'support',
    title: 'Oscillateurs',
    question: 'RSI, MACD, stochastique : que disent-ils ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Le registre des calculs ne publie aucun oscillateur ; en dériver un dans le navigateur serait le calcul financier interdit en TypeScript.',
    },
  },
  {
    id: 'regime',
    size: 'S',
    variant: 'support',
    title: 'Régime',
    question: 'Dans quel régime de marché cet instrument évolue-t-il ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Le moteur publie lui-même « no regime assessment exists for this population » : la preuve requise « regime » manque à chaque candidat.',
    },
  },
  {
    id: 'fundamental-quality',
    size: 'S',
    variant: 'support',
    title: 'Qualité fondamentale',
    question: 'Les fondamentaux sont-ils solides ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Les faits SEC sont relayés verbatim (module « Faits officiels ») ; aucun ratio ni note de qualité n’est publié, et le relais interdit d’en calculer.',
    },
  },
  {
    id: 'valuation',
    size: 'S',
    variant: 'support',
    title: 'Valorisation',
    question: 'L’instrument est-il cher ou bon marché ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Aucun multiple ni juste valeur n’est publié ; rapprocher un prix d’un fait SEC serait une valorisation calculée hors autorité.',
    },
  },
  {
    id: 'financials',
    size: 'M',
    variant: 'support',
    title: 'Faits officiels (SEC)',
    question: 'Quels dépôts et faits XBRL officiels sont publiés pour cet instrument ?',
    status: { kind: 'served', contract: 'GET /api/v1/sources/sec/{instrument}/fundamentals' },
  },
  {
    id: 'model-confidence',
    size: 'S',
    variant: 'support',
    title: 'Confiance du modèle',
    question: 'À quel point le verdict est-il sûr ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Aucune probabilité calibrée, validée hors échantillon et versionnée n’est publiée ; sans elle, aucun degré de confiance ne peut être affiché.',
    },
  },
  {
    id: 'analyst-revisions',
    size: 'S',
    variant: 'support',
    title: 'Révisions d’analystes',
    question: 'Le consensus s’est-il déplacé ?',
    status: {
      kind: 'absent',
      reason: 'NO_SOURCE',
      note: 'Aucune source de consensus ni de révisions n’est collectée ; rien n’autorise le scraping d’un tiers.',
    },
  },
  {
    id: 'verdict',
    size: 'M',
    variant: 'support',
    title: 'Verdict analytique',
    question: 'Quel statut et quelle direction l’unique moteur publie-t-il ?',
    status: { kind: 'served', contract: `${DOSSIER} — advice (AdviceEngine)` },
  },
  {
    id: 'scenarios',
    size: 'M',
    variant: 'support',
    title: 'Scénarios',
    question: 'Que vaudrait la structure de base sous d’autres spots et horizons ?',
    status: { kind: 'served', contract: `${DOSSIER} — scenarios (THÉORIQUE)` },
  },
  {
    id: 'upcoming-catalysts',
    size: 'S',
    variant: 'support',
    title: 'Catalyseurs à venir',
    question: 'Quels événements publiés concernent cet instrument ?',
    status: { kind: 'served', contract: 'GET /api/v1/calendar — agenda filtré par ticker' },
  },
  {
    id: 'key-risks',
    size: 'S',
    variant: 'support',
    title: 'Risques déclarés',
    question: 'Quelles limites et gates dégradées le moteur déclare-t-il ?',
    status: { kind: 'served', contract: `${DOSSIER} — advice.risk_summary, limitations, gates` },
  },
  {
    id: 'peers',
    size: 'S',
    variant: 'support',
    title: 'Pairs du secteur',
    question: 'Comment les instruments du même secteur ont-ils clôturé ?',
    status: { kind: 'served', contract: 'GET /api/v1/markets/overview — sectors[].tickers' },
  },
  {
    id: 'evidence',
    size: 'S',
    variant: 'support',
    title: 'Evidence',
    question: 'Quels clusters d’observations la fusion a-t-elle retenus ?',
    status: { kind: 'served', contract: `${DOSSIER} — evidence` },
  },
  {
    id: 'levels',
    size: 'S',
    variant: 'support',
    title: 'Niveaux clés',
    question: 'Quels supports et résistances sont publiés ?',
    status: {
      kind: 'absent',
      reason: 'SERVER_CONTRACT_MISSING',
      note: 'Aucun niveau n’est publié dans le dossier ; les extrêmes de la série sont lisibles dans la table OHLCV, mais un niveau est une décision de calcul qui reste au serveur.',
    },
  },
  {
    id: 'contradictions',
    size: 'S',
    variant: 'support',
    title: 'Contradictions',
    question: 'Quels faits se contredisent dans ce dossier ?',
    status: {
      kind: 'absent',
      reason: 'SERVER_CONTRACT_MISSING',
      note: 'L’explication IA nomme des contradictions sur un DTO validé ; le dossier lui-même n’en publie aucune liste.',
    },
  },
];

export function absentAnalysisModules(): readonly (AnalysisModule & {
  readonly status: Extract<AnalysisModuleStatus, { kind: 'absent' }>;
})[] {
  return ANALYSIS_MODULES.flatMap((module) =>
    module.status.kind === 'absent' ? [{ ...module, status: module.status }] : [],
  );
}

export function analysisModule(id: string): AnalysisModule {
  const module = ANALYSIS_MODULES.find((candidate) => candidate.id === id);
  if (module === undefined) {
    throw new Error(`Unknown analysis module: ${id}`);
  }
  return module;
}
