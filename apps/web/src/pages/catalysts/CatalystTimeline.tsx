import {
  CATEGORY_LABELS,
  VERSION_STATE_CONFLICTING,
  categoryLabelOf,
  statusLabelOf,
  statusMarkOf,
} from '../calendar/calendarView.ts';
import { LINK_LABELS } from './catalystsView.ts';
import type { CatalystView } from './catalystsView.ts';

/**
 * Visuel dominant de Catalyseurs : la timeline des événements reliés à une
 * thèse ou à une position.
 *
 * Contrat §10 — widgets attendus : importance, statut, révisions, conflits et
 * fenêtre. Les cinq sont servis par le snapshot d'agenda et relayés VERBATIM.
 *
 * « consensus fourni », sixième widget nommé par le contrat, N'EST PAS
 * affiché : aucun champ de consensus n'existe dans le contrat d'agenda
 * publié. Le dessiner supposerait de l'inventer — l'article 17 de la
 * Constitution l'interdit. Son absence est écrite en clair sous la timeline.
 *
 * L'ordre est celui du serveur. Aucun tri, aucun regroupement implicite,
 * aucune couleur porteuse d'information seule : chaque statut porte aussi sa
 * marque textuelle et son libellé.
 */

export interface CatalystTimelineProps {
  readonly catalysts: readonly CatalystView[];
  readonly unlinkedCount: number;
  /** Identifiant de l'événement ouvert dans l'inspecteur, `null` si aucun. */
  readonly selectedEventId: string | null;
  readonly onSelect: (eventId: string) => void;
}

export function CatalystTimeline({
  catalysts,
  unlinkedCount,
  selectedEventId,
  onSelect,
}: CatalystTimelineProps) {
  return (
    <section
      className="vx-cat-timeline"
      /*
        LA DOMINANTE DE CATALYSEURS. La page demande « quels événements
        vérifiés peuvent modifier la thèse et quand ? » : c'est cette timeline
        qui répond. La file de revues portait la dominante ; elle vit pourtant
        plus bas et répond à une autre question (« quelles thèses doivent être
        revues »). Une dominante mal placée ne se voit dans aucun test — elle
        se voit à la question que la page pose.
      */
      data-rank="dominant"
      aria-labelledby="vx-cat-timeline-title"
    >
      <h2 id="vx-cat-timeline-title">
        Timeline — {catalysts.length} événement(s) relié(s)
      </h2>
      <p className="vx-cat-scope" role="note">
        Ordre publié par le worker, conservé tel quel. Seuls les événements que le snapshot relie à
        une thèse déclarée ou à une position du registre manuel figurent ici ;{' '}
        <strong data-testid="cat-unlinked">{unlinkedCount}</strong> événement(s) servi(s) ne sont
        reliés à aucune des deux et restent sur Calendrier — ils ne sont ni masqués ni comptés
        comme catalyseurs.
      </p>

      {catalysts.length === 0 ? (
        <p className="vx-cell-absent" data-testid="cat-empty">
          Aucun événement servi n'est relié à une thèse ou à une position. C'est un état réel du
          snapshot, pas un défaut d'affichage.
        </p>
      ) : (
        /*
          LA RÉGION DÉFILANTE EST UNE ENVELOPPE, PAS LA LISTE.
          Première version : `role="region"` posé directement sur le `<ol>`.
          Un rôle explicite REMPLACE le rôle implicite : la liste cessait d'être
          une liste, ses sept `<li>` n'étaient plus contenus dans une `<ul>` ou
          `<ol>`, et axe l'a dit — violation `listitem`, impact « serious »,
          sur un seuil déclaré à zéro. La borne de hauteur ne valait pas ça.
          L'enveloppe porte donc la région et le `tabIndex` ; la liste reste
          une liste.
        */
        <div
          className="vx-cat-list-scroll"
          tabIndex={0}
          role="region"
          aria-label="Timeline des catalyseurs, région défilante"
        >
        <ol className="vx-cat-list" data-testid="cat-list">
          {catalysts.map(({ event, links, theses, positions }) => (
            <li
              key={event.eventId}
              className="vx-cat-item"
              data-testid={`cat-${event.eventId}`}
              data-selected={event.eventId === selectedEventId ? 'true' : undefined}
            >
              <div className="vx-cat-when">
                <time dateTime={event.eventTimeUtc} className="vx-num">
                  {event.eventTimeUtc}
                </time>
                {event.eventTimeLocal !== null && event.exchangeTimezone !== null ? (
                  <span className="vx-cat-local">
                    {event.eventTimeLocal} ({event.exchangeTimezone})
                  </span>
                ) : (
                  <span className="vx-cell-absent">fuseau de place non publié</span>
                )}
              </div>

              <div className="vx-cat-what">
                {/*
                  Ouvrir l'inspecteur est l'action PRIMAIRE de la page, et la
                  seule. C'est un bouton, pas une ligne cliquable : le clavier
                  doit l'atteindre dans l'ordre du document et `aria-pressed`
                  dit lequel est ouvert.
                */}
                <button
                  type="button"
                  className="vx-cat-open"
                  aria-pressed={event.eventId === selectedEventId}
                  onClick={() => onSelect(event.eventId)}
                >
                  <span className="vx-cat-title">{event.title ?? event.eventId}</span>
                </button>
                <span className="vx-cat-tags">
                  <span className="vx-badge" data-category={event.category}>
                    {categoryLabelOf(event.category)}
                  </span>
                  {/* Statut : marque textuelle + libellé, jamais la couleur seule. */}
                  <span className="vx-badge" data-status={event.status}>
                    {statusMarkOf(event.status)} {statusLabelOf(event.status)}
                  </span>
                  {event.ticker !== null ? <code>{event.ticker}</code> : null}
                  {event.synthetic ? (
                    <span className="vx-badge-synthetic">SYNTHÉTIQUE</span>
                  ) : null}
                </span>
              </div>

              <div className="vx-cat-why">
                <span className="vx-cat-links">
                  {links.map((link) => (
                    <span key={link} className="vx-badge" data-link={link}>
                      {LINK_LABELS[link]}
                    </span>
                  ))}
                </span>

                {theses.length > 0 ? (
                  <ul className="vx-cat-theses">
                    {theses.map((thesis, index) => (
                      <li key={`${event.eventId}-${thesis.thesisId ?? index}`}>
                        <span className="vx-cat-thesis-title">{thesis.title ?? '—'}</span>
                        {thesis.status !== null ? <code>{thesis.status}</code> : null}
                        {thesis.knownInQueue ? (
                          <>
                            {thesis.isDue ? (
                              <span className="vx-badge vx-badge-warning">revue due</span>
                            ) : null}
                            {thesis.hasNewInformation ? (
                              <span
                                className="vx-badge vx-badge-warning"
                                data-testid={`cat-new-info-${thesis.thesisId ?? index}`}
                              >
                                nouvelle information
                              </span>
                            ) : null}
                            {thesis.effectiveReviewDueAt !== null ? (
                              <span className="vx-cat-due">
                                échéance :{' '}
                                <time dateTime={thesis.effectiveReviewDueAt}>
                                  {thesis.effectiveReviewDueAt}
                                </time>
                              </span>
                            ) : null}
                          </>
                        ) : (
                          // L'événement nomme une thèse que la file de revue
                          // publiée ne contient pas. Les deux snapshots sont
                          // indépendants : la divergence est DITE, pas comblée.
                          <span className="vx-cell-absent" data-testid="cat-thesis-unknown">
                            thèse absente du snapshot de revue — état non affiché
                          </span>
                        )}
                      </li>
                    ))}
                  </ul>
                ) : null}

                {positions.length > 0 ? (
                  <p className="vx-cat-positions">
                    Positions du registre manuel concernées :{' '}
                    {positions.map((identifier) => (
                      <code key={identifier}>#{identifier}</code>
                    ))}
                  </p>
                ) : null}
              </div>

              <div className="vx-cat-quality">
                {/* Importance : relayée, jamais recalculée ni agrégée. */}
                {event.importance.code !== null ? (
                  <span className="vx-cat-importance">
                    importance <code>{event.importance.code}</code>
                    {event.importance.ruleVersion !== null ? (
                      <> (règle v{event.importance.ruleVersion})</>
                    ) : null}
                  </span>
                ) : (
                  <span className="vx-cell-absent">importance non publiée</span>
                )}
                {/*
                  Le drapeau `revised` et la liste `revisions` sont DEUX
                  champs distincts du snapshot, et ils peuvent diverger : le
                  worker peut marquer un événement révisé sans publier le
                  détail. Écrire « révisé — 0 révision(s) » relayait la
                  divergence en la rendant illisible. Les deux cas sont
                  désormais nommés séparément, et aucun des deux n'est masqué.
                */}
                {event.revised ? (
                  <span className="vx-badge vx-badge-warning" data-testid={`cat-revised-${event.eventId}`}>
                    {event.revisions.length > 0
                      ? `révisé — ${event.revisions.length} révision(s)`
                      : 'révisé — détail des révisions non publié'}
                  </span>
                ) : null}
                {event.versionState === VERSION_STATE_CONFLICTING ? (
                  <span
                    className="vx-badge vx-badge-warning"
                    data-testid={`cat-conflict-${event.eventId}`}
                  >
                    versions en conflit ({event.conflictingVersions.length})
                  </span>
                ) : null}
                <span className="vx-cat-provenance">
                  source {event.source !== null ? <code>{event.source}</code> : '—'} · droit{' '}
                  {event.rights !== null ? <code>{event.rights}</code> : '—'} · qualité{' '}
                  {event.quality !== null ? <code>{event.quality}</code> : '—'}
                </span>
              </div>
            </li>
          ))}
        </ol>
        </div>
      )}

      <p className="vx-cat-missing" role="note" data-testid="cat-missing-widget">
        Le contrat de cette page nomme aussi un widget « consensus fourni ». Aucun champ de
        consensus n'existe dans le contrat d'agenda publié : il est donc ABSENT, pas approximé.
        Catégories couvertes par le libellé : {Object.keys(CATEGORY_LABELS).length}.
      </p>
    </section>
  );
}
