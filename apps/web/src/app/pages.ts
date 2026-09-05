/**
 * Modèle de navigation — 4 groupes. Douze destinations réelles, douze en
 * cible (voir ALL_PAGES).
 * Sources : docs/01-product/NAVIGATION.md, docs/01-product/ROUTES.md et les
 * fiches docs/01-product/pages/NN-*.md (questions métier reprises mot à mot).
 *
 * ARBITRAGE DE ROUTES (ADR implicite du dossier 14) — écarts volontaires
 * vis-à-vis de docs/01-product/ROUTES.md :
 *   - `/ai` remplace `/vertex-ai` : préfixe court et stable, cohérent avec le
 *     libellé « Vertex IA » ;
 *   - `/analysis/:instrument?` et `/options/:underlying?` : le paramètre est
 *     optionnel afin que l'entrée du rail reste atteignable sans instrument
 *     sélectionné (état vide explicite, jamais un instrument par défaut) ;
 *   - `/simulator/:id?` : identifiant de brouillon optionnel dans l'URL.
 * Les paramètres restent des identifiants Vertex opaques et non sensibles
 * (aucun secret, compte ou contenu de portefeuille dans l'URL).
 *
 * Les numéros de lot renvoient aux dossiers de capacité de
 * docs/07-delivery/FOLDER_BY_FOLDER_PROGRAM.md (dossiers 15 à 24).
 */

/**
 * LIEN DE SIGNALEMENT d'une page — lot L0, §4 de la spécification widgets v2.
 *
 * `resource` est une TÊTE FIXE du flux SSE (`<kind>/<key>`), ou `null` quand la
 * tête dépend d'un identifiant (instrument, portefeuille) que le shell ne
 * connaît pas : le badge dit alors « SANS SIGNAL » plutôt que d'inventer une
 * clé. `queryKey` est la clé de cache réellement lue pour la fraîcheur SERVIE.
 * `note` porte le motif, écrit, quand la tête n'est pas fixe ou quand elle est
 * suivie par un autre lot.
 */
interface PageLiveLink {
  readonly resource: string | null;
  readonly queryKey: readonly [string, string];
  readonly note?: string;
}

export interface PageDef {
  /** Identifiant stable de la page. */
  readonly key: string;
  /** Titre affiché (français). */
  readonly title: string;
  /** Cible du lien du rail. */
  readonly navPath: string;
  /** Motif de route React Router. */
  readonly routePath: string;
  /** Question métier de la page — une ligne, reprise de sa fiche produit. */
  readonly question: string;
  /** Dossier/lot du programme qui livrera la page. */
  readonly lot: string;
  /** Ressource principale suivie par le flux SSE, ou `null` avec son motif. */
  readonly live: PageLiveLink | null;
}

export interface NavGroup {
  readonly label: string;
  readonly pages: readonly PageDef[];
}

const today: PageDef = {
  key: 'today',
  title: "Aujourd'hui",
  navPath: '/today',
  routePath: '/today',
  question: "Qu'est-ce qui mérite réellement mon attention maintenant ?",
  lot: 'LOT-15',
  live: { resource: 'attention/global', queryKey: ['snapshot', 'attention/global'] },
};

const opportunities: PageDef = {
  key: 'opportunities',
  title: 'Opportunités',
  navPath: '/opportunities',
  routePath: '/opportunities',
  question: 'Quels candidats admissibles méritent une analyse approfondie ?',
  lot: 'LOT-18',
  live: { resource: 'opportunities/global', queryKey: ['snapshot', 'opportunities/global'] },
};

const analysis: PageDef = {
  key: 'analysis',
  title: 'Analyse',
  navPath: '/analysis',
  routePath: '/analysis/:instrument?',
  question:
    'Que disent les données certifiées sur cet instrument, et quelles limites restent ouvertes ?',
  lot: 'LOT-19',
  // Tête PAR INSTRUMENT (`analysis/<instrument>`, suivie par préfixe) : le
  // shell ne connaît pas l'instrument, il ne peut donc pas nommer la clé.
  live: null,
};

const options: PageDef = {
  key: 'options',
  title: 'Options',
  navPath: '/options',
  routePath: '/options/:underlying?',
  question: 'Quels contrats sont réellement exploitables et quels risques portent-ils ?',
  lot: 'LOT-20',
  // Tête PAR SOUS-JACENT (`option_chain/<underlying>`, suivie par préfixe).
  live: null,
};

const simulator: PageDef = {
  key: 'simulator',
  title: 'Simulateur',
  navPath: '/simulator',
  routePath: '/simulator/:id?',
  question: 'Comment une structure réagit-elle au prix, au temps et à la volatilité ?',
  lot: 'LOT-21',
  // Le simulateur n'a AUCUN snapshot : son résultat vient d'un calcul demandé
  // explicitement. Il n'y a donc rien à signaler, et rien à prétendre suivre.
  live: null,
};

const calendar: PageDef = {
  key: 'calendar',
  title: 'Calendrier',
  navPath: '/calendar',
  routePath: '/calendar',
  question: 'Quels événements peuvent affecter mes instruments et mon portefeuille ?',
  lot: 'LOT-16',
  live: { resource: 'calendar/global', queryKey: ['snapshot', 'calendar/global'] },
};

const markets: PageDef = {
  key: 'markets',
  title: 'Marchés',
  navPath: '/markets',
  routePath: '/markets',
  question: 'Dans quel contexte de marché vais-je analyser les instruments ?',
  lot: 'LOT-17',
  live: { resource: 'markets_overview/global', queryKey: ['snapshot', 'markets_overview/global'] },
};

const charts: PageDef = {
  key: 'charts',
  title: 'Graphiques',
  navPath: '/charts',
  routePath: '/charts/:instrument?',
  question: 'Quelles relations puis-je explorer sans perdre méthode et contexte ?',
  lot: 'LOT-A2',
  // Même tête par instrument que l'Analyse : `analysis/<instrument>`.
  live: null,
};

const portfolio: PageDef = {
  key: 'portfolio',
  title: 'Portefeuille',
  navPath: '/portfolio',
  routePath: '/portfolio',
  question: 'Quelles expositions et concentrations résultent de mon ledger manuel ?',
  lot: 'LOT-22',
  live: {
    // La tête est `portfolio_valuation/<id>` (suivie par PRÉFIXE) ; la clé de
    // cache, elle, est unique côté client — `queryKeyForResource` traduit déjà
    // tout signal de cette famille vers `['snapshot', 'portfolio']`.
    resource: null,
    queryKey: ['snapshot', 'portfolio'],
    note: 'tête par portefeuille (portfolio_valuation/<id>), signalée par préfixe',
  },
};

const catalysts: PageDef = {
  key: 'catalysts',
  title: 'Catalyseurs',
  navPath: '/catalysts',
  routePath: '/catalysts',
  question: 'Quels événements vérifiés peuvent modifier la thèse et quand ?',
  lot: 'LOT-23',
  live: { resource: 'review_queue/global', queryKey: ['snapshot', 'review_queue/global'] },
};

const risk: PageDef = {
  key: 'risks',
  title: 'Risques',
  navPath: '/risks',
  routePath: '/risks',
  question: "Qu'est-ce qui bouge ensemble dans mon périmètre, et qu'est-ce qui protège de quoi ?",
  lot: 'LOT-22',
  live: {
    // Tête FIXE publiée par le worker (`vertex_worker.risk`, key="global").
    // Elle entre dans `SSE_RESOURCES` avec le lot S4 (branche
    // `lot/srv-s4-sse-risk-matrix-20260903`, commits 55fb4b0 et ec5e6c0) :
    // tant que ce lot n'est pas fusionné, `isKnownResource` la refuse et le
    // badge de la page dit « SANS SIGNAL » — ce qui est exactement vrai.
    resource: 'risk_matrix/global',
    queryKey: ['snapshot', 'risk_matrix/global'],
    note: 'suivie par le flux à partir du lot S4 (lot/srv-s4-sse-risk-matrix-20260903)',
  },
};

const system: PageDef = {
  key: 'sources-reports',
  title: 'Sources & Rapports',
  navPath: '/sources-reports',
  routePath: '/sources-reports',
  question: 'Puis-je faire confiance aux sources, traitements et sauvegardes maintenant ?',
  lot: 'LOT-24',
  live: { resource: 'capabilities/global', queryKey: ['snapshot', 'capabilities/global'] },
};

/** Les 4 groupes exacts du rail, dans l'ordre canonique. */
export const NAV_GROUPS: readonly NavGroup[] = [
  { label: 'Décider', pages: [today, opportunities, analysis, options, simulator] },
  { label: 'Observer', pages: [calendar, markets, charts] },
  { label: 'Piloter', pages: [portfolio, risk, catalysts] },
  { label: 'Assistance', pages: [system] },
];

/**
 * Les destinations RÉELLES du rail, à plat, dans l'ordre.
 *
 * La cible du blueprint est douze (`references/pages.md`), et le rail en
 * porte douze : `performance` a rejoint Portefeuille (LOT-08), `follow-up` a
 * rejoint la destination Catalyseurs créée au LOT-10, `ai` a rejoint
 * l'inspecteur d'Analyse et de Portefeuille (LOT-12), et Graphiques a été
 * installée au LOT-A2 (2026-09-02) — composition complète de sa planche,
 * dominante servie par le contrat Analyse, chaque module sans source déclaré
 * absent avec son motif (`AbsentModule`), jamais simulé.
 *
 * Risques a été installé le 2026-09-01 : sa route (`GET /api/v1/risk/matrix`),
 * ses données (snapshot `risk_matrix/global`) et ses tests existent — c'est
 * EXACTEMENT la condition posée juste en dessous, pas une exception à elle.
 * L'écart est mesuré par `scripts/audit_titanium_ledger.py` et journalisé
 * dans `docs/05-design/PAGE_ARBITRATION.md`. Il n'est PAS comblé par une
 * entrée de rail sans route, données ni tests : une façade serait un
 * mensonge d'interface, pas une étape.
 */
export const ALL_PAGES: readonly PageDef[] = NAV_GROUPS.flatMap((group) => group.pages);

/** Route d'atterrissage par défaut. */
export const DEFAULT_PATH = today.navPath;
