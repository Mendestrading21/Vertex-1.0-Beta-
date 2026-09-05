/**
 * Module dont la place est TENUE et l'absence DÉCLARÉE.
 *
 * POURQUOI CE COMPOSANT EXISTE. Les douze planches canoniques montrent des
 * modules dont une large part n'a aucune source dans ce dépôt. La consigne
 * produit est de livrer la composition d'abord, les branchements ensuite.
 *
 * Cet ordre n'est légitime qu'à une condition, et ce composant l'incarne : un
 * module non branché montre sa GÉOMÉTRIE RÉELLE, son titre et sa question, puis
 * déclare pourquoi il est vide — avec un motif du vocabulaire fermé ci-dessous.
 *
 * TROIS CHOSES QU'IL NE FAIT JAMAIS.
 *
 * 1. Aucun chiffre. Pas un cours, pas un pourcentage, pas un compte. Un
 *    placeholder numérique est une valeur inventée, et l'article 17 de la
 *    Constitution l'interdit — c'est aussi la seule règle que la phase
 *    « affichage d'abord » ne peut pas se permettre d'assouplir.
 * 2. Aucun rectangle gris muet. Une zone vide sans motif occupe la place sans
 *    rien dire : le lecteur ne sait pas s'il manque une source, un abonnement
 *    ou une décision. Les trois appellent des actions différentes.
 * 3. Aucune promesse. Le motif dit ce qui manque, pas quand ce sera livré.
 */

/** Vocabulaire FERMÉ des natures d'absence. Deny-by-default. */
export const ABSENCE_REASONS = {
  NO_SOURCE: {
    label: 'AUCUNE SOURCE',
    court: 'rien ne collecte cette donnée',
    detail:
      'Aucune source ne publie cette donnée aujourd’hui. Ce n’est pas un défaut d’affichage : rien ne la collecte.',
  },
  SUBSCRIPTION_REQUIRED: {
    label: 'ABONNEMENT REQUIS',
    court: 'abonnement distinct, non souscrit',
    detail:
      'La donnée existe chez le fournisseur mais relève d’un abonnement distinct, non souscrit. Aucun contournement n’est tenté.',
  },
  SERVER_CONTRACT_MISSING: {
    label: 'CONTRAT SERVEUR ABSENT',
    court: 'aucun contrat versionné ne la publie',
    detail:
      'La donnée serait dérivable, mais aucun contrat versionné ne la publie. La calculer ici créerait une seconde autorité.',
  },
  DECISION_PENDING: {
    label: 'DÉCISION EN ATTENTE',
    court: 'arbitrage d’autorité financière requis',
    detail:
      'Un arbitrage d’autorité financière est requis avant de pouvoir servir ce module. Le trancher seul reviendrait à inventer une hypothèse.',
  },
} as const satisfies Record<
  string,
  { readonly label: string; readonly court: string; readonly detail: string }
>;

export type AbsenceReason = keyof typeof ABSENCE_REASONS;

export interface AbsentModuleProps {
  /** Nom du module, tel qu'il apparaîtra une fois branché. */
  readonly title: string;
  /** La question à laquelle ce module répondra — elle ne change pas au branchement. */
  readonly question: string;
  readonly reason: AbsenceReason;
  /**
   * Précision propre à ce module : ce qui manque exactement, en une phrase.
   * Facultative, jamais inventée — elle vient de ce qui a été mesuré.
   */
  readonly note?: string;
}

/**
 * DIVULGATION PROGRESSIVE — mesurée, pas esthétique.
 *
 * Le module d'absence affichait en permanence sa question (≈ 60 caractères),
 * le détail de son motif (≈ 150) et sa note (≈ 120). Sur Marchés, onze modules
 * absents mettaient ainsi près de 3 500 caractères de prose à l'écran, sous
 * des cartes qui ne portent aucune donnée. Une planche devenait un mur de
 * texte gris, et le lecteur cessait de lire — donc l'information cessait
 * d'exister, alors même qu'elle était affichée.
 *
 * Ce qui reste TOUJOURS visible : le titre, la pastille du motif typé, et le
 * motif en une ligne. Ce qui passe derrière « Pourquoi ? » : la question du
 * module, l'explication complète et la note.
 *
 * RIEN N'EST SUPPRIMÉ. Tout le texte reste dans le document, atteignable au
 * clavier, lu par les technologies d'assistance, trouvable par la recherche du
 * navigateur. C'est la définition de l'aération : une interaction de plus,
 * jamais une information de moins.
 */
export function AbsentModule({ title, question, reason, note }: AbsentModuleProps) {
  const nature = ABSENCE_REASONS[reason];
  return (
    <section
      className="vx-absent"
      role="status"
      data-absence={reason}
      aria-labelledby={`vx-absent-${reason}-${title}`}
    >
      <header className="vx-absent-head">
        <h3 id={`vx-absent-${reason}-${title}`} title={question}>
          {title}
        </h3>
        <span className="vx-absent-badge">{nature.label}</span>
      </header>
      {/*
        Le CORPS ne porte aucune valeur. Le test `AbsentModule.test.tsx` refuse
        tout chiffre ici — le titre peut en contenir (« VaR 95 % »), parce
        qu'il décrit le module et non son contenu.
      */}
      <div className="vx-absent-body" data-testid="absent-body">
        <p className="vx-absent-court">{nature.court}</p>
        <details className="vx-absent-why">
          <summary>Pourquoi&nbsp;?</summary>
          <p className="vx-absent-question">{question}</p>
          <p>{nature.detail}</p>
          {note !== undefined ? <p className="vx-absent-note">{note}</p> : null}
        </details>
      </div>
    </section>
  );
}
