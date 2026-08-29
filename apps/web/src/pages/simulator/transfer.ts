/**
 * Transfert typé Options → Simulateur.
 *
 * L'inspecteur d'option construit ce DTO à partir des CHAÎNES SERVEUR
 * verbatim du snapshot (identité complète du contrat, prime côté ASK si
 * publiée, spot et IV Vertex si résolue) et le transmet par l'état de
 * navigation React Router (`navigate('/simulator', { state })`).
 *
 * Choix documenté : ni query string (une identité de contrat n'a rien à
 * faire dans une URL partageable) ni localStorage (état VOLATILE d'intention,
 * pas une donnée à persister). L'état de navigation est perdu au rechargement
 * complet — comportement voulu : le simulateur repart alors vide, sans
 * jamais rejouer une intention périmée.
 *
 * À la réception, `parseSimulatorTransfer` revalide TOUT fail-closed : un
 * état absent, d'une autre version ou malformé rend `null` et le composeur
 * démarre vide (jamais un préremplissage deviné).
 */

export const SIMULATOR_TRANSFER_VERSION = 1 as const;

export interface SimulatorTransfer {
  readonly version: typeof SIMULATOR_TRANSFER_VERSION;
  readonly source: 'options';
  /** Identité complète du contrat (chaînes serveur verbatim). */
  readonly underlying: string;
  readonly conId: number | null;
  readonly right: 'CALL' | 'PUT';
  readonly strike: string;
  readonly expiration: string;
  readonly tradingClass: string;
  readonly multiplier: number;
  readonly currency: string;
  /** Prime unitaire suggérée (ask serveur verbatim) — éditable, jamais imposée. */
  readonly premium: string | null;
  readonly premiumSide: 'ASK' | null;
  /** Hypothèses suggérées depuis le snapshot (verbatim, éditables). */
  readonly spot: string | null;
  readonly iv: string | null;
  readonly population: string | null;
}

function isDecimalString(value: unknown): value is string {
  return typeof value === 'string' && /^[+-]?\d+(\.\d+)?$/.test(value);
}

function optionalDecimalString(value: unknown): string | null {
  return isDecimalString(value) ? value : null;
}

export function parseSimulatorTransfer(value: unknown): SimulatorTransfer | null {
  if (typeof value !== 'object' || value === null) {
    return null;
  }
  const raw = value as Record<string, unknown>;
  if (raw['version'] !== SIMULATOR_TRANSFER_VERSION || raw['source'] !== 'options') {
    return null;
  }
  const underlying = raw['underlying'];
  const right = raw['right'];
  const strike = raw['strike'];
  const expiration = raw['expiration'];
  const tradingClass = raw['tradingClass'];
  const multiplier = raw['multiplier'];
  const currency = raw['currency'];
  if (
    typeof underlying !== 'string' ||
    underlying === '' ||
    (right !== 'CALL' && right !== 'PUT') ||
    !isDecimalString(strike) ||
    typeof expiration !== 'string' ||
    expiration === '' ||
    typeof tradingClass !== 'string' ||
    tradingClass === '' ||
    typeof multiplier !== 'number' ||
    !Number.isInteger(multiplier) ||
    multiplier <= 0 ||
    typeof currency !== 'string' ||
    currency === ''
  ) {
    return null;
  }
  const conId = raw['conId'];
  const premiumSide = raw['premiumSide'];
  const population = raw['population'];
  return {
    version: SIMULATOR_TRANSFER_VERSION,
    source: 'options',
    underlying,
    conId: typeof conId === 'number' && Number.isInteger(conId) ? conId : null,
    right,
    strike,
    expiration,
    tradingClass,
    multiplier,
    currency,
    premium: optionalDecimalString(raw['premium']),
    premiumSide: premiumSide === 'ASK' ? 'ASK' : null,
    spot: optionalDecimalString(raw['spot']),
    iv: optionalDecimalString(raw['iv']),
    population: typeof population === 'string' && population !== '' ? population : null,
  };
}
