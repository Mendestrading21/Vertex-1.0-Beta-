import { useEffect, useId, useRef, useState } from 'react';
import type { KeyboardEvent as ReactKeyboardEvent } from 'react';

import type { AttentionItem } from '../api/client.ts';
import { FreshnessBadge } from '../components/FreshnessBadge.tsx';

/**
 * Visuel dominant de la page Aujourd'hui : la file d'attention.
 *
 * Liste verticale des items publiés par le worker (le serveur en publie au
 * plus 15 ; la liste rend EXACTEMENT ce qui est reçu). Chaque ligne porte le
 * titre, les sources, l'âge AU MOMENT DU SNAPSHOT (différence entre deux
 * horodatages serveur — `as_of` du snapshot et `first_published_at` de la
 * provenance ; jamais l'horloge du navigateur), au plus 3 raisons de
 * pertinence en badges texte et le marqueur SYNTHÉTIQUE par item.
 *
 * Le détail s'ouvre dans un panneau latéral accessible (dialog modal, focus
 * piégé, Échap pour fermer, focus restitué au déclencheur) et montre la
 * provenance complète telle que publiée.
 */

// -- lecture défensive du bloc de provenance (relayé verbatim, non typé) ----

function provString(provenance: Record<string, unknown>, key: string): string | null {
  const value = provenance[key];
  return typeof value === 'string' && value !== '' ? value : null;
}

function provStringList(provenance: Record<string, unknown>, key: string): readonly string[] {
  const value = provenance[key];
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter((entry): entry is string => typeof entry === 'string');
}

/**
 * Âge d'un événement au moment du snapshot : différence entre deux
 * horodatages FOURNIS PAR LE SERVEUR. `null` si l'un des deux manque ou ne se
 * lit pas — l'absence reste une absence, jamais un zéro.
 */
export function snapshotAgeSeconds(asOf: string | null, eventTime: string | null): number | null {
  if (asOf === null || eventTime === null) {
    return null;
  }
  const asOfMs = Date.parse(asOf);
  const eventMs = Date.parse(eventTime);
  if (Number.isNaN(asOfMs) || Number.isNaN(eventMs)) {
    return null;
  }
  return Math.floor((asOfMs - eventMs) / 1000);
}

// -- panneau latéral de détail ----------------------------------------------

function AbsentValue({ label }: { readonly label: string }) {
  return (
    // `role="img"` obligatoire : sur un <span> sans rôle (rôle implicite
    // `generic`), ARIA INTERDIT `aria-label` et les lecteurs d'écran
    // ignorent le libellé — le motif de l'absence ne serait pas annoncé.
    // Aligné sur OptionChainTable.tsx, qui portait déjà le rôle correct.
    <span className="vx-cell-absent" role="img" aria-label={label}>
      —
    </span>
  );
}

interface SideSheetProps {
  readonly item: AttentionItem;
  readonly asOf: string | null;
  readonly onClose: () => void;
}

function SideSheet({ item, asOf, onClose }: SideSheetProps) {
  const sheetRef = useRef<HTMLDivElement | null>(null);
  const titleId = useId();

  useEffect(() => {
    const sheet = sheetRef.current;
    if (sheet !== null) {
      const first = sheet.querySelector<HTMLElement>('button');
      first?.focus();
    }
  }, []);

  const handleKeyDown = (event: ReactKeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'Escape') {
      event.stopPropagation();
      onClose();
      return;
    }
    if (event.key !== 'Tab') {
      return;
    }
    const sheet = sheetRef.current;
    if (sheet === null) {
      return;
    }
    const focusables = Array.from(
      sheet.querySelectorAll<HTMLElement>('button, a[href], [tabindex]:not([tabindex="-1"])'),
    );
    if (focusables.length === 0) {
      return;
    }
    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last?.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first?.focus();
    }
  };

  const provenance = item.provenance;
  const memberIds = provStringList(provenance, 'member_event_ids');
  const clusterId = provString(provenance, 'cluster_id');
  const instrumentRef = provString(provenance, 'instrument_ref');
  const firstPublishedAt = provString(provenance, 'first_published_at');
  const lastReceivedAt = provString(provenance, 'last_received_at');

  return (
    <div
      ref={sheetRef}
      className="vx-sheet"
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      onKeyDown={handleKeyDown}
    >
      <div className="vx-sheet-head">
        <h2 id={titleId}>{item.title}</h2>
        <button type="button" className="vx-sheet-close" onClick={onClose}>
          Fermer
        </button>
      </div>
      {item.synthetic ? <p className="vx-badge vx-badge-synthetic">SYNTHÉTIQUE</p> : null}
      <dl className="vx-sheet-facts">
        <div>
          <dt>Item</dt>
          <dd>
            <code>{item.id}</code>
          </dd>
        </div>
        <div>
          <dt>Cluster</dt>
          <dd>{clusterId === null ? <AbsentValue label="cluster inconnu" /> : <code>{clusterId}</code>}</dd>
        </div>
        <div>
          <dt>Événements membres</dt>
          <dd>
            {memberIds.length === 0 ? (
              <AbsentValue label="aucun événement membre publié" />
            ) : (
              <ul className="vx-sheet-list">
                {memberIds.map((memberId) => (
                  <li key={memberId}>
                    <code>{memberId}</code>
                  </li>
                ))}
              </ul>
            )}
          </dd>
        </div>
        <div>
          <dt>Sources</dt>
          <dd>{item.sources.join(', ')}</dd>
        </div>
        <div>
          <dt>Droits</dt>
          <dd>{item.rights.join(', ')}</dd>
        </div>
        <div>
          <dt>Première publication (UTC)</dt>
          <dd>
            {firstPublishedAt === null ? (
              <AbsentValue label="première publication inconnue" />
            ) : (
              <time dateTime={firstPublishedAt}>{firstPublishedAt}</time>
            )}
          </dd>
        </div>
        <div>
          <dt>Dernière réception (UTC)</dt>
          <dd>
            {lastReceivedAt === null ? (
              <AbsentValue label="dernière réception inconnue" />
            ) : (
              <time dateTime={lastReceivedAt}>{lastReceivedAt}</time>
            )}
          </dd>
        </div>
        <div>
          <dt>Instrument</dt>
          <dd>
            {instrumentRef === null ? (
              <AbsentValue label="aucun instrument associé" />
            ) : (
              <code>{instrumentRef}</code>
            )}
          </dd>
        </div>
        <div>
          <dt>Snapshot as_of (UTC)</dt>
          <dd>
            {asOf === null ? <AbsentValue label="as_of absent" /> : <time dateTime={asOf}>{asOf}</time>}
          </dd>
        </div>
      </dl>
    </div>
  );
}

// -- file d'attention --------------------------------------------------------

export interface AttentionQueueProps {
  readonly items: readonly AttentionItem[];
  readonly asOf: string | null;
}

export function AttentionQueue({ items, asOf }: AttentionQueueProps) {
  const [openItemId, setOpenItemId] = useState<string | null>(null);
  const triggerRef = useRef<HTMLButtonElement | null>(null);

  const openItem = items.find((item) => item.id === openItemId) ?? null;

  function close(): void {
    setOpenItemId(null);
    triggerRef.current?.focus();
    triggerRef.current = null;
  }

  return (
    <div className="vx-queue">
      <ol className="vx-queue-list">
        {items.map((item) => {
          const firstPublishedAt = provString(item.provenance, 'first_published_at');
          return (
            <li key={item.id} className="vx-queue-item">
              <div className="vx-queue-item-main">
                <button
                  type="button"
                  className="vx-queue-title"
                  aria-haspopup="dialog"
                  aria-expanded={openItemId === item.id}
                  onClick={(event) => {
                    triggerRef.current = event.currentTarget;
                    setOpenItemId(item.id);
                  }}
                >
                  {item.title}
                </button>
                <p className="vx-queue-sources">{item.sources.join(', ')}</p>
              </div>
              <div className="vx-queue-item-meta">
                {item.synthetic ? (
                  <span className="vx-badge vx-badge-synthetic">SYNTHÉTIQUE</span>
                ) : null}
                <FreshnessBadge
                  ageSeconds={snapshotAgeSeconds(asOf, firstPublishedAt)}
                  sourceLabel="au snapshot"
                />
                {item.relevance_reasons.slice(0, 3).map((reason) => (
                  <span key={reason} className="vx-badge vx-badge-reason">
                    {reason}
                  </span>
                ))}
              </div>
            </li>
          );
        })}
      </ol>
      {openItem !== null ? <SideSheet item={openItem} asOf={asOf} onClose={close} /> : null}
    </div>
  );
}
