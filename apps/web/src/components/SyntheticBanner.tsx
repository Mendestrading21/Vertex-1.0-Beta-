/**
 * Bandeau de population SYNTHETIC — visible, jamais masquable.
 *
 * Rendu dès que la population publiée par le worker vaut `SYNTHETIC` : les
 * données affichées sont générées, aucune n'est réelle ni issue d'un
 * abonnement. La distinction réel/synthétique ne partage jamais le même
 * statut visuel (règle de sécurité financière).
 */
export function SyntheticBanner({ population }: { readonly population: string | null }) {
  if (population !== 'SYNTHETIC') {
    return null;
  }
  return (
    <p className="vx-synthetic-banner" role="status" data-population="SYNTHETIC">
      <strong>DONNÉES SYNTHÉTIQUES</strong>
      <span>
        Population « SYNTHETIC » publiée par le worker : contenu généré pour le développement,
        aucune donnée réelle ni de marché.
      </span>
    </p>
  );
}
