import type { ReactNode } from 'react';

/**
 * LA carte. Une seule, pour les douze destinations.
 *
 * POURQUOI CE COMPOSANT EXISTE — et c'est mesuré, pas ressenti.
 * `docs/05-design/REFONTE_TITANIUM_LEDGER.md` le chiffre : `global.css`
 * déclare 443 classes `.vx-*`, dont 89 seulement sont atteintes par la couche
 * thématique Titanium Ledger, à travers 15 listes de sélecteurs énumérées à la
 * main :
 *
 *     .vx-chartframe,
 *     .vx-today-primary,
 *     .vx-snapshot-rail,
 *     …                     (15 blocs de ce genre)
 *
 * Un module ajouté à une page n'hérite donc de RIEN. Il faut penser à
 * l'inscrire dans les 15 listes, sinon il tombe silencieusement hors du thème.
 * « Le même style sur toutes les pages » n'était pas seulement absent : il
 * était impossible à garantir, et aucune porte ne le voyait. Le LOT V2 en a
 * donné la preuve la plus nette — la largeur du rail était déclarée TROIS fois,
 * et changer la déclaration de base ne changeait rien à l'écran.
 *
 * CE QUE LA PRIMITIVE GARANTIT. Une surface, une anatomie, un jeu d'espaces.
 * Le style vient de `.vx-card` ; une page choisit un RANG, jamais une
 * apparence.
 *
 * CE QU'ELLE NE FAIT PAS. Elle ne calcule rien, ne formate aucune valeur et
 * n'invente aucun libellé. Le pied de provenance reçoit ce que la page a reçu
 * du serveur.
 */

/**
 * Le rang décide de la lumière, pas la page.
 *
 * `dominant` porte la tranche métallique et l'ombre de panneau. Le contrat
 * canonique est explicite : « une lumière dominante maximum par carte, deux
 * par écran hors rouge/vert ». Une porte (`one-dominant-per-page.test.ts`)
 * compte les porteurs et refuse le second.
 */
export type CardRank = 'dominant' | 'default' | 'quiet';

export interface CardProps {
  /** Micro-libellé au-dessus du titre. Court, il nomme la NATURE du module. */
  readonly kicker?: string;
  readonly title: string;
  /** Identifiant du titre, pour `aria-labelledby`. Obligatoire dès qu'une page en a deux. */
  readonly titleId?: string;
  /** Contenu aligné à droite de la tête : compte, filtre, badge d'état. */
  readonly aside?: ReactNode;
  readonly rank?: CardRank;
  /**
   * Pied de PROVENANCE : source, `as_of`, fraîcheur, méthode. Il vit au bas de
   * la carte qui porte la valeur — jamais dans un bandeau lointain, où le
   * lecteur ne saurait plus à quelle donnée il se rapporte.
   */
  readonly footer?: ReactNode;
  readonly children: ReactNode;
  /** Classe de composition uniquement (placement en grille). Jamais d'apparence. */
  readonly className?: string;
}

export function Card({
  kicker,
  title,
  titleId,
  aside,
  rank = 'default',
  footer,
  children,
  className,
}: CardProps) {
  return (
    <section
      className={className === undefined ? 'vx-card' : `vx-card ${className}`}
      data-rank={rank}
      {...(titleId === undefined ? {} : { 'aria-labelledby': titleId })}
    >
      <header className="vx-card-head">
        <div className="vx-card-heading">
          {kicker === undefined ? null : <p className="vx-card-kicker">{kicker}</p>}
          <h2 {...(titleId === undefined ? {} : { id: titleId })}>{title}</h2>
        </div>
        {aside === undefined ? null : <div className="vx-card-aside">{aside}</div>}
      </header>
      <div className="vx-card-body">{children}</div>
      {footer === undefined ? null : <footer className="vx-card-foot">{footer}</footer>}
    </section>
  );
}
