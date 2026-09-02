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
    detail:
      'Aucune source ne publie cette donnée aujourd’hui. Ce n’est pas un défaut d’affichage : rien ne la collecte.',
  },
  SUBSCRIPTION_REQUIRED: {
    label: 'ABONNEMENT REQUIS',
    detail:
      'La donnée existe chez le fournisseur mais relève d’un abonnement distinct, non souscrit. Aucun contournement n’est tenté.',
  },
  SERVER_CONTRACT_MISSING: {
    label: 'CONTRAT SERVEUR ABSENT',
    detail:
      'La donnée serait dérivable, mais aucun contrat versionné ne la publie. La calculer ici créerait une seconde autorité.',
  },
  DECISION_PENDING: {
    label: 'DÉCISION EN ATTENTE',
    detail:
      'Un arbitrage d’autorité financière est requis avant de pouvoir servir ce module. Le trancher seul reviendrait à inventer une hypothèse.',
  },
} as const satisfies Record<string, { readonly label: string; readonly detail: string }>;

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
        <h3 id={`vx-absent-${reason}-${title}`}>{title}</h3>
        <span className="vx-absent-badge">{nature.label}</span>
      </header>
      <p className="vx-absent-question">{question}</p>
      {/*
        Le CORPS ne porte aucune valeur. Le test `AbsentModule.test.tsx` refuse
        tout chiffre ici — le titre peut en contenir (« VaR 95 % »), parce
        qu'il décrit le module et non son contenu.
      */}
      <div className="vx-absent-body" data-testid="absent-body">
        <p>{nature.detail}</p>
        {note !== undefined ? <p className="vx-absent-note">{note}</p> : null}
      </div>
    </section>
  );
}
