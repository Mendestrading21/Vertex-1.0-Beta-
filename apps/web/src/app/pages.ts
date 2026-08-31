/**
 * Modèle de navigation — 4 groupes, 12 pages.
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
};

const opportunities: PageDef = {
  key: 'opportunities',
  title: 'Opportunités',
  navPath: '/opportunities',
  routePath: '/opportunities',
  question: 'Quels candidats admissibles méritent une analyse approfondie ?',
  lot: 'LOT-18',
};

const analysis: PageDef = {
  key: 'analysis',
  title: 'Analyse',
  navPath: '/analysis',
  routePath: '/analysis/:instrument?',
  question:
    'Que disent les données certifiées sur cet instrument, et quelles limites restent ouvertes ?',
  lot: 'LOT-19',
};

const options: PageDef = {
  key: 'options',
  title: 'Options',
  navPath: '/options',
  routePath: '/options/:underlying?',
  question: 'Quels contrats sont réellement exploitables et quels risques portent-ils ?',
  lot: 'LOT-20',
};

const simulator: PageDef = {
  key: 'simulator',
  title: 'Simulateur',
  navPath: '/simulator',
  routePath: '/simulator/:id?',
  question: 'Comment une structure réagit-elle au prix, au temps et à la volatilité ?',
  lot: 'LOT-21',
};

const calendar: PageDef = {
  key: 'calendar',
  title: 'Calendrier',
  navPath: '/calendar',
  routePath: '/calendar',
  question: 'Quels événements peuvent affecter mes instruments et mon portefeuille ?',
  lot: 'LOT-16',
};

const markets: PageDef = {
  key: 'markets',
  title: 'Marchés',
  navPath: '/markets',
  routePath: '/markets',
  question: 'Dans quel contexte de marché vais-je analyser les instruments ?',
  lot: 'LOT-17',
};

const portfolio: PageDef = {
  key: 'portfolio',
  title: 'Portefeuille',
  navPath: '/portfolio',
  routePath: '/portfolio',
  question: 'Quelles expositions et concentrations résultent de mon ledger manuel ?',
  lot: 'LOT-22',
};

const followUp: PageDef = {
  key: 'follow-up',
  title: 'Suivi',
  navPath: '/follow-up',
  routePath: '/follow-up',
  question: 'Quelles thèses, alertes et informations doivent être revues ?',
  lot: 'LOT-23',
};

const performance: PageDef = {
  key: 'performance',
  title: 'Performance',
  navPath: '/performance',
  routePath: '/performance',
  question:
    'Quelle performance ai-je réellement enregistrée, avec quels risques et contributions ?',
  lot: 'LOT-23',
};

const vertexAi: PageDef = {
  key: 'ai',
  title: 'Vertex IA',
  navPath: '/ai',
  routePath: '/ai',
  question:
    'Comment expliquer, relier et résumer les données certifiées sans créer une seconde vérité ?',
  lot: 'LOT-24',
};

const system: PageDef = {
  key: 'sources-reports',
  title: 'Sources & Rapports',
  navPath: '/sources-reports',
  routePath: '/sources-reports',
  question: 'Puis-je faire confiance aux sources, traitements et sauvegardes maintenant ?',
  lot: 'LOT-24',
};

/** Les 4 groupes exacts du rail, dans l'ordre canonique. */
export const NAV_GROUPS: readonly NavGroup[] = [
  { label: 'Décider', pages: [today, opportunities, analysis, options, simulator] },
  { label: 'Observer', pages: [calendar, markets] },
  { label: 'Piloter', pages: [portfolio, followUp, performance] },
  { label: 'Assistance', pages: [vertexAi, system] },
];

/** Les 12 pages, à plat, dans l'ordre du rail. */
export const ALL_PAGES: readonly PageDef[] = NAV_GROUPS.flatMap((group) => group.pages);

/** Route d'atterrissage par défaut. */
export const DEFAULT_PATH = today.navPath;
