import { formatAge } from '../FreshnessBadge.tsx';

/**
 * LIVEDATAINDICATOR — le statut canonique d'un jeu de données.
 *
 * CE QU'IL EST. Une pastille compacte qui répond à une seule question : « à
 * quel point puis-je me fier à ce que je lis en ce moment ? » Elle porte un
 * état nommé, la fraîcheur SERVIE, la source, et le droit quand il manque.
 *
 * POURQUOI IL NE DIT PAS « ● LIVE · 124 ms ».
 *
 * La maquette de référence montrait une latence en millisecondes. Le contrat
 * serveur ne publie AUCUNE latence : il publie `as_of`, `age_seconds`,
 * `freshness_policy`, `budget_seconds`, `entitlements` et un statut typé.
 * Afficher « 124 ms » aurait donc exigé de le fabriquer côté navigateur — un
 * chiffre inventé, présenté comme une mesure. Le champ n'existe pas dans ce
 * composant, et le type ne permet pas de l'y glisser. Le jour où le serveur
 * publiera une latence, elle entrera ici avec sa provenance.
 *
 * ET POURQUOI `LIVE` SE MÉRITE. Vertex tient un flux SSE *signal-only* : chaque
 * trame vaut `{resource, version}` et ne transporte aucune donnée. Un lien SSE
 * ouvert ne rend donc PAS une donnée « live » — il dit seulement qu'on sera
 * prévenu d'une nouvelle publication. `LiveBadge` (état du LIEN) et ce
 * composant (état de la DONNÉE) répondent à deux questions différentes, et
 * c'est délibéré : les confondre est exactement la façon dont une interface se
 * met à mentir. L'état `live` n'est ici accessible qu'à une donnée dont le
 * serveur a déclaré la politique de fraîcheur temps réel ET dont l'âge tient
 * dans le budget publié.
 *
 * MOUVEMENT. Une seule pulsation, très faible, réservée à `live`, supprimée
 * sous `prefers-reduced-motion`. Rien d'autre ne bouge : un tableau de bord qui
 * clignote ne dit pas « vivant », il dit « ne me lisez pas ».
 */

/**
 * Les huit états. Ils sont EXCLUSIFS et ordonnés du plus fiable au moins
 * fiable ; aucun n'est un synonyme décoratif d'un autre.
 */
export type LiveDataState =
  /** Politique temps réel ET âge dans le budget servi. */
  | 'live'
  /** Donnée réelle mais volontairement retardée par la source (droit différé). */
  | 'delayed'
  /** Âge au-delà du budget servi : la donnée existe, elle ne décrit plus l'instant. */
  | 'stale'
  /** Marché fermé : la dernière valeur est la bonne, elle ne bougera plus d'ici l'ouverture. */
  | 'closed'
  /** Saisie par l'utilisateur. Aucune source externe ne l'a produite. */
  | 'manual'
  /** Population SYNTHETIC ou DEMO : contenu généré, jamais du marché. */
  | 'simulated'
  /** Aucune valeur publiée, ou droit manquant. */
  | 'unavailable'
  /** Publiée mais partielle, contradictoire ou issue d'un chemin de secours déclaré. */
  | 'degraded';

interface Presentation {
  readonly label: string;
  /** Plein = la donnée décrit l'instant. Creux = elle ne le décrit plus. */
  readonly filled: boolean;
  readonly tone: 'positive' | 'warning' | 'negative' | 'neutral' | 'muted';
  /** Phrase de définition, lisible au clavier — jamais réservée au survol. */
  readonly meaning: string;
}

/**
 * Le vocabulaire, en un seul endroit.
 *
 * `unknown` n'a pas d'entrée : un état inconnu ne doit jamais se replier sur un
 * état rassurant. Il n'est pas représentable, donc il n'est pas représenté —
 * l'appelant doit choisir `unavailable` ou `degraded` en connaissance de cause.
 */
const PRESENTATION: Readonly<Record<LiveDataState, Presentation>> = {
  live: {
    label: 'EN COURS',
    filled: true,
    tone: 'positive',
    meaning: "politique temps réel, âge dans le budget publié par le serveur",
  },
  delayed: {
    label: 'RETARDÉ',
    filled: true,
    tone: 'warning',
    meaning: 'donnée réelle, volontairement différée par la source',
  },
  stale: {
    label: 'PÉRIMÉ',
    filled: false,
    tone: 'warning',
    meaning: "âge au-delà du budget servi : la donnée ne décrit plus l'instant",
  },
  closed: {
    label: 'MARCHÉ FERMÉ',
    filled: false,
    tone: 'neutral',
    meaning: "dernière valeur de séance ; elle ne bougera pas avant l'ouverture",
  },
  manual: {
    label: 'SAISIE MANUELLE',
    filled: true,
    tone: 'neutral',
    meaning: 'déclarée par vous ; aucune source externe ne la produit ni ne la corrige',
  },
  simulated: {
    label: 'SYNTHÉTIQUE',
    filled: true,
    tone: 'warning',
    meaning: 'contenu généré pour le développement — jamais une donnée de marché',
  },
  unavailable: {
    label: 'INDISPONIBLE',
    filled: false,
    tone: 'negative',
    meaning: 'aucune valeur publiée, ou droit manquant sur cette source',
  },
  degraded: {
    label: 'DÉGRADÉ',
    filled: false,
    tone: 'negative',
    meaning: 'publiée mais partielle, contradictoire ou issue d’un chemin de secours déclaré',
  },
};

export interface LiveDataIndicatorProps {
  readonly state: LiveDataState;
  /**
   * Âge en secondes, SERVI par l'API. `null` = âge non publié — et c'est dit,
   * pas masqué. Ce composant ne lit jamais l'horloge du navigateur.
   */
  readonly ageSeconds: number | null;
  /** Instant d'observation servi (ISO). Rendu en `<time>` quand il existe. */
  readonly asOf?: string | null;
  /** Nom de la source, tel que publié. */
  readonly source?: string | null;
  /**
   * Droit manquant, quand il est la cause. Il n'est affiché que sur
   * `unavailable` : ailleurs il ne serait qu'un mot de plus.
   */
  readonly missingEntitlement?: string | null;
  /** `compact` n'affiche que la pastille et l'état ; `full` ajoute la ligne de contexte. */
  readonly variant?: 'compact' | 'full';
}

export function LiveDataIndicator({
  state,
  ageSeconds,
  asOf = null,
  source = null,
  missingEntitlement = null,
  variant = 'full',
}: LiveDataIndicatorProps) {
  const vue = PRESENTATION[state];
  // Le nom accessible porte l'état ET sa définition : quelqu'un qui ne voit pas
  // la couleur obtient l'information complète, sans dépendre d'un survol.
  const nom = `${vue.label} — ${vue.meaning}`;

  return (
    <span
      className="vx-live"
      data-state={state}
      data-tone={vue.tone}
      data-variant={variant}
      role="status"
      aria-label={nom}
    >
      <span className="vx-live-dot" data-filled={vue.filled ? 'true' : 'false'} aria-hidden="true" />
      {/* Le mot double toujours la couleur et la forme : jamais la couleur seule. */}
      <span className="vx-live-label">{vue.label}</span>
      {variant === 'compact' ? null : (
        <span className="vx-live-context">
          {source === null ? null : <span className="vx-live-source">{source}</span>}
          <span className="vx-live-age">{formatAge(ageSeconds)}</span>
          {asOf === null ? null : (
            <time className="vx-live-asof" dateTime={asOf}>
              {asOf}
            </time>
          )}
          {state === 'unavailable' && missingEntitlement !== null ? (
            <span className="vx-live-entitlement">droit requis : {missingEntitlement}</span>
          ) : null}
        </span>
      )}
    </span>
  );
}
