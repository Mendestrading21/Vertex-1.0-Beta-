/**
 * SQUELETTES DE CHARGEMENT — un par FORME, jamais un rectangle universel.
 *
 * CE QUI EXISTAIT. Deux barres génériques (`vx-dsb-skeleton`, `vx-w2-skeleton`)
 * servaient pour tout : un graphique, une table de 400 lignes, une métrique
 * d'une ligne. Le problème n'est pas esthétique — c'est que la place réservée
 * ne correspondait pas à la place occupée ensuite. Le contenu arrivait, la
 * carte changeait de hauteur, et toute la rangée se réorganisait sous les yeux
 * du lecteur. C'est exactement le défaut que la porte anti-trou de V3a mesure
 * en régime permanent ; ici il se produit au chargement.
 *
 * CE QUE CHAQUE SQUELETTE PROMET. Occuper approximativement la place de ce qui
 * arrive : un graphique réserve une surface, une table réserve des lignes, une
 * métrique réserve une ligne. La promesse n'est pas au pixel — elle est dans
 * l'ordre de grandeur, et cela suffit à supprimer le sursaut.
 *
 * ANNONCE. Un squelette n'est pas décoratif : il porte `role="status"` et
 * `aria-busy`, avec un libellé qui dit CE QUI charge. Un chargement silencieux
 * laisse un lecteur d'écran devant une page apparemment vide.
 *
 * MOUVEMENT. Un balayage lent et unique, supprimé sous `prefers-reduced-motion`.
 * Aucune pulsation : plusieurs squelettes qui clignotent en même temps
 * transforment l'attente en agitation.
 */

interface Base {
  /** Ce qui charge, en toutes lettres. « Chargement… » seul n'informe personne. */
  readonly label: string;
}

function Enveloppe({ label, children }: Base & { readonly children: React.ReactNode }) {
  return (
    <div className="vx-skel" role="status" aria-busy="true" aria-label={label}>
      {children}
    </div>
  );
}

/** Réserve la surface d'un graphique : une aire, des repères d'axe, une légende. */
export function ChartSkeleton({ label, height = 'medium' }: Base & { readonly height?: 'small' | 'medium' | 'large' }) {
  return (
    <Enveloppe label={label}>
      <div className="vx-skel-chart" data-height={height} aria-hidden="true">
        <span className="vx-skel-plot" />
        <span className="vx-skel-axis" />
      </div>
    </Enveloppe>
  );
}

/** Réserve une ligne de chiffre et sa légende. */
export function MetricSkeleton({ label }: Base) {
  return (
    <Enveloppe label={label}>
      <div className="vx-skel-metric" aria-hidden="true">
        <span className="vx-skel-line" data-width="short" />
        <span className="vx-skel-line" data-width="number" />
      </div>
    </Enveloppe>
  );
}

/**
 * Réserve `rows` lignes ET `columns` colonnes.
 *
 * Le nombre de lignes est un PARAMÈTRE parce que la page le connaît souvent :
 * une chaîne d'options en attend une douzaine, un registre plusieurs dizaines.
 * Réserver toujours trois lignes aurait recréé le sursaut qu'on cherche à
 * supprimer.
 */
export function TableSkeleton({
  label,
  rows = 6,
  columns = 4,
}: Base & { readonly rows?: number; readonly columns?: number }) {
  return (
    <Enveloppe label={label}>
      <div className="vx-skel-table" aria-hidden="true">
        {Array.from({ length: rows }, (_, ligne) => (
          <div className="vx-skel-row" key={`ligne-${String(ligne)}`}>
            {Array.from({ length: columns }, (_, colonne) => (
              <span className="vx-skel-cell" key={`cellule-${String(colonne)}`} />
            ))}
          </div>
        ))}
      </div>
    </Enveloppe>
  );
}

/** Réserve une grille de jours : six semaines de sept cases. */
export function CalendarSkeleton({ label, weeks = 5 }: Base & { readonly weeks?: number }) {
  return (
    <Enveloppe label={label}>
      <div className="vx-skel-calendar" aria-hidden="true">
        {Array.from({ length: weeks * 7 }, (_, index) => (
          <span className="vx-skel-day" key={`jour-${String(index)}`} />
        ))}
      </div>
    </Enveloppe>
  );
}

/** Réserve une mosaïque de cellules — treemap ou matrice. */
export function HeatmapSkeleton({ label, cells = 24 }: Base & { readonly cells?: number }) {
  return (
    <Enveloppe label={label}>
      <div className="vx-skel-heatmap" aria-hidden="true">
        {Array.from({ length: cells }, (_, index) => (
          <span className="vx-skel-tile" key={`tuile-${String(index)}`} />
        ))}
      </div>
    </Enveloppe>
  );
}

/** Réserve la colonne d'inspecteur : un titre, des paires libellé/valeur. */
export function InspectorSkeleton({ label, facts = 6 }: Base & { readonly facts?: number }) {
  return (
    <Enveloppe label={label}>
      <div className="vx-skel-inspector" aria-hidden="true">
        <span className="vx-skel-line" data-width="title" />
        {Array.from({ length: facts }, (_, index) => (
          <div className="vx-skel-fact" key={`fait-${String(index)}`}>
            <span className="vx-skel-line" data-width="short" />
            <span className="vx-skel-line" data-width="number" />
          </div>
        ))}
      </div>
    </Enveloppe>
  );
}
