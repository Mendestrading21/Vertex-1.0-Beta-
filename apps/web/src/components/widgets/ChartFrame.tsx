import type { ReactNode } from 'react';

import { LiveDataIndicator } from './LiveDataIndicator.tsx';
import type { LiveDataState } from './LiveDataIndicator.tsx';

/**
 * CHARTFRAME — l'anatomie commune de toute visualisation.
 *
 * CE QU'ELLE REMPLACE. `references/charts.md` décrit une anatomie en huit
 * points : titre court et question, état global et fraîcheur, surface, axes,
 * légende, provenance et méthode, table équivalente. Cette anatomie était
 * ÉCRITE À LA MAIN dans quatre pages, sous la classe `vx-chartframe` — même
 * en-tête, même liste de métadonnées, même pied, recopiés. Rien n'obligeait
 * une visualisation nouvelle à les porter, et rien ne signalait qu'il en
 * manquait un.
 *
 * CE QUE LE TYPE EXIGE MAINTENANT, ET QUE LA RECOPIE N'EXIGEAIT PAS.
 *
 *   - `question` : une visualisation répond à une question ou n'a pas lieu
 *     d'être. Sans elle, une page devient une collection de formes.
 *   - `unit` : un axe sans unité ne se lit pas. Non nullable.
 *   - `timezone` : obligatoire dès qu'une période est en jeu — une date sans
 *     fuseau est une date fausse une fois sur deux.
 *   - `dataState` : l'état de la donnée est DANS le cadre, pas à côté. Une
 *     figure périmée qui ne le dit pas est pire qu'une figure absente.
 *   - `equivalent` : l'équivalent textuel ou tabulaire est OBLIGATOIRE. C'est
 *     la règle d'accessibilité que le dépôt s'était donnée et que rien ne
 *     vérifiait ; ici, le composant ne se construit pas sans.
 *
 * CE QU'ELLE NE FAIT PAS. Elle ne dessine rien et ne connaît aucun moteur :
 * ECharts ou Lightweight Charts sont montés dans `children`, chargés par leur
 * propre route. Le cadre n'impose ni bibliothèque ni géométrie — seulement le
 * contrat qui entoure la figure.
 */

export interface ChartProvenance {
  /** Méthode et version du calcul, telles que publiées. */
  readonly method: string;
  /** Source publiée. `null` quand le contrat n'en publie pas — et c'est dit. */
  readonly source: string | null;
  /** Instant d'observation servi (ISO). */
  readonly asOf: string | null;
  /** Population couverte, verbatim (« 22 sur 24 instruments suivis »). */
  readonly population?: string | null;
  /** Exclusions déclarées. Une exclusion tue n'est pas une exclusion. */
  readonly exclusions?: string | null;
}

export interface ChartFrameProps {
  readonly id: string;
  /** Titre court. Jamais spectaculaire. */
  readonly title: string;
  /** La question à laquelle la figure répond. Obligatoire. */
  readonly question: string;
  /** Unité de l'axe de valeur. Obligatoire, non nullable. */
  readonly unit: string;
  /** Période couverte, en toutes lettres. */
  readonly period: string;
  /** Fuseau IANA d'affichage. Une date sans fuseau est une date fausse. */
  readonly timezone: string;
  readonly dataState: LiveDataState;
  readonly ageSeconds: number | null;
  readonly provenance: ChartProvenance;
  /** Rang de composition. Une seule dominante par écran. */
  readonly rank?: 'dominant' | 'support';
  /** Barre d'outils facultative — période, comparaison, overlays. */
  readonly toolbar?: ReactNode;
  /** La figure. Le cadre ne connaît pas son moteur. */
  readonly children: ReactNode;
  /**
   * Équivalent exact : table ou liste structurée. OBLIGATOIRE.
   * Un graphique sans équivalent est inaccessible, et son contenu disparaît
   * pour qui ne peut pas le voir.
   */
  readonly equivalent: ReactNode;
  /** Repliable par défaut : présent dans le DOM, pas dans le champ visuel. */
  readonly equivalentLabel?: string;
}

export function ChartFrame({
  id,
  title,
  question,
  unit,
  period,
  timezone,
  dataState,
  ageSeconds,
  provenance,
  rank = 'support',
  toolbar,
  children,
  equivalent,
  equivalentLabel = 'Voir les valeurs exactes',
}: ChartFrameProps) {
  const titreId = `${id}-title`;

  return (
    <section className="vx-cf" id={id} data-rank={rank} aria-labelledby={titreId}>
      <header className="vx-cf-head">
        <div className="vx-cf-head-text">
          {/* La question précède le titre : c'est elle qui justifie la figure. */}
          <p className="vx-cf-question">{question}</p>
          <h2 className="vx-cf-title" id={titreId}>
            {title}
          </h2>
        </div>
        <div className="vx-cf-head-side">
          <LiveDataIndicator state={dataState} ageSeconds={ageSeconds} variant="compact" />
          {toolbar === undefined ? null : <div className="vx-cf-toolbar">{toolbar}</div>}
        </div>
      </header>

      {/* Unité, période et fuseau sont AU-DESSUS de la figure, pas en note de
          bas de page : ce sont les trois choses sans lesquelles l'axe ne se
          lit pas. */}
      <p className="vx-cf-scale">
        <span className="vx-cf-unit">{unit}</span>
        <span className="vx-cf-period">{period}</span>
        <span className="vx-cf-tz">{timezone}</span>
      </p>

      <div className="vx-cf-plot">{children}</div>

      <details className="vx-cf-equivalent">
        {/* Repliée mais PRÉSENTE dans le DOM : l'équivalent reste atteignable
            au clavier et par recherche, sans occuper la surface. */}
        <summary>{equivalentLabel}</summary>
        {equivalent}
      </details>

      <footer className="vx-cf-foot">
        <dl className="vx-cf-provenance">
          <div>
            <dt>Méthode</dt>
            <dd>{provenance.method}</dd>
          </div>
          <div>
            <dt>Source</dt>
            <dd>{provenance.source ?? 'non publiée par le contrat'}</dd>
          </div>
          <div>
            <dt>Observé</dt>
            <dd>
              {provenance.asOf === null ? (
                'instant non publié'
              ) : (
                <time dateTime={provenance.asOf}>{provenance.asOf}</time>
              )}
            </dd>
          </div>
          {provenance.population === undefined || provenance.population === null ? null : (
            <div>
              <dt>Population</dt>
              <dd>{provenance.population}</dd>
            </div>
          )}
          {provenance.exclusions === undefined || provenance.exclusions === null ? null : (
            <div>
              <dt>Exclusions</dt>
              <dd>{provenance.exclusions}</dd>
            </div>
          )}
        </dl>
      </footer>
    </section>
  );
}
