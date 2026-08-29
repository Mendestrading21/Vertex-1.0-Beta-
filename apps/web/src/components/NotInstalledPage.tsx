import type { PageDef } from '../app/pages.ts';

/**
 * Page « Lot non installé » — honnête par construction :
 * titre, question métier de la fiche produit, badge NON_IMPLÉMENTÉ — LOT-NN.
 * Aucune donnée fictive, aucun chiffre, aucune façade de fonctionnalité.
 */
export function NotInstalledPage({ page }: { readonly page: PageDef }) {
  const headingId = `vx-page-title-${page.key}`;
  return (
    <article className="vx-not-installed" aria-labelledby={headingId}>
      <p className="vx-badge vx-badge-warning">NON_IMPLÉMENTÉ — {page.lot}</p>
      <h1 id={headingId}>{page.title}</h1>
      <p className="vx-not-installed-question">{page.question}</p>
      <p className="vx-not-installed-note">
        Lot non installé. Cette page n'affiche aucune donnée — ni réelle, ni estimée, ni simulée.
        Elle sera livrée par le dossier {page.lot} du programme dossier par dossier.
      </p>
    </article>
  );
}
