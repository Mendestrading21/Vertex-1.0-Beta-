/**
 * Aide de navigation de développement : les 4 sous-jacents/instruments
 * SYNTHÉTIQUES que le worker publie (miroir de la liste
 * `SYNTHETIC_FOCUS_TICKERS` de `vertex_core.synthetic`). Ce n'est PAS une
 * donnée de marché : une simple liste de liens de navigation ; tout autre
 * identifiant répond l'état vide honnête de l'API. Module minuscule partagé
 * par les chunks paresseux /options et /analysis.
 */
export const DEV_SYNTHETIC_UNDERLYINGS: readonly string[] = [
  'SYN-ENER-01',
  'SYN-FINL-01',
  'SYN-TECH-01',
  'SYN-TECH-02',
];
