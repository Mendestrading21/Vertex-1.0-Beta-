/**
 * ÉCHELLES DIVERGENTES À BORNES DÉCLARÉES — pour une valeur SIGNÉE en pourcent.
 *
 * CE QU'ELLES REMPLACENT. Deux façons de peindre un signe, toutes deux
 * fautives pour la même raison de fond : la couleur ne mesurait rien.
 *
 *   - La carte des marchés posait la teinte PLEINE selon le seul signe. Un
 *     +0,09 % et un +2,42 % recevaient exactement le même vert.
 *   - La carte mensuelle de performance passait par une rampe continue bornée
 *     au MAXIMUM ABSOLU des mois affichés. Le même mois à +3 % changeait donc
 *     de couleur selon les autres mois de la grille : ajouter une année
 *     exceptionnelle délavait tout le reste, et deux captures n'étaient plus
 *     comparables. C'est une normalisation locale sur des données servies,
 *     exactement ce que `.claude/rules/frontend.md` interdit.
 *
 * CE QUE C'EST. Des tables de correspondance FIXES, écrites ici une fois pour
 * toutes : une valeur servie tombe dans un intervalle nommé, et cet intervalle
 * a une teinte. La même valeur donne toujours la même couleur, sur toutes les
 * pages et dans toutes les sessions. Les bornes sont PUBLIÉES dans la légende,
 * et la valeur reste écrite en toutes lettres à côté de sa couleur : la teinte
 * accompagne le nombre, elle ne le remplace jamais.
 *
 * POURQUOI PLUSIEURS ÉCHELLES. Un rendement quotidien et un rendement mensuel
 * n'ont pas la même amplitude usuelle. Peindre les deux avec les mêmes bornes
 * saturerait la grille mensuelle — tout au dernier cran — et la couleur
 * cesserait à nouveau de mesurer. Chaque échelle porte donc ses propres seuils,
 * et son nom dit à quelle grandeur elle s'applique. Ce n'est PAS un réglage
 * automatique : le choix d'échelle est fait par le composant, une fois, et il
 * ne dépend d'aucune donnée.
 *
 * POURQUOI SEPT CRANS. Trois par signe plus le zéro exact. Au-delà, l'œil ne
 * distingue plus deux crans voisins sur une petite surface ; en deçà, on
 * retombe sur le drapeau vert/rouge qu'on vient de quitter. Le zéro a son
 * propre cran parce que « exactement zéro » est une observation, pas une
 * absence — et qu'il ne doit ressembler ni à l'un ni à l'autre signe.
 *
 * CE QU'ELLES REFUSENT. Une valeur absente ne reçoit AUCUNE couleur : la
 * fonction rend `null`, et l'appelant doit alors la traiter comme une absence.
 * Peindre une absence en gris neutre la rendrait indiscernable d'un zéro servi.
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

export interface SignedScale {
  /** Identifiant de l'échelle, employé dans les attributs de données. */
  readonly key: string;
  /** Ce que l'échelle mesure, pour le nom accessible de la légende. */
  readonly mesure: string;
  readonly steps: readonly SignedStep[];
}

/** Écriture française d'un seuil : virgule décimale, signe explicite. */
function seuil(valeur: number): string {
  const texte = Math.abs(valeur).toString().replace('.', ',');
  return `${valeur < 0 ? '−' : '+'}${texte} %`;
}

/**
 * Construit les sept crans depuis DEUX seuils.
 *
 * Les crans sont engendrés, jamais recopiés : une table écrite à la main peut
 * contenir un trou (une valeur sans couleur) ou un recouvrement (un rangement
 * qui dépend de l'ordre des lignes), et ces deux défauts sont silencieux —
 * la carte s'afficherait quand même.
 */
function construire(key: string, mesure: string, proche: number, loin: number): SignedScale {
  return {
    key,
    mesure,
    steps: [
      { key: 'down-3', from: null, to: -loin, label: `sous ${seuil(-loin)}`, token: 'negative-band-3' },
      {
        key: 'down-2',
        from: -loin,
        to: -proche,
        label: `${seuil(-loin)} à ${seuil(-proche)}`,
        token: 'negative-band-2',
      },
      {
        key: 'down-1',
        from: -proche,
        to: 0,
        label: `${seuil(-proche)} à 0 %`,
        token: 'negative-band-1',
      },
      { key: 'flat', from: 0, to: 0, label: 'exactement 0 %', token: 'titanium-soft' },
      { key: 'up-1', from: 0, to: proche, label: `0 % à ${seuil(proche)}`, token: 'positive-band-1' },
      {
        key: 'up-2',
        from: proche,
        to: loin,
        label: `${seuil(proche)} à ${seuil(loin)}`,
        token: 'positive-band-2',
      },
      { key: 'up-3', from: loin, to: null, label: `au-dessus de ${seuil(loin)}`, token: 'positive-band-3' },
    ],
  };
}

/**
 * Les échelles du produit, avec leurs seuils en POURCENT.
 *
 * Ils sont volontairement ronds : un lecteur doit pouvoir se dire « ce bloc est
 * au-dessus de deux pour cent » sans consulter une table. Ils ne dépendent
 * d'aucune donnée, donc ils ne bougent pas d'un instantané à l'autre.
 */
export const SIGNED_SCALES = {
  /** Variation d'une séance : l'ordre de grandeur usuel est le point de pourcent. */
  quotidien: construire('quotidien', 'rendement 1 jour', 1, 2),
  /** Variation d'un mois : quelques points de pourcent, donc des seuils plus larges. */
  mensuel: construire('mensuel', 'rendement mensuel', 2, 5),
} as const satisfies Record<string, SignedScale>;

/**
 * Range une valeur servie dans son cran, sur une échelle DONNÉE.
 *
 * `valeur` est le nombre déjà extrait de la chaîne servie par l'appelant :
 * cette fonction ne parse rien et n'arrondit rien. Une valeur non finie rend
 * `null` — une absence ne se peint pas.
 */
export function signedStep(valeur: number | null, echelle: SignedScale): SignedStep | null {
  if (valeur === null || !Number.isFinite(valeur)) {
    return null;
  }
  if (valeur === 0) {
    return echelle.steps.find((cran) => cran.key === 'flat') ?? null;
  }
  for (const cran of echelle.steps) {
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
