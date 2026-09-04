import { useCallback, useEffect, useId, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { useMarketsOverview } from '../api/hooks.ts';
import { ALL_PAGES } from '../app/pages.ts';
import { flattenTickers } from '../components/markets/marketsView.ts';

/**
 * PALETTE DE COMMANDES — ⌘K / Ctrl+K.
 *
 * POURQUOI ELLE EST ÉCRITE ICI PLUTÔT QU'IMPORTÉE. Une palette est un
 * `combobox` + `listbox` : le motif est entièrement décrit par WAI-ARIA APG et
 * tient en une centaine de lignes de HTML natif. Ajouter une dépendance pour
 * cela aurait apporté un thème à neutraliser, une surface de bundle sur TOUTES
 * les routes, et une seconde convention de focus à faire cohabiter avec celle
 * du shell. Le motif est repris ; le paquet ne l'est pas.
 *
 * CE QU'ELLE CHERCHE, ET CE QU'ELLE NE PEUT PAS CHERCHER.
 *
 * Deux familles seulement, parce que ce sont les deux qui existent :
 *   - les DESTINATIONS, connues statiquement (`ALL_PAGES`) ;
 *   - les INSTRUMENTS du dernier instantané Marchés DÉJÀ EN CACHE.
 *
 * Il n'existe aucune route de recherche d'instruments dans le contrat
 * (`/api/v1/...` ne publie ni `search` ni `symbols`). La palette ne peut donc
 * pas prétendre chercher « dans le marché » : elle cherche dans ce que le
 * serveur a réellement publié. Quand l'instantané n'est pas chargé, elle le
 * DIT — au lieu de rendre une liste vide qui ferait croire à une absence de
 * résultats.
 *
 * AUCUNE ACTION DE MARCHÉ. La palette navigue et sélectionne. Elle ne porte
 * aucune commande d'ordre, de prévisualisation ou de transmission, et le
 * vocabulaire d'exécution n'y apparaît pas — un test l'exige.
 */

export interface PaletteResult {
  readonly id: string;
  readonly group: 'Destinations' | 'Instruments';
  readonly label: string;
  /** Contexte : la question de la page, ou le secteur de l'instrument. */
  readonly detail: string;
  readonly path: string;
}

/**
 * Filtre par sous-chaîne, insensible à la casse et aux accents.
 *
 * Pas de score de pertinence flou : sur un jeu de quelques dizaines d'entrées,
 * un classement approximatif rend surtout le résultat imprévisible. Ce qui
 * commence par la saisie passe devant ; le reste suit dans l'ordre servi.
 */
function normaliser(valeur: string): string {
  return valeur
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase();
}

export function filtrer(resultats: readonly PaletteResult[], saisie: string): readonly PaletteResult[] {
  const requete = normaliser(saisie.trim());
  if (requete === '') {
    return resultats;
  }
  const retenus = resultats.filter(
    (r) => normaliser(r.label).includes(requete) || normaliser(r.detail).includes(requete),
  );
  const debut = retenus.filter((r) => normaliser(r.label).startsWith(requete));
  const reste = retenus.filter((r) => !normaliser(r.label).startsWith(requete));
  return [...debut, ...reste];
}

export interface CommandPaletteProps {
  readonly open: boolean;
  readonly onClose: () => void;
}

export function CommandPalette({ open, onClose }: CommandPaletteProps) {
  const navigate = useNavigate();
  const marches = useMarketsOverview();
  const [saisie, setSaisie] = useState('');
  const [actif, setActif] = useState(0);
  const champRef = useRef<HTMLInputElement>(null);
  const declencheurRef = useRef<Element | null>(null);
  const listeId = useId();

  const destinations: readonly PaletteResult[] = useMemo(
    () =>
      ALL_PAGES.map((page) => ({
        id: `page:${page.key}`,
        group: 'Destinations' as const,
        label: page.title,
        detail: page.question,
        path: page.navPath,
      })),
    [],
  );

  const instruments: readonly PaletteResult[] = useMemo(() => {
    const apercu = marches.data;
    if (apercu === undefined) {
      return [];
    }
    return flattenTickers(apercu.sectors).map((entree) => ({
      id: `instrument:${entree.ticker.ticker}`,
      group: 'Instruments' as const,
      label: entree.ticker.ticker,
      detail: entree.sectorLabel,
      path: `/analysis/${entree.ticker.ticker}`,
    }));
  }, [marches.data]);

  const resultats = useMemo(
    () => filtrer([...destinations, ...instruments], saisie),
    [destinations, instruments, saisie],
  );

  // Le focus revient TOUJOURS à l'élément qui a ouvert la palette : sans cela,
  // fermer au clavier renvoie le focus au document et la navigation repart de
  // zéro.
  useEffect(() => {
    if (open) {
      declencheurRef.current = document.activeElement;
      champRef.current?.focus();
      setSaisie('');
      setActif(0);
    } else {
      const declencheur = declencheurRef.current;
      if (declencheur instanceof HTMLElement) {
        declencheur.focus();
      }
    }
  }, [open]);

  const ouvrir = useCallback(
    (resultat: PaletteResult | undefined) => {
      if (resultat === undefined) {
        return;
      }
      navigate(resultat.path);
      onClose();
    },
    [navigate, onClose],
  );

  if (!open) {
    return null;
  }

  const parGroupe: ReadonlyArray<[PaletteResult['group'], readonly PaletteResult[]]> = [
    ['Destinations', resultats.filter((r) => r.group === 'Destinations')],
    ['Instruments', resultats.filter((r) => r.group === 'Instruments')],
  ];

  return (
    <div
      className="vx-palette-scrim"
      role="presentation"
      onMouseDown={(evenement) => {
        if (evenement.target === evenement.currentTarget) {
          onClose();
        }
      }}
    >
      <div
        className="vx-palette"
        role="dialog"
        aria-modal="true"
        aria-label="Recherche globale et navigation"
        onKeyDown={(evenement) => {
          if (evenement.key === 'Escape') {
            evenement.preventDefault();
            onClose();
            return;
          }
          if (evenement.key === 'ArrowDown') {
            evenement.preventDefault();
            setActif((index) => (resultats.length === 0 ? 0 : (index + 1) % resultats.length));
            return;
          }
          if (evenement.key === 'ArrowUp') {
            evenement.preventDefault();
            setActif((index) =>
              resultats.length === 0 ? 0 : (index - 1 + resultats.length) % resultats.length,
            );
            return;
          }
          if (evenement.key === 'Enter') {
            evenement.preventDefault();
            ouvrir(resultats[actif]);
          }
        }}
      >
        <div className="vx-palette-field">
          <input
            ref={champRef}
            className="vx-palette-input"
            type="text"
            role="combobox"
            aria-expanded="true"
            aria-controls={listeId}
            aria-activedescendant={resultats[actif] === undefined ? undefined : `${listeId}-${actif}`}
            aria-label="Rechercher une destination ou un instrument publié"
            placeholder="Rechercher une destination ou un instrument publié…"
            value={saisie}
            onChange={(evenement) => {
              setSaisie(evenement.target.value);
              setActif(0);
            }}
          />
          <kbd className="vx-palette-kbd">Échap</kbd>
        </div>

        <ul className="vx-palette-list" id={listeId} role="listbox" aria-label="Résultats">
          {parGroupe.map(([groupe, entrees]) =>
            entrees.length === 0 ? null : (
              <li key={groupe} className="vx-palette-group" role="presentation">
                <p className="vx-palette-group-title">{groupe}</p>
                <ul role="presentation">
                  {entrees.map((resultat) => {
                    const index = resultats.indexOf(resultat);
                    return (
                      <li
                        key={resultat.id}
                        id={`${listeId}-${index}`}
                        className="vx-palette-item"
                        role="option"
                        aria-selected={index === actif}
                        data-active={index === actif ? 'true' : 'false'}
                        onMouseEnter={() => {
                          setActif(index);
                        }}
                        onMouseDown={(evenement) => {
                          evenement.preventDefault();
                          ouvrir(resultat);
                        }}
                      >
                        <span className="vx-palette-item-label">{resultat.label}</span>
                        <span className="vx-palette-item-detail">{resultat.detail}</span>
                      </li>
                    );
                  })}
                </ul>
              </li>
            ),
          )}
        </ul>

        {/*
          Deux silences DIFFÉRENTS, et les confondre serait mentir : « aucun
          résultat » dit que la recherche a abouti à rien ; « instantané non
          chargé » dit que la moitié du corpus n'a pas encore été publiée.
        */}
        {resultats.length === 0 ? (
          <p className="vx-palette-empty" role="status">
            Aucune destination ni instrument publié ne correspond à cette saisie.
          </p>
        ) : null}
        {marches.data === undefined ? (
          <p className="vx-palette-note" role="status">
            Instantané Marchés non chargé : seules les destinations sont cherchables pour l’instant.
          </p>
        ) : null}
      </div>
    </div>
  );
}

/**
 * Branche ⌘K / Ctrl+K sur toute l'application.
 *
 * Le raccourci est ignoré pendant une saisie : intercepter ⌘K alors que
 * l'utilisateur écrit dans un champ lui volerait sa frappe.
 */
export function useCommandPalette(): { readonly open: boolean; readonly setOpen: (v: boolean) => void } {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    function surTouche(evenement: KeyboardEvent): void {
      if (evenement.key !== 'k' || !(evenement.metaKey || evenement.ctrlKey)) {
        return;
      }
      const cible = evenement.target;
      const saisieEnCours =
        cible instanceof HTMLInputElement ||
        cible instanceof HTMLTextAreaElement ||
        (cible instanceof HTMLElement && cible.isContentEditable);
      if (saisieEnCours) {
        return;
      }
      evenement.preventDefault();
      setOpen((precedent) => !precedent);
    }
    window.addEventListener('keydown', surTouche);
    return () => {
      window.removeEventListener('keydown', surTouche);
    };
  }, []);

  return { open, setOpen };
}
