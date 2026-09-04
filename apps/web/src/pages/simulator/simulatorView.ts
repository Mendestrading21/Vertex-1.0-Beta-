/**
 * Aides de PRÉSENTATION et de transport du Simulateur — aucun calcul
 * financier.
 *
 * Le formulaire collecte des CHAÎNES déclarées par l'utilisateur ; elles
 * partent verbatim vers `POST /simulations/preview` (le contrat accepte les
 * chaînes décimales) et TOUT est validé et calculé côté serveur
 * (`vertex_core`). Ici on ne fait que : vérifier la STRUCTURE du formulaire
 * (champs présents, entiers de forme, bornes de taille du contrat) pour
 * l'état `invalid_input`, découper les grilles saisies en listes de chaînes,
 * et relayer la raison EXACTE d'un refus 422 avec une explication française.
 */
import type { SimulationOptionLeg, SimulationPreviewRequest } from '../../api/client.ts';
import type { SimulatorTransfer } from './transfer.ts';

// ---------------------------------------------------------------------------
// Modèle de formulaire (brouillon local, jamais persisté)
// ---------------------------------------------------------------------------

type LegSide = 'LONG' | 'SHORT';
type LegRight = 'CALL' | 'PUT' | 'STOCK';

export interface LegDraft {
  readonly id: number;
  /** « jambe longue » (quantité positive) ou « jambe courte » (négative). */
  readonly side: LegSide;
  readonly count: string;
  readonly right: LegRight;
  readonly strike: string;
  readonly premium: string;
  readonly multiplier: string;
}

export interface AssumptionsDraft {
  readonly spot: string;
  readonly volatility: string;
  readonly rate: string;
  readonly dividendYield: string;
  readonly fees: string;
  readonly spotGrid: string;
  readonly timeGridYears: string;
}

export const MAX_LEGS = 8;
export const MAX_SPOT_GRID = 41;
export const MAX_TIME_GRID = 8;

let nextLegId = 1;

export function makeLegDraft(overrides: Partial<Omit<LegDraft, 'id'>> = {}): LegDraft {
  nextLegId += 1;
  return {
    id: nextLegId,
    side: 'LONG',
    count: '1',
    right: 'CALL',
    strike: '',
    premium: '',
    multiplier: '100',
    ...overrides,
  };
}

export function legDraftFromTransfer(transfer: SimulatorTransfer): LegDraft {
  return makeLegDraft({
    side: 'LONG',
    count: '1',
    right: transfer.right,
    strike: transfer.strike,
    premium: transfer.premium ?? '',
    multiplier: String(transfer.multiplier),
  });
}

export function assumptionsFromTransfer(transfer: SimulatorTransfer): AssumptionsDraft {
  return {
    spot: transfer.spot ?? '',
    volatility: transfer.iv ?? '',
    rate: '',
    dividendYield: '',
    fees: '0',
    spotGrid: '',
    timeGridYears: '0',
  };
}

export const EMPTY_ASSUMPTIONS: AssumptionsDraft = {
  spot: '',
  volatility: '',
  rate: '',
  dividendYield: '',
  fees: '0',
  spotGrid: '',
  timeGridYears: '0',
};

// ---------------------------------------------------------------------------
// Construction de la requête (structure seulement — décimaux validés serveur)
// ---------------------------------------------------------------------------

/** Découpe une grille saisie (virgules, points-virgules ou espaces). */
export function splitGrid(value: string): string[] {
  return value
    .split(/[,;\s]+/)
    .map((entry) => entry.trim())
    .filter((entry) => entry !== '');
}

function isFormInteger(value: string): boolean {
  return /^\d+$/.test(value.trim()) && Number.parseInt(value.trim(), 10) > 0;
}

export interface BuildResult {
  readonly request: SimulationPreviewRequest | null;
  /** Défauts de STRUCTURE du formulaire (état invalid_input) — en français. */
  readonly issues: readonly string[];
}

export function buildPreviewRequest(
  legs: readonly LegDraft[],
  assumptions: AssumptionsDraft,
): BuildResult {
  const issues: string[] = [];
  if (legs.length === 0) {
    issues.push('Au moins une jambe est requise.');
  }
  if (legs.length > MAX_LEGS) {
    issues.push(`Au plus ${MAX_LEGS} jambes (contrat serveur).`);
  }
  const wireLegs: SimulationOptionLeg[] = [];
  legs.forEach((leg, index) => {
    const position = `Jambe ${index + 1}`;
    if (!isFormInteger(leg.count)) {
      issues.push(`${position} : la quantité doit être un entier strictement positif.`);
    }
    if (!isFormInteger(leg.multiplier)) {
      issues.push(`${position} : le multiplicateur doit être un entier strictement positif.`);
    }
    if (leg.right === 'STOCK') {
      if (leg.strike.trim() !== '') {
        issues.push(`${position} : une jambe STOCK ne porte pas de strike (contrat serveur).`);
      }
    } else if (leg.strike.trim() === '') {
      issues.push(`${position} : le strike est requis pour CALL/PUT.`);
    }
    if (leg.premium.trim() === '') {
      issues.push(`${position} : la prime unitaire déclarée est requise.`);
    }
    if (issues.length > 0) {
      return;
    }
    const count = Number.parseInt(leg.count.trim(), 10);
    const wireLeg: SimulationOptionLeg = {
      quantity: leg.side === 'LONG' ? count : -count,
      right: leg.right,
      premium: leg.premium.trim(),
      multiplier: Number.parseInt(leg.multiplier.trim(), 10),
      // STOCK : le contrat interdit le strike — null explicite (défaut wire).
      strike: leg.right === 'STOCK' ? null : leg.strike.trim(),
    };
    wireLegs.push(wireLeg);
  });

  const required: readonly [keyof AssumptionsDraft, string][] = [
    ['spot', 'le spot déclaré'],
    ['volatility', 'la volatilité déclarée'],
    ['rate', 'le taux déclaré'],
    ['dividendYield', 'le rendement de dividende déclaré'],
  ];
  for (const [key, label] of required) {
    if (assumptions[key].trim() === '') {
      issues.push(`Hypothèses : ${label} est requis (champ décimal, validé côté serveur).`);
    }
  }
  const spotGrid = splitGrid(assumptions.spotGrid);
  const timeGrid = splitGrid(assumptions.timeGridYears);
  if (spotGrid.length === 0) {
    issues.push('Hypothèses : la grille de spots doit contenir au moins une valeur.');
  }
  if (spotGrid.length > MAX_SPOT_GRID) {
    issues.push(`Hypothèses : la grille de spots est bornée à ${MAX_SPOT_GRID} valeurs (contrat serveur).`);
  }
  if (timeGrid.length === 0) {
    issues.push('Hypothèses : la grille de temps doit contenir au moins une valeur.');
  }
  if (timeGrid.length > MAX_TIME_GRID) {
    issues.push(`Hypothèses : la grille de temps est bornée à ${MAX_TIME_GRID} valeurs (contrat serveur).`);
  }

  if (issues.length > 0) {
    return { request: null, issues };
  }
  return {
    request: {
      legs: wireLegs,
      assumptions: {
        spot: assumptions.spot.trim(),
        volatility: assumptions.volatility.trim(),
        rate: assumptions.rate.trim(),
        dividend_yield: assumptions.dividendYield.trim(),
        fees: assumptions.fees.trim() === '' ? '0' : assumptions.fees.trim(),
        spot_grid: spotGrid,
        time_grid_years: timeGrid,
      },
    },
    issues: [],
  };
}

// ---------------------------------------------------------------------------
// Refus 422 : relais de la raison EXACTE + explication française
// ---------------------------------------------------------------------------

/** Explications françaises des codes de refus connus (le code reste affiché). */
export const REJECTION_CODES_FR: Readonly<Record<string, string>> = {
  OUTSIDE_CLOSED_CATALOG:
    'Structure hors du catalogue fermé DEFINED_RISK : le vérificateur ne certifie que les ' +
    'structures à risque défini de son catalogue — la prévisualisation est refusée, rien n’est ' +
    'approximé.',
  UNCOVERED_SHORT_UPSIDE_TAIL:
    'Jambe courte non couverte quand le spot monte : la perte théorique n’est pas bornée — ' +
    'structure refusée fail-closed.',
  UNCOVERED_SHORT_DOWNSIDE_TAIL:
    'Jambe courte non couverte quand le spot baisse : la perte théorique n’est pas bornée — ' +
    'structure refusée fail-closed.',
  VERTICAL_DEBIT_NOT_BELOW_WIDTH:
    'Débit du vertical incohérent avec l’écart de strikes : la structure déclarée ne correspond ' +
    'pas à un vertical à risque défini — refusée.',
};

export interface RejectionView {
  /** `refusal` : code typé du vérificateur/du domaine ; `wire` : contrat JSON violé. */
  readonly kind: 'refusal' | 'wire';
  readonly code: string | null;
  readonly message: string | null;
  readonly explanation: string | null;
  readonly wireIssues: readonly string[];
}

export function rejectionViewOf(detail: unknown): RejectionView | null {
  if (typeof detail !== 'object' || detail === null) {
    return null;
  }
  const body = (detail as Record<string, unknown>)['detail'];
  if (typeof body === 'object' && body !== null && !Array.isArray(body)) {
    const record = body as Record<string, unknown>;
    const code = typeof record['code'] === 'string' ? record['code'] : null;
    const message = typeof record['message'] === 'string' ? record['message'] : null;
    if (code === null && message === null) {
      return null;
    }
    return {
      kind: 'refusal',
      code,
      message,
      explanation: code !== null ? (REJECTION_CODES_FR[code] ?? null) : null,
      wireIssues: [],
    };
  }
  if (Array.isArray(body)) {
    const wireIssues = body
      .map((entry) => {
        if (typeof entry !== 'object' || entry === null) {
          return null;
        }
        const record = entry as Record<string, unknown>;
        const loc = Array.isArray(record['loc']) ? record['loc'].join('.') : '';
        const msg = typeof record['msg'] === 'string' ? record['msg'] : '';
        const line = [loc, msg].filter((part) => part !== '').join(' — ');
        return line === '' ? null : line;
      })
      .filter((line): line is string => line !== null);
    return {
      kind: 'wire',
      code: null,
      message: null,
      explanation: null,
      wireIssues,
    };
  }
  return null;
}
