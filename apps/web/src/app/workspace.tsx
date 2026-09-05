import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import type { ReactNode } from 'react';

/**
 * CONTEXTE DE TRAVAIL — le modèle de contexte partagé du skill maître.
 *
 * CE QU'IL RÉPARE. L'application ne contenait AUCUN contexte React : chaque
 * page tenait sa propre sélection dans un `useState` local — huit `selected`
 * indépendants, mesurés. Cliquer un instrument sur Marchés ne disait rien à
 * Analyse ; revenir sur une page perdait le choix qu'on venait d'y faire. Le
 * skill exige pourtant que la navigation PRÉSERVE explicitement instrument,
 * horizon, devise, fuseau, portefeuille manuel, scénario et référence.
 *
 * QUI EST PROPRIÉTAIRE DE QUOI, ET POURQUOI CE N'EST PAS ARBITRAIRE.
 *
 * L'URL reste propriétaire de ce qu'elle porte déjà : `/analysis/:instrument`
 * et `/options/:underlying` sont des adresses partageables, et une seconde
 * source pour la même valeur créerait exactement la divergence que ce contexte
 * cherche à supprimer. Les pages concernées appellent donc `adopter()` avec le
 * paramètre de route : le contexte SUIT l'URL, il ne la contredit jamais.
 *
 * Le contexte est propriétaire de ce que l'URL ne porte pas : horizon, devise,
 * fuseau, référence de comparaison, scénario actif. Ces choix survivent à la
 * navigation sans polluer une adresse qu'on partage.
 *
 * CE QU'IL N'INVENTE PAS. Aucun instrument par défaut : `activeInstrument` vaut
 * `null` tant que rien n'a été choisi, et les pages affichent alors leur état
 * vide explicite. Choisir « le premier de la liste » aurait fabriqué une
 * sélection que l'utilisateur n'a pas faite, et l'aurait rendue indiscernable
 * d'un vrai choix.
 *
 * CE QU'IL NE CONTIENT PAS. Aucune donnée de marché, aucun résultat de calcul,
 * aucun verdict. C'est un contexte d'INTENTION — ce que l'utilisateur regarde —
 * jamais un cache parallèle. Les données restent la propriété de React Query,
 * et le verdict celle du serveur.
 */

/** Devise de travail. `CHF` par défaut (modèle de contexte du skill maître). */
export type WorkspaceCurrency = 'CHF' | 'EUR' | 'USD';

export interface WorkspaceState {
  /** Instrument regardé. `null` = aucun choix fait — jamais un défaut fabriqué. */
  readonly activeInstrument: string | null;
  /** Venue de l'instrument, quand elle est servie. */
  readonly venue: string | null;
  /** Horizon d'analyse déclaré (« 1 mois », « 6 mois »). */
  readonly horizon: string | null;
  readonly currency: WorkspaceCurrency;
  /** Fuseau IANA d'affichage. Le stockage reste UTC. */
  readonly timezone: string;
  /** Portefeuille manuel sélectionné. */
  readonly portfolioId: string | null;
  /** Scénario de simulation actif. */
  readonly scenarioId: string | null;
  /** Référence de comparaison. */
  readonly benchmark: string | null;
}

export interface WorkspaceApi extends WorkspaceState {
  /**
   * Adopte l'instrument porté par l'URL.
   *
   * Distinct de `selectInstrument` À DESSEIN : celui-ci est l'écho d'une
   * adresse, celui-là un choix de l'utilisateur. Les confondre ferait qu'un
   * simple rendu de page ressemblerait à une action.
   */
  readonly adopter: (instrument: string | null, venue?: string | null) => void;
  readonly selectInstrument: (instrument: string | null, venue?: string | null) => void;
  readonly setHorizon: (horizon: string | null) => void;
  readonly setCurrency: (currency: WorkspaceCurrency) => void;
  readonly setPortfolio: (portfolioId: string | null) => void;
  readonly setScenario: (scenarioId: string | null) => void;
  readonly setBenchmark: (benchmark: string | null) => void;
}

const DEFAUT: WorkspaceState = {
  activeInstrument: null,
  venue: null,
  horizon: null,
  currency: 'CHF',
  timezone: 'Europe/Zurich',
  portfolioId: null,
  scenarioId: null,
  benchmark: null,
};

const WorkspaceContext = createContext<WorkspaceApi | null>(null);

export function WorkspaceProvider({ children }: { readonly children: ReactNode }) {
  const [etat, setEtat] = useState<WorkspaceState>(DEFAUT);

  const poser = useCallback((instrument: string | null, venue: string | null) => {
    setEtat((precedent) =>
      // Comparaison avant écriture : réécrire la même valeur re-rendrait tous
      // les consommateurs à chaque rendu de page, pour rien.
      precedent.activeInstrument === instrument && precedent.venue === venue
        ? precedent
        : { ...precedent, activeInstrument: instrument, venue },
    );
  }, []);

  const api: WorkspaceApi = useMemo(
    () => ({
      ...etat,
      adopter: (instrument, venue = null) => {
        poser(instrument, venue);
      },
      selectInstrument: (instrument, venue = null) => {
        poser(instrument, venue);
      },
      setHorizon: (horizon) => {
        setEtat((precedent) => ({ ...precedent, horizon }));
      },
      setCurrency: (currency) => {
        setEtat((precedent) => ({ ...precedent, currency }));
      },
      setPortfolio: (portfolioId) => {
        setEtat((precedent) => ({ ...precedent, portfolioId }));
      },
      setScenario: (scenarioId) => {
        setEtat((precedent) => ({ ...precedent, scenarioId }));
      },
      setBenchmark: (benchmark) => {
        setEtat((precedent) => ({ ...precedent, benchmark }));
      },
    }),
    [etat, poser],
  );

  return <WorkspaceContext.Provider value={api}>{children}</WorkspaceContext.Provider>;
}

/**
 * Lit le contexte, et ÉCHOUE bruyamment hors du fournisseur.
 *
 * Rendre un état par défaut aurait laissé un composant fonctionner en
 * apparence tout en ignorant silencieusement chaque sélection — le pire des
 * deux mondes, parce que le défaut ne se voit qu'à l'usage.
 */
export function useWorkspace(): WorkspaceApi {
  const contexte = useContext(WorkspaceContext);
  if (contexte === null) {
    throw new Error(
      'useWorkspace() hors de <WorkspaceProvider> : le contexte de travail doit envelopper toute la coquille.',
    );
  }
  return contexte;
}
