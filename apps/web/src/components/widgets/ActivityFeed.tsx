import { Link } from 'react-router-dom';

import { signSymbolOf } from '../markets/marketsView.ts';
import type { SignGroup } from '../markets/marketsView.ts';
import { StatusChip } from './StatusChip.tsx';
import type { StatusChipProps } from './StatusChip.tsx';

/**
 * Journal groupé par jour — horodatages SERVIS, montants SERVIS signés.
 *
 * LE LIBELLÉ RELATIF EST REFUSÉ. « Aujourd'hui », « Hier », « Demain » n'ont de
 * sens que par rapport à une horloge ; le navigateur n'en a pas le droit
 * (`FreshnessBadge` ne lit jamais `Date.now()`). Un libellé relatif servi est
 * donc remplacé par la DATE ISO servie et le refus est DIT — le regroupement
 * lui-même reste celui de la vue, sur un champ servi non nul (par exemple
 * `provenance.last_received_at`, jamais `first_published_at` quand il vaut
 * `null`).
 *
 * VOCABULAIRE. Les libellés d'items viennent du serveur, verbatim : ce
 * composant n'en fabrique aucun, et n'emploie donc aucun terme d'instruction
 * de marché.
 */
const RELATIVE = /^\s*(aujourd|hier|demain|tout à l|à l’instant|maintenant)/i;

export interface FeedItem {
  readonly id: string;
  /** Horodatage ISO SERVI. */
  readonly timeIso: string;
  /** Heure SERVIE, avec son fuseau nommé. */
  readonly timeLabel: string;
  readonly title: string;
  /** Montant SERVI, chaîne signée. `null` = non publié. */
  readonly amount?: string | null;
  readonly sign?: SignGroup;
  readonly chips?: readonly StatusChipProps[];
  readonly to?: string;
}

export interface FeedGroup {
  /** Jour ISO SERVI. */
  readonly dayIso: string;
  /** Libellé de jour SERVI. Un libellé relatif est refusé. */
  readonly dayLabel: string;
  readonly items: readonly FeedItem[];
}

export interface ActivityFeedProps {
  readonly groups: readonly FeedGroup[];
  readonly ariaLabel: string;
  readonly emptyLabel?: string;
}

export function ActivityFeed({ groups, ariaLabel, emptyLabel }: ActivityFeedProps) {
  if (groups.length === 0) {
    return (
      <p className="vx-w2-absent" role="status">
        {emptyLabel ?? 'Aucun événement publié pour cette fenêtre.'}
      </p>
    );
  }

  return (
    <section className="vx-w2-feed" aria-label={ariaLabel}>
      {groups.map((group) => {
        const relative = RELATIVE.test(group.dayLabel);
        return (
          <section key={group.dayIso} className="vx-w2-feed-day">
            <h3 className="vx-w2-feed-day-head">
              <time dateTime={group.dayIso}>{relative ? group.dayIso : group.dayLabel}</time>
              {relative ? (
                <span data-absent="true"> — libellé relatif refusé (aucune horloge locale)</span>
              ) : null}
            </h3>
            <ul className="vx-w2-feed-list">
              {group.items.map((item) => (
                <li key={item.id} className="vx-w2-feed-item">
                  <span className="vx-w2-feed-time">
                    <time dateTime={item.timeIso}>{item.timeLabel}</time>
                  </span>
                  <span className="vx-w2-feed-title">
                    {item.to === undefined ? item.title : <Link to={item.to}>{item.title}</Link>}
                    {item.chips?.map((chip) => (
                      <StatusChip key={chip.label} {...chip} />
                    ))}
                  </span>
                  <span
                    className="vx-w2-feed-amount"
                    data-sign={item.amount === null || item.amount === undefined ? 'unknown' : (item.sign ?? 'unknown')}
                  >
                    {item.amount === null || item.amount === undefined ? (
                      <span data-absent="true">montant non publié</span>
                    ) : (
                      <>
                        {item.sign === undefined ? null : (
                          <span aria-hidden="true">{signSymbolOf(item.sign)}</span>
                        )}{' '}
                        {item.amount}
                      </>
                    )}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        );
      })}
    </section>
  );
}
