import { InspectorPanel } from '../../shell/inspector.tsx';
import { statusLabelOf, statusMarkOf } from '../calendar/calendarView.ts';
import type { CatalystView } from './catalystsView.ts';

/**
 * Inspecteur de Catalyseurs. Le contrat des douze pages (§10) en fixe le
 * contenu exact : « source, fuseau, historique, instruments liés et
 * incertitude ». Les cinq sont servis par le snapshot d'agenda et relayés
 * VERBATIM — aucun n'est dérivé, aucun n'est complété.
 *
 * « Incertitude » n'est PAS une probabilité : le contrat d'agenda n'en publie
 * aucune, et `.claude/rules/financial-safety.md` interdit d'afficher une
 * probabilité sans calibration, horizon, population et validation hors
 * échantillon. L'incertitude affichée ici est FACTUELLE : statut estimé ou
 * confirmé, existence de révisions, existence de versions en conflit,
 * fraîcheur déclarée. Ce sont des faits publiés, pas une prédiction.
 */

export interface CatalystInspectorProps {
  readonly catalyst: CatalystView;
}

export function CatalystInspector({ catalyst }: CatalystInspectorProps) {
  const { event } = catalyst;
  return (
    <InspectorPanel subject={event.ticker ?? event.eventId}>
      <dl className="vx-inspector-facts">
        <div>
          <dt>Événement</dt>
          <dd>{event.title ?? event.eventId}</dd>
        </div>

        {/* Source — §10. */}
        <div>
          <dt>Source</dt>
          <dd>
            {event.source !== null ? <code>{event.source}</code> : <em>non publiée</em>}
            {event.sourceEventId !== null ? (
              <span className="vx-inspector-hash"> · {event.sourceEventId}</span>
            ) : null}
          </dd>
        </div>
        <div>
          <dt>Droit</dt>
          <dd>{event.rights !== null ? <code>{event.rights}</code> : <em>non publié</em>}</dd>
        </div>

        {/* Fuseau — §10 : les deux chaînes serveur, jamais une conversion. */}
        <div>
          <dt>Instant (UTC)</dt>
          <dd>
            <time dateTime={event.eventTimeUtc} className="vx-num">
              {event.eventTimeUtc}
            </time>
          </dd>
        </div>
        <div>
          <dt>Heure de place</dt>
          <dd>
            {event.eventTimeLocal !== null ? (
              <>
                <span className="vx-num">{event.eventTimeLocal}</span>{' '}
                {event.exchangeTimezone !== null ? (
                  <code>{event.exchangeTimezone}</code>
                ) : (
                  <em>fuseau non publié</em>
                )}
              </>
            ) : (
              <em>non publiée</em>
            )}
          </dd>
        </div>

        {/* Incertitude — FACTUELLE, jamais une probabilité. */}
        <div>
          <dt>Statut</dt>
          <dd>
            {statusMarkOf(event.status)} {statusLabelOf(event.status)}
          </dd>
        </div>
        <div>
          <dt>Fraîcheur déclarée</dt>
          <dd>
            {event.fresh === null ? (
              <em>non publiée</em>
            ) : event.fresh ? (
              'fraîche selon le serveur'
            ) : (
              'PÉRIMÉE selon le serveur'
            )}
            {event.staleAfter !== null ? (
              <span className="vx-inspector-hash"> · péremption {event.staleAfter}</span>
            ) : null}
          </dd>
        </div>
        <div>
          <dt>Qualité</dt>
          <dd>{event.quality !== null ? <code>{event.quality}</code> : <em>non publiée</em>}</dd>
        </div>
      </dl>

      {/* Historique — §10 : révisions et conflits, avec valeurs antérieures. */}
      <section className="vx-inspector-block" aria-labelledby="vx-inspector-history">
        <h3 id="vx-inspector-history">Historique publié</h3>
        {event.revisions.length === 0 ? (
          <p className="vx-cell-absent">
            {event.revised
              ? 'Marqué révisé, mais le détail des révisions n’est pas publié.'
              : 'Aucune révision publiée.'}
          </p>
        ) : (
          <ol className="vx-inspector-history">
            {/*
              La clé compose les TROIS champs publiés d'une révision. La
              source ne publie aucun identifiant de révision : composer sur le
              contenu est la seule identité disponible. Deux révisions
              strictement identiques sont un doublon de la source, pas un cas
              à masquer — elles resteront donc toutes deux affichées.
            */}
            {event.revisions.map((revision) => (
              <li
                key={[
                  revision.revisedAt ?? 'sans-date',
                  revision.previousStatus ?? 'sans-statut',
                  revision.previousEventTimeUtc ?? 'sans-instant',
                ].join('|')}
              >
                {revision.revisedAt !== null ? (
                  <time dateTime={revision.revisedAt}>{revision.revisedAt}</time>
                ) : (
                  <em>date de révision non publiée</em>
                )}
                {revision.previousStatus !== null ? (
                  <span> · statut antérieur <code>{revision.previousStatus}</code></span>
                ) : null}
                {revision.previousEventTimeUtc !== null ? (
                  <span>
                    {' '}
                    · instant antérieur{' '}
                    <time dateTime={revision.previousEventTimeUtc} className="vx-num">
                      {revision.previousEventTimeUtc}
                    </time>
                  </span>
                ) : null}
              </li>
            ))}
          </ol>
        )}

        {event.conflictingVersions.length > 0 ? (
          <p className="vx-inspector-note" data-testid="inspector-conflict">
            {event.conflictingVersions.length} version(s) en conflit publiées par la source. Aucune
            n’est choisie ici : le conflit est montré, pas arbitré.
          </p>
        ) : null}
      </section>

      {/* Instruments liés — §10. */}
      <section className="vx-inspector-block" aria-labelledby="vx-inspector-links">
        <h3 id="vx-inspector-links">Éléments liés</h3>
        {catalyst.theses.length === 0 && catalyst.positions.length === 0 ? (
          <p className="vx-cell-absent">Aucun lien publié.</p>
        ) : (
          <ul className="vx-inspector-links">
            {catalyst.theses.map((thesis, index) => (
              <li key={`these-${thesis.thesisId ?? index}`}>
                Thèse :{' '}
                {thesis.title ?? (
                  <span className="vx-cell-absent">titre non renseigné</span>
                )}
                {thesis.knownInQueue ? null : (
                  <span className="vx-cell-absent"> (absente du snapshot de revue)</span>
                )}
              </li>
            ))}
            {catalyst.positions.map((identifier) => (
              <li key={`position-${identifier}`}>
                Position du registre manuel <code>#{identifier}</code>
              </li>
            ))}
          </ul>
        )}
        {event.context.links.length > 0 ? (
          <ul className="vx-inspector-links">
            {event.context.links.map((link) => (
              <li key={`${link.rel}-${link.resource}`}>
                <code>{link.rel}</code> → <code>{link.resource}</code>
              </li>
            ))}
          </ul>
        ) : null}
      </section>

      <p className="vx-inspector-note">
        Aucune probabilité n’est affichée : le contrat d’agenda n’en publie aucune, et une
        probabilité sans calibration, horizon, population ni validation hors échantillon est
        interdite.
      </p>
    </InspectorPanel>
  );
}
