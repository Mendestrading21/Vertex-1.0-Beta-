import type { FreshnessPolicyView } from '../api/client.ts';

/**
 * Badge de fraîcheur — un âge SERVI, et l'ÉCHELLE SERVIE qui le juge.
 *
 * Ce composant ne lit jamais `Date.now()` ni `new Date()` : il formate deux
 * durées déjà mesurées ailleurs.
 *
 * POURQUOI LE BUDGET. « il y a 3 j » ne dit rien tout seul. Trois jours sur
 * une barre quotidienne de séance fermée, c'est normal ; trois jours sur une
 * cotation, c'est une donnée morte. L'API publie depuis le début l'échelle qui
 * tranche — `freshness_policy = {budget_seconds, kind, version}`, servie par
 * DOUZE routes — en écrivant noir sur blanc son intention : « le client pose
 * `age_seconds` sur cette échelle et n'invente ni TTL ni ratio ; publier le
 * budget évite un second registre recopié côté interface ». AUCUN fichier
 * d'interface ne la lisait. Le contrat existait, la moitié cliente n'avait
 * jamais été écrite, et le lecteur voyait un âge sans savoir de quoi il était
 * l'âge.
 *
 * POURQUOI PAS UNE JAUGE. `LinearGauge` exigerait une POSITION SERVIE en
 * pourcentage (`WIDGET_LIBRARY.md` : « le navigateur ne calcule ni
 * pourcentage, ni seuil, ni position du marqueur »). Le serveur publie deux
 * durées, pas un ratio : dessiner un remplissage obligerait à calculer
 * `âge / budget` ici. Les deux durées sont donc AFFICHÉES, jamais divisées. Le
 * jour où le serveur publiera la position, la jauge pourra la prendre.
 *
 * Un budget absent n'est pas un budget infini : une famille sans TTL au
 * registre publie `null` (matrice de capacités). L'échelle est alors tue, pas
 * inventée.
 */

export interface FreshnessBadgeProps {
  /**
   * Âge de la donnée en secondes, fourni par l'API.
   * `null` = âge inconnu (distinct d'un âge invalide ou de zéro).
   */
  readonly ageSeconds: number | null;
  /** Étiquette de source facultative (ex. « IBKR différé »). */
  readonly sourceLabel?: string;
  /**
   * `budget_seconds` SERVI de `freshness_policy`. `null`/absent = la famille
   * n'a pas de TTL au registre ; l'échelle n'est alors PAS affichée, et
   * surtout pas remplacée par une valeur par défaut.
   */
  readonly budgetSeconds?: number | null;
  /** `kind` SERVI de la politique (`daily_bar`, `news_attention`…). */
  readonly policyKind?: string | null;
  /** `version` SERVIE de la politique : un TTL qui change monte de version. */
  readonly policyVersion?: string | null;
}

/** Formatage déterministe d'un âge en secondes. Exporté pour les tests. */
export function formatAge(ageSeconds: number | null): string {
  if (ageSeconds === null) {
    return 'âge inconnu';
  }
  if (Number.isNaN(ageSeconds) || !Number.isFinite(ageSeconds) || ageSeconds < 0) {
    return 'âge invalide';
  }
  const seconds = Math.floor(ageSeconds);
  if (seconds < 60) {
    return `il y a ${seconds} s`;
  }
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    return `il y a ${minutes} min`;
  }
  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    return `il y a ${hours} h`;
  }
  const days = Math.floor(hours / 24);
  return `il y a ${days} j`;
}

/**
 * Le budget servi, mis en forme comme une DURÉE et non comme un instant :
 * « budget 1 j », pas « il y a 1 j ». Les deux nombres sont du même ordre,
 * c'est justement pourquoi ils doivent se lire différemment.
 */
export function formatBudget(budgetSeconds: number | null | undefined): string | null {
  if (budgetSeconds === null || budgetSeconds === undefined) {
    return null;
  }
  if (!Number.isFinite(budgetSeconds) || budgetSeconds <= 0) {
    // Un budget nul ou négatif est refusé à la frontière serveur (« la forme
    // qu'une absence prendrait si elle était convertie en zéro »). S'il
    // arrive ici, il est TU : afficher « budget 0 s » ferait lire toute donnée
    // comme périmée.
    return null;
  }
  const age = formatAge(budgetSeconds);
  return age.startsWith('il y a ') ? `budget ${age.slice('il y a '.length)}` : null;
}

/**
 * Extrait les trois props d'échelle d'une `freshness_policy` SERVIE.
 *
 * Un seul endroit connaît les noms de champs du contrat ; les douze sites
 * d'appel écrivent `{...policyProps(data.freshness_policy)}` et rien d'autre.
 * Une politique absente rend un objet VIDE — les props ne sont donc pas
 * posées, et le badge ne peut pas les confondre avec un budget nul.
 */
export function policyProps(
  policy: FreshnessPolicyView | null | undefined,
): Pick<FreshnessBadgeProps, 'budgetSeconds' | 'policyKind' | 'policyVersion'> {
  if (policy === null || policy === undefined) {
    return {};
  }
  return {
    budgetSeconds: policy.budget_seconds,
    policyKind: policy.kind,
    policyVersion: policy.version,
  };
}

export function FreshnessBadge({
  ageSeconds,
  sourceLabel,
  budgetSeconds = null,
  policyKind = null,
  policyVersion = null,
}: FreshnessBadgeProps) {
  const budget = formatBudget(budgetSeconds);
  // La politique complète reste ATTEIGNABLE sans encombrer la ligne : c'est
  // la désaturation du texte, pas sa suppression.
  const politique =
    budget === null
      ? null
      : [budget, policyKind, policyVersion === null ? null : `politique ${policyVersion}`]
          .filter((part): part is string => part !== null && part !== '')
          .join(' · ');

  return (
    <span className="vx-freshness">
      <span className="vx-freshness-age">{formatAge(ageSeconds)}</span>
      {budget === null ? null : (
        <span
          className="vx-freshness-budget"
          {...(politique === null ? {} : { title: politique })}
        >
          {budget}
        </span>
      )}
      {sourceLabel !== undefined ? (
        <span className="vx-freshness-source">— {sourceLabel}</span>
      ) : null}
    </span>
  );
}
