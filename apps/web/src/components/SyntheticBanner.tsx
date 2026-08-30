/**
 * Bandeau de nature de population — visible, jamais masquable, FAIL-CLOSED.
 *
 * `population` est le SEUL champ qui sépare une donnée réelle d'une donnée
 * générée. Le composant rendait `null` dès que l'étiquette n'était pas
 * exactement `SYNTHETIC` : une étiquette forgée (`REAL`, `LIVE`,
 * `IBKR_REALTIME_ENTITLED`) ou absente SUPPRIMAIT donc l'avertissement au lieu
 * de fermer — l'inverse exact du fail-closed, sur le seul champ qui compte
 * pour cette distinction (5e audit adversarial).
 *
 * Trois règles tiennent ce fichier :
 *
 * 1. le bandeau ne disparaît jamais. Une étiquette inconnue ou absente
 *    AVERTIT : l'utilisateur doit voir qu'il ne sait pas ce qu'il regarde ;
 * 2. chaque nature déclarée a un rendu DISTINCT. « Réel, retardé, théorique,
 *    simulé et démonstration ne partagent jamais le même statut visuel ou
 *    sémantique » (`.claude/rules/financial-safety.md`) ;
 * 3. le bandeau dit ce qui est DÉCLARÉ, pas ce qui est vérifié. L'API ne peut
 *    pas prouver qu'une donnée étiquetée `REAL` l'est ; l'interface ne le
 *    prétend donc pas non plus.
 *
 * Identité visuelle Black Glass : ambre = prudence ou dégradation, rouge =
 * risque, neutre pour le reste. Aucune couleur brute — uniquement des tokens
 * `--vx-*`, sinon `src/design/no-raw-colors.test.ts` échoue.
 */

/** Ambre = prudence/dégradation, rouge = risque, neutre = ni l'un ni l'autre. */
export type PopulationTone = 'neutral' | 'caution' | 'risk';

interface PopulationNature {
  /** Libellé court, unique, en français — jamais partagé avec une autre nature. */
  readonly label: string;
  readonly tone: PopulationTone;
  /** Ce que la nature signifie pour le lecteur, sans euphémisme. */
  readonly detail: string;
}

/**
 * Vocabulaire fermé publié par le relais (`POPULATION_LABELS` côté API).
 *
 * Une nature absente de cette table est traitée comme NON RECONNUE, jamais
 * comme « rien à signaler » : ajouter un membre côté API sans l'ajouter ici
 * dégrade le rendu vers l'avertissement, pas vers le silence.
 */
export const POPULATION_NATURES = {
  REAL: {
    label: 'DONNÉES RÉELLES',
    tone: 'neutral',
    detail:
      'Nature déclarée par le worker : observations de marché. Le relais ne vérifie pas cette déclaration, il la transmet.',
  },
  DELAYED: {
    label: 'DONNÉES RETARDÉES',
    tone: 'caution',
    detail:
      'Observations différées : elles ne décrivent pas le marché à cet instant. Ne jamais les lire comme un prix courant.',
  },
  THEORETICAL: {
    label: 'VALEURS THÉORIQUES',
    tone: 'caution',
    detail:
      'Valeurs calculées par un modèle sous hypothèses, jamais observées sur un marché.',
  },
  SIMULATED: {
    label: 'DONNÉES SIMULÉES',
    tone: 'caution',
    detail:
      'Résultats d’une simulation : aucune de ces valeurs n’a été cotée ni échangée.',
  },
  SYNTHETIC: {
    label: 'DONNÉES SYNTHÉTIQUES',
    tone: 'caution',
    detail:
      'Population « SYNTHETIC » publiée par le worker : contenu généré pour le développement, aucune donnée réelle ni de marché.',
  },
  DEMO: {
    label: 'DONNÉES DE DÉMONSTRATION',
    tone: 'caution',
    detail:
      'Contenu de démonstration : il illustre l’interface et ne provient d’aucun abonnement.',
  },
  USER_DECLARED: {
    label: 'SAISIE UTILISATEUR',
    tone: 'neutral',
    detail:
      'Déclaré à la main par vous : Vertex le restitue sans le rapprocher d’une source externe.',
  },
  SYNTHETIC_MARKS_REAL_LEDGER: {
    label: 'MARQUES SYNTHÉTIQUES SUR REGISTRE DÉCLARÉ',
    tone: 'caution',
    detail:
      'Deux populations distinctes, jamais additionnées : le registre vient de vos saisies, les valorisations sont générées.',
  },
  EMPTY: {
    label: 'POPULATION VIDE',
    tone: 'caution',
    detail:
      'Aucune observation retenue pour cet univers : ce qui est affiché ne décrit aucune donnée.',
  },
} as const satisfies Record<string, PopulationNature>;

export type PopulationLabel = keyof typeof POPULATION_NATURES;

/** Nature non déclarée par le producteur (champ absent ou vide). */
const UNDECLARED: PopulationNature = {
  label: 'NATURE NON DÉCLARÉE',
  tone: 'risk',
  detail:
    'Le producteur n’a pas déclaré la nature de ces données. Rien ne permet de savoir si elles sont réelles, retardées ou générées : ne rien en conclure.',
};

/** Étiquette présente mais hors du vocabulaire fermé du relais. */
const UNRECOGNISED: PopulationNature = {
  label: 'NATURE NON RECONNUE',
  tone: 'risk',
  detail:
    'L’étiquette reçue n’appartient pas au vocabulaire publié. Le seul champ qui sépare une donnée réelle d’une donnée générée est illisible : ne rien en conclure.',
};

/** Teintes autorisées, exclusivement des tokens Black Glass. */
const TONE_ACCENT: Record<PopulationTone, string> = {
  neutral: 'var(--vx-text)',
  caution: 'var(--vx-warning)',
  risk: 'var(--vx-negative)',
};

const TONE_EDGE: Record<PopulationTone, string> = {
  neutral: 'var(--vx-border-strong)',
  caution: 'var(--vx-warning)',
  risk: 'var(--vx-negative)',
};

/** Longueur maximale d’une étiquette inconnue recopiée à l’écran. */
const MAX_ECHOED_LABEL = 24;

function isDeclaredLabel(value: string): value is PopulationLabel {
  return Object.hasOwn(POPULATION_NATURES, value);
}

/**
 * Nature à rendre pour l'étiquette reçue, et clé technique associée.
 *
 * Fail-closed : tout ce qui n'est pas un membre exact du vocabulaire tombe
 * dans `UNRECOGNISED` (ou `UNDECLARED` si rien n'a été déclaré). Aucune
 * normalisation, aucun `trim`, aucune casse tolérée — `'SYNTHETIC '` n'est pas
 * `'SYNTHETIC'`, et le lecteur doit le savoir.
 *
 * Le TYPE est vérifié avant toute chose. `hasOwnProperty` et l'indexation
 * COERCENT leur clé en chaîne : un objet portant `toString: () => 'REAL'`
 * affichait « DONNÉES RÉELLES » en ton neutre, et un nombre faisait planter le
 * rendu sur `.slice` (6e audit). Le contrat d'API type `population` en
 * `string | null`, donc ce n'est pas atteignable aujourd'hui — mais une
 * garantie fail-closed qui repose sur la bonne foi de l'appelant n'en est pas
 * une.
 */
export function resolvePopulationNature(population: unknown): {
  readonly key: string;
  readonly nature: PopulationNature;
} {
  if (population === null || population === undefined || population === '') {
    return { key: 'UNDECLARED', nature: UNDECLARED };
  }
  if (typeof population !== 'string') {
    return { key: 'UNRECOGNISED', nature: UNRECOGNISED };
  }
  if (isDeclaredLabel(population)) {
    return { key: population, nature: POPULATION_NATURES[population] };
  }
  return { key: 'UNRECOGNISED', nature: UNRECOGNISED };
}

export function SyntheticBanner({ population }: { readonly population: string | null }) {
  const { key, nature } = resolvePopulationNature(population);
  // L'écho ne cite QUE des chaînes : une valeur d'un autre type n'a pas de
  // libellé à montrer, et `.slice` la ferait planter.
  const echoed =
    key === 'UNRECOGNISED' && typeof population === 'string'
      ? population.slice(0, MAX_ECHOED_LABEL) +
        (population.length > MAX_ECHOED_LABEL ? '…' : '')
      : null;

  return (
    <p
      className="vx-synthetic-banner"
      role={nature.tone === 'risk' ? 'alert' : 'status'}
      data-vx-population-banner=""
      data-population={population ?? ''}
      data-vx-nature={key}
      data-vx-tone={nature.tone}
      style={{ borderColor: TONE_EDGE[nature.tone] }}
    >
      <strong style={{ color: TONE_ACCENT[nature.tone] }}>{nature.label}</strong>
      <span>
        {nature.detail}
        {echoed !== null ? ` Étiquette reçue : « ${echoed} ».` : ''}
      </span>
    </p>
  );
}
