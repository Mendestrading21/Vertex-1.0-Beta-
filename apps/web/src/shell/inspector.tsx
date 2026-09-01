import { useEffect, useState, useSyncExternalStore } from 'react';
import { createPortal } from 'react-dom';

/**
 * Inspecteur contextuel du shell — point 6 de l'anatomie canonique :
 * « zone de travail dense avec une dominante centrale et un inspecteur
 * contextuel À DROITE ». Largeur de référence : 300–340 px selon viewport
 * (`references/canonical-visual.md`).
 *
 * Le contrat des douze pages donne à CHAQUE destination le contenu de son
 * inspecteur (§7 « ligne sélectionnée, provenance manuelle, corrections et
 * impacts », §10 « source, fuseau, historique, instruments liés et
 * incertitude », etc.). L'inspecteur est donc un EMPLACEMENT du shell, rempli
 * par la page — jamais un composant qui irait lire les données lui-même.
 *
 * Deux règles tenues par ce mécanisme :
 *
 * 1. **Aucune colonne morte.** L'aside n'occupe la grille que si une page y a
 *    monté du contenu. Une destination qui n'a rien à inspecter n'affiche pas
 *    un panneau vide — ce serait de la chrome décorative, et
 *    `.claude/rules/frontend.md` interdit d'ajouter un module « sans décision
 *    utilisateur précise ».
 * 2. **Un seul propriétaire.** L'inspecteur n'a pas d'état propre et ne
 *    recalcule rien : il rend ce que la page lui passe, qui vient déjà d'un
 *    DTO relayé.
 *
 * Mécanique : le panneau est monté par la page via un portail vers le nœud du
 * shell. Un compteur externe (même motif que `sseStateStore`) dit au shell si
 * au moins un panneau est monté, sans que le shell ait à connaître les pages.
 */

let mountedPanels = 0;
const listeners = new Set<() => void>();

function notify(): void {
  for (const listener of listeners) {
    listener();
  }
}

export const inspectorStore = {
  getState(): number {
    return mountedPanels;
  },
  subscribe(listener: () => void): () => void {
    listeners.add(listener);
    return () => {
      listeners.delete(listener);
    };
  },
};

/** Identifiant du nœud d'accueil, posé par `AppShell`. */
export const INSPECTOR_SLOT_ID = 'vx-inspector-slot';

/** `true` dès qu'une page a monté un panneau d'inspecteur. */
export function useInspectorOccupied(): boolean {
  return useSyncExternalStore(
    inspectorStore.subscribe,
    () => inspectorStore.getState() > 0,
    () => false,
  );
}

export interface InspectorPanelProps {
  /**
   * Titre du panneau. Le contrat canonique montre « Inspecteur — <sujet> » :
   * le sujet est le nom de l'élément sélectionné, jamais un libellé générique.
   */
  readonly subject: string;
  readonly children: React.ReactNode;
}

/**
 * Monte un panneau dans l'inspecteur du shell. À rendre par la PAGE, pas par
 * le shell : c'est la page qui sait ce qu'elle a de sélectionné.
 */
export function InspectorPanel({ subject, children }: InspectorPanelProps) {
  const [slot, setSlot] = useState<HTMLElement | null>(null);

  useEffect(() => {
    mountedPanels += 1;
    notify();
    // Le nœud d'accueil est rendu par `AppShell`, donc déjà présent quand une
    // page se monte. On le lit après la peinture pour ne dépendre d'aucun
    // ordre de montage.
    setSlot(document.getElementById(INSPECTOR_SLOT_ID));
    return () => {
      mountedPanels -= 1;
      notify();
    };
  }, []);

  if (slot === null) {
    return null;
  }

  return createPortal(
    <section className="vx-inspector-panel" aria-labelledby="vx-inspector-title">
      <h2 id="vx-inspector-title" className="vx-inspector-heading">
        Inspecteur — {subject}
      </h2>
      {children}
    </section>,
    slot,
  );
}
