import { useCallback, useEffect, useId, useRef, useState } from 'react';
import type { ReactNode } from 'react';

import type { AttentionItem } from '../api/client.ts';
import { AbsentCell } from '../components/absence.tsx';
import { FreshnessBadge } from '../components/FreshnessBadge.tsx';
import { InspectorPanel } from '../shell/inspector.tsx';

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

interface SideSheetProps {
  readonly item: AttentionItem;
  readonly asOf: string | null;
  readonly onClose: () => void;
}

/**
 * LOT-13 : ce panneau était un DIALOGUE MODAL (`role="dialog"`,
 * `aria-modal="true"`, piège de focus). Il est devenu un panneau de
 * l'inspecteur du shell, comme l'anatomie canonique le décrit — « le shell
 * reste identique sur les douze destinations », et l'inspecteur en fait
 * partie.
 *
 * LE PIÈGE DE FOCUS A ÉTÉ RETIRÉ, ET C'EST LA CORRECTION, PAS UN
 * AFFAIBLISSEMENT. Un piège n'est correct que pour un dialogue modal, où le
 * reste de la page est justement inerte. Sur un panneau NON modal, piéger le
 * clavier enfermerait l'utilisateur hors de sa propre page : ce serait un
 * défaut d'accessibilité, pas une protection. Les tests qui l'asséraient sont
 * remplacés par l'assertion correcte — depuis le dernier élément du panneau,
 * la tabulation CONTINUE vers le reste de la page.
 *
 * Ce qui est CONSERVÉ, parce que ces propriétés valent pour les deux motifs :
 * le focus entre dans le panneau à l'ouverture, `Échap` le referme, et le
 * focus revient au déclencheur.
 */
function SideSheet({ item, asOf, onClose }: SideSheetProps) {
  const sheetRef = useRef<HTMLDivElement | null>(null);
  const titleId = useId();
  const [sheetNode, setSheetNode] = useState<HTMLDivElement | null>(null);

  /**
   * Le focus entre dans le panneau DÈS QUE son nœud existe.
   *
   * Un `useEffect([])` ne suffit pas ici : le panneau est monté par PORTAIL,
   * et le nœud d'accueil n'est résolu qu'après un premier rendu. À ce
   * moment-là `sheetRef.current` est encore `null`, l'effet ne trouve aucun
   * bouton, et le focus reste sur le déclencheur — c'est exactement le défaut
   * que la conversion a introduit et que le test a rattrapé. Une ref de
   * rappel, elle, se déclenche à l'attachement réel du nœud.
   */
  const attacherPanneau = useCallback((node: HTMLDivElement | null) => {
    sheetRef.current = node;
    setSheetNode(node);
    node?.querySelector<HTMLElement>('button')?.focus();
  }, []);

  // `Échap` referme le panneau depuis n'importe quel élément qu'il contient.
  //
  // L'écouteur est attaché NATIVEMENT au panneau plutôt que posé en
  // `onKeyDown` sur le conteneur : sans `role="dialog"`, ce conteneur est un
  // élément statique, et y accrocher un gestionnaire clavier est justement ce
  // que la règle d'accessibilité du linter refuse. Un écouteur natif sur le
  // nœud réel couvre le même besoin sans prétendre que le div est interactif.
  useEffect(() => {
    if (sheetNode === null) {
      return;
    }
    function onKeyDown(event: KeyboardEvent): void {
      if (event.key === 'Escape') {
        event.stopPropagation();
        onClose();
      }
    }
    sheetNode.addEventListener('keydown', onKeyDown);
    return () => {
      sheetNode.removeEventListener('keydown', onKeyDown);
    };
  }, [sheetNode, onClose]);

  const provenance = item.provenance;
  const memberIds = provStringList(provenance, 'member_event_ids');
  const clusterId = provString(provenance, 'cluster_id');
  const instrumentRef = provString(provenance, 'instrument_ref');
  const firstPublishedAt = provString(provenance, 'first_published_at');
  const lastReceivedAt = provString(provenance, 'last_received_at');

  return (
    <InspectorPanel subject={item.title}>
      <div ref={attacherPanneau} className="vx-sheet">
        <div className="vx-sheet-head">
          <h3 id={titleId} className="vx-visually-hidden">
            {item.title}
          </h3>
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
          <dd>{clusterId === null ? <AbsentCell quoi="cluster" nature="not_published" reason={null} /> : <code>{clusterId}</code>}</dd>
        </div>
        <div>
          <dt>Événements membres</dt>
          <dd>
            {memberIds.length === 0 ? (
              <AbsentCell quoi="événements membres" nature="not_published" reason={null} />
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
              <AbsentCell quoi="première publication" nature="not_published" reason={null} accord="f" />
            ) : (
              <time dateTime={firstPublishedAt}>{firstPublishedAt}</time>
            )}
          </dd>
        </div>
        <div>
          <dt>Dernière réception (UTC)</dt>
          <dd>
            {lastReceivedAt === null ? (
              <AbsentCell quoi="dernière réception" nature="not_published" reason={null} accord="f" />
            ) : (
              <time dateTime={lastReceivedAt}>{lastReceivedAt}</time>
            )}
          </dd>
        </div>
        <div>
          <dt>Instrument</dt>
          <dd>
            {instrumentRef === null ? (
              <AbsentCell quoi="instrument" nature="not_applicable" reason={null} />
            ) : (
              <code>{instrumentRef}</code>
            )}
          </dd>
        </div>
        <div>
          <dt>Snapshot as_of (UTC)</dt>
          <dd>
            {asOf === null ? <AbsentCell quoi="as_of" nature="not_published" reason={null} /> : <time dateTime={asOf}>{asOf}</time>}
          </dd>
        </div>
        </dl>
      </div>
    </InspectorPanel>
  );
}

// -- file d'attention --------------------------------------------------------

export interface AttentionQueueProps {
  readonly items: readonly AttentionItem[];
  readonly asOf: string | null;
  /**
   * LOT-A3 : ce que l'inspecteur montre TANT QU'AUCUN item n'est ouvert — la
   * vérité du snapshot. La planche §1 garde l'inspecteur à droite en
   * permanence ; sans sélection, il porte la provenance de la file plutôt
   * qu'une colonne vide. Un seul panneau à la fois : le détail d'un item le
   * remplace, `Échap` le restitue.
   */
  readonly fallbackInspector?: ReactNode;
}

export function AttentionQueue({ items, asOf, fallbackInspector }: AttentionQueueProps) {
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
      {/*
        LOT-A3 — la file est BORNÉE : quinze items déroulés faisaient 1 800 px
        de page, et la planche §1 compose neuf autres modules autour. Le
        conteneur défile, il ne tronque pas : le nombre d'items servis reste
        le nombre d'items présents. `tabIndex` dans le même geste que la borne
        (axe `scrollable-region-focusable`, seuil zéro).
      */}
      <div
        className="vx-queue-scroll"
        tabIndex={0}
        role="region"
        aria-label="File d’attention, liste défilante"
      >
      <ol className="vx-queue-list">
        {items.map((item) => {
          const firstPublishedAt = provString(item.provenance, 'first_published_at');
          return (
            <li key={item.id} className="vx-queue-item">
              <div className="vx-queue-item-main">
                <button
                  type="button"
                  className="vx-queue-title"
                  // Plus `aria-haspopup="dialog"` : le panneau n'est plus un
                  // dialogue. `aria-expanded` reste, il décrit exactement ce
                  // que fait le bouton — déployer un panneau de détail.
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
      </div>
      {openItem !== null ? (
        <SideSheet item={openItem} asOf={asOf} onClose={close} />
      ) : (
        (fallbackInspector ?? null)
      )}
    </div>
  );
}
