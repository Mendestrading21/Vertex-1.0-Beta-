/**
 * ÉCHELLE DIVERGENTE À BORNES DÉCLARÉES — pour une valeur SIGNÉE en pourcent.
 *
 * CE QU'ELLE REMPLACE. Trois couleurs plates : vert plein si positif, rouge
 * plein si négatif, gris si nul. Un +0,09 % et un +2,42 % recevaient le même
 * vert. La couleur couvrait donc toute la surface de la carte des marchés sans
 * mesurer quoi que ce soit — l'inverse exact de la loi « la couleur est une
 * mesure » — et une planche de blocs saturés relève de l'esthétique que
 * l'identité proscrit nommément.
 *
 * CE QU'ELLE N'EST PAS. Ce n'est pas une normalisation. Une normalisation
 * regarde l'ensemble des valeurs affichées pour en déduire un minimum et un
 * maximum ; la même valeur changerait alors de couleur selon ses voisines, deux
 * captures ne seraient plus comparables, et la teinte deviendrait un calcul
 * local sur des données servies — ce que `.claude/rules/frontend.md` interdit.
 *
 * CE QU'ELLE EST. Une table de correspondance FIXE, écrite ici une fois pour
 * toutes : une valeur servie tombe dans un intervalle nommé, et cet intervalle
 * a une teinte. La même valeur donne toujours la même couleur, sur toutes les
 * pages, dans toutes les sessions. Les bornes sont PUBLIÉES dans la légende,
 * et la valeur elle-même reste écrite en toutes lettres à côté de sa couleur :
 * la teinte accompagne le nombre, elle ne le remplace jamais.
 *
 * POURQUOI SEPT CRANS. Trois par signe plus le zéro exact. Au-delà, l'œil ne
 * distingue plus deux crans voisins sur une petite surface ; en deçà, on
 * retombe sur le drapeau vert/rouge qu'on vient de quitter. Le zéro a son
 * propre cran parce que « exactement zéro » est une observation, pas une
 * absence — et qu'il ne doit ressembler ni à l'un ni à l'autre signe.
 *
 * CE QU'ELLE REFUSE. Une valeur absente ne reçoit AUCUNE couleur : elle rend
 * `null`, et l'appelant doit alors la traiter comme une absence. Peindre une
 * absence en gris neutre la rendrait indiscernable d'un zéro servi.
 */

/** Un cran de l'échelle : ses bornes, son nom, son jeton. */
export interface SignedStep {
  /** Identifiant stable, utilisé comme attribut de données et comme clé. */
  readonly key: string;
  /** Borne basse INCLUSE, en pourcent. `null` = pas de borne basse. */
  readonly from: number | null;
  /** Borne haute EXCLUE, en pourcent. `null` = pas de borne haute. */
  readonly to: number | null;
  /** Libellé de légende, en français, avec ses bornes chiffrées. */
  readonly label: string;
  /** Jeton de couleur, sans le préfixe `--vx-`. */
  readonly token: string;
}

/**
 * Les bornes, en POURCENT, telles qu'elles apparaissent dans la légende.
 *
 * Elles sont volontairement rondes : un lecteur doit pouvoir se dire « ce
 * bloc est au-dessus de deux pour cent » sans consulter une table. Elles ne
 * dépendent d'aucune donnée, donc elles ne bougent pas d'un instantané à
 * l'autre.
 */
export const SIGNED_STEPS: readonly SignedStep[] = [
  { key: 'down-3', from: null, to: -2, label: 'sous −2 %', token: 'negative-band-3' },
  { key: 'down-2', from: -2, to: -1, label: '−2 % à −1 %', token: 'negative-band-2' },
  { key: 'down-1', from: -1, to: 0, label: '−1 % à 0 %', token: 'negative-band-1' },
  { key: 'flat', from: 0, to: 0, label: 'exactement 0 %', token: 'titanium-soft' },
  { key: 'up-1', from: 0, to: 1, label: '0 % à +1 %', token: 'positive-band-1' },
  { key: 'up-2', from: 1, to: 2, label: '+1 % à +2 %', token: 'positive-band-2' },
  { key: 'up-3', from: 2, to: null, label: 'au-dessus de +2 %', token: 'positive-band-3' },
];

/**
 * Range une valeur servie dans son cran.
 *
 * `valeur` est le NOMBRE déjà extrait de la chaîne servie par l'appelant —
 * cette fonction ne parse rien et n'arrondit rien. Une valeur non finie rend
 * `null` : une absence ne se peint pas.
 */
export function signedStep(valeur: number | null): SignedStep | null {
  if (valeur === null || !Number.isFinite(valeur)) {
    return null;
  }
  if (valeur === 0) {
    return SIGNED_STEPS.find((cran) => cran.key === 'flat') ?? null;
  }
  for (const cran of SIGNED_STEPS) {
    if (cran.key === 'flat') {
      continue;
    }
    const auDessus = cran.from === null || valeur >= cran.from;
    const enDessous = cran.to === null || valeur < cran.to;
    if (auDessus && enDessous) {
      return cran;
    }
  }
  return null;
}
