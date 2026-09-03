import type { ReactNode } from 'react';

/**
 * La liste de faits d'un inspecteur : libellé, valeur — filetée, en argent.
 * Les valeurs arrivent déjà formées par la page (chaînes serveur, `<time>`,
 * `<code>`) ; ce composant ne formate rien et ne calcule rien.
 */
export interface SnapshotFact {
  readonly label: string;
  readonly value: ReactNode;
}

export function SnapshotFacts({
  facts,
  testId,
}: {
  readonly facts: readonly SnapshotFact[];
  readonly testId?: string;
}) {
  return (
    <dl className="vx-inspector-facts" {...(testId === undefined ? {} : { 'data-testid': testId })}>
      {facts.map((fact) => (
        <div key={fact.label}>
          <dt>{fact.label}</dt>
          <dd>{fact.value}</dd>
        </div>
      ))}
    </dl>
  );
}

/** « non publié » pour toute valeur absente ; la chaîne telle quelle sinon. */
export function publishedOr(value: string | number | null | undefined): string {
  return value === null || value === undefined || value === '' ? 'non publié' : String(value);
}
