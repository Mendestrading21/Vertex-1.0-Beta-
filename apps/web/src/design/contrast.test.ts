import { describe, expect, it } from 'vitest';
import { analyser, composer, contraste, deltaE } from './colorMetrics.ts';
import { SIGNED_SCALES } from './signedScale.ts';
import { color } from './tokens.ts';

/**
 * PORTE DE CONTRASTE — LOT V1.
 *
 * `docs/05-design/TOKENS.md` affirme depuis l'origine : « Chaque token de
 * couleur a un libellé/icône associé et UNE PAIRE TEXTE/FOND VÉRIFIÉE AA ».
 * Rien ne le vérifiait. L'audit du 2026-09-04 a mesuré ce que cette absence
 * laissait passer :
 *
 *   - `signal-deep` à 2,67:1 sur `surface-1` — illisible comme texte ;
 *   - `text` sur `signal` à 1,94:1 — un bouton plein au texte clair ;
 *   - `text-muted` à 4,35:1 sur `hover` — sous le seuil AA, alors qu'il porte
 *     les métadonnées À L'INTÉRIEUR des cartes, donc sur leur état de survol.
 *
 * CE QUE CETTE PORTE N'EST PAS. Elle ne remplace pas `axe` en e2e : `axe` ne
 * mesure que les paires RÉELLEMENT rendues, sur les données du moment. Un état
 * dégradé qu'aucun test ne visite n'est jamais mesuré. Cette porte, elle,
 * mesure le CONTRAT : toute paire déclarée utilisable doit tenir, qu'elle soit
 * rendue aujourd'hui ou demain.
 */

/**
 * Le calcul lui-même vit dans `colorMetrics.ts`.
 *
 * Il y a été déplacé le jour où une deuxième porte en a eu besoin : trois
 * copies d'une même arithmétique de couleur, c'était trois occasions de
 * diverger, et une porte qui mesure faux rassure au lieu d'alerter.
 */
const ratio = contraste;

/** Arrondi à deux décimales, pour que le message d'échec soit lisible. */
const arrondi = (n: number): number => Math.round(n * 100) / 100;

/**
 * Les fonds sur lesquels du texte est RÉELLEMENT posé. `black` en est absent :
 * il n'habille aucune surface de lecture, seulement le fond de la fenêtre
 * derrière le shell.
 */
const FONDS = ['app', 'surface-0', 'surface-1', 'surface-2', 'surface-3', 'hover'] as const;

/**
 * Jetons de texte, et le seuil qu'ils doivent tenir SUR CHACUN des fonds.
 *
 * 4,5:1 est le seuil AA du texte normal (WCAG 1.4.3). Aucun jeton n'est ici à
 * 3:1 « texte large » : le produit n'a aucun texte au-dessus de 24 px qui ne
 * soit pas déjà `text` ou `signal-bright`.
 */
const TEXTES = [
  'text',
  'text-secondary',
  'text-muted',
  'silver',
  'titanium',
  'signal',
  'signal-bright',
  'positive',
  'negative',
  'warning',
  'option',
  'macro',
] as const;

/**
 * Jetons qui ne sont JAMAIS du texte, chacun avec la raison écrite qui le
 * dispense. Une exemption sans raison est une exemption qui se déguise.
 */
const JAMAIS_TEXTE: ReadonlyArray<{ readonly jeton: keyof typeof color; readonly raison: string }> = [
  {
    jeton: 'signal-deep',
    raison:
      "Fin de dégradé uniquement (ADR-017). À 2,88:1 sur `app` il n'est lisible ni comme texte ni comme fond de texte sombre ; le test « aucun jeton exempté ne sert de couleur de texte » plus bas le prouve sur le CSS réel.",
  },
  {
    jeton: 'grid-line',
    raison:
      'Trame de fond décorative. « Arrière-plan : décor presque invisible » — un décor qui atteindrait 3:1 deviendrait un contenu.',
  },
  {
    jeton: 'titanium-ghost',
    raison:
      "Filigrane de registre, délibérément sous le seuil : à `titanium-soft` le code d'espace se lisait aussi bien que le titre de page, soit un second titre qui ne dit rien.",
  },
];

describe('Contraste des jetons — WCAG 2.2', () => {
  it('la mesure elle-même est juste sur des paires connues', () => {
    // Anti-vacuité : si `ratio` était faux, tout le reste passerait pour de
    // mauvaises raisons. Noir pur sur blanc pur vaut exactement 21:1.
    expect(arrondi(ratio('#000000', '#ffffff'))).toBe(21);
    expect(arrondi(ratio('#ffffff', '#ffffff'))).toBe(1);
    // Une couleur à alpha 0 disparaît dans son fond.
    expect(arrondi(ratio('rgba(255, 255, 255, 0)', '#000000'))).toBe(1);
  });

  it('chaque jeton de texte tient AA sur chaque fond de lecture', () => {
    const echecs: string[] = [];
    for (const texte of TEXTES) {
      for (const fond of FONDS) {
        const mesure = ratio(color[texte], color[fond]);
        if (mesure < 4.5) {
          echecs.push(`${texte} sur ${fond} : ${arrondi(mesure)}:1`);
        }
      }
    }
    expect(echecs, `Paires sous le seuil AA de 4,5:1 :\n  ${echecs.join('\n  ')}`).toEqual([]);
  });

  it('un texte sombre sur accent plein tient AA', () => {
    // Le cas des boutons remplis. `text` sur `signal` vaut 1,94:1 et aucune
    // porte ne l'interdisait ; la règle est donc énoncée dans l'autre sens :
    // sur un accent plein, le texte est SOMBRE, et on prouve qu'il tient.
    const echecs: string[] = [];
    for (const accent of ['signal', 'positive', 'negative', 'warning', 'option', 'macro'] as const) {
      for (const sombre of ['black', 'app', 'surface-0'] as const) {
        const mesure = ratio(color[sombre], color[accent]);
        if (mesure < 4.5) {
          echecs.push(`${sombre} sur ${accent} : ${arrondi(mesure)}:1`);
        }
      }
    }
    expect(echecs, `Texte sombre illisible sur son accent :\n  ${echecs.join('\n  ')}`).toEqual([]);
  });

  it('le texte reste lisible sur CHAQUE cran de l’échelle divergente', () => {
    // Les crans sont translucides : ils se composent d'abord sur le fond de
    // lecture, et c'est le RÉSULTAT qui porte le texte. Mesurer le cran seul
    // n'aurait aucun sens — il n'est jamais opaque.
    //
    // Le cran le plus dense est celui qui décide : plus la teinte couvre, plus
    // le fond s'éclaircit, et plus le texte clair s'en rapproche.
    const echecs: string[] = [];
    for (const cran of SIGNED_SCALES.quotidien.steps) {
      for (const fond of FONDS) {
        const pose = composer(analyser(color[cran.token as keyof typeof color]), analyser(color[fond]));
        const mesure = ratio(color.text, pose);
        if (mesure < 4.5) {
          echecs.push(`text sur ${cran.token} posé sur ${fond} : ${arrondi(mesure)}:1`);
        }
      }
    }
    expect(echecs, `Crans où la valeur devient illisible :\n  ${echecs.join('\n  ')}`).toEqual([]);
  });

  it('deux crans voisins se DISTINGUENT une fois posés sur leur fond', () => {
    // Une échelle dont deux crans se ressemblent ne mesure rien : elle donne
    // l'illusion d'une gradation.
    //
    // La mesure est ΔE, PAS le contraste. Une première version comparait des
    // luminances et déclarait « down-1 » et « flat » indiscernables : deux
    // aplats de clarté voisine, l'un rouge et l'autre neutre, que l'œil sépare
    // pourtant sans hésiter. Le contraste est aveugle à la teinte ; la
    // distinction de deux surfaces ne l'est pas.
    //
    // Le seuil est plus bas que celui de `token-distinctness` (10) parce que la
    // question est différente : là-bas, deux SENS ne doivent pas se confondre ;
    // ici, deux crans d'une même échelle sont voisins par construction et il
    // suffit qu'un pas se voie.
    const poses = SIGNED_SCALES.quotidien.steps.map((cran) => ({
      cle: cran.key,
      couleur: composer(
        analyser(color[cran.token as keyof typeof color]),
        analyser(color['surface-1']),
      ),
    }));
    const trop_proches: string[] = [];
    for (let i = 1; i < poses.length; i += 1) {
      const precedent = poses[i - 1];
      const courant = poses[i];
      if (precedent === undefined || courant === undefined) {
        continue;
      }
      const ecart = deltaE(precedent.couleur, courant.couleur);
      if (ecart < 4) {
        trop_proches.push(`${precedent.cle} et ${courant.cle} : ΔE ${arrondi(ecart)}`);
      }
    }
    expect(trop_proches, `Crans indiscernables :\n  ${trop_proches.join('\n  ')}`).toEqual([]);
  });

  it('chaque exemption porte une raison écrite et un jeton réel', () => {
    for (const { jeton, raison } of JAMAIS_TEXTE) {
      expect(Object.keys(color), `jeton exempté inexistant : ${jeton}`).toContain(jeton);
      expect(raison.length, `raison trop courte : ${jeton}`).toBeGreaterThan(80);
    }
  });

  it('aucune exemption n’est inutile : chacune échouerait vraiment', () => {
    // Une exemption dont le jeton tiendrait AA serait une exemption morte,
    // et elle laisserait passer un défaut futur sans que personne le sache.
    for (const { jeton } of JAMAIS_TEXTE) {
      const meilleur = Math.max(...FONDS.map((fond) => ratio(color[jeton], color[fond])));
      expect(arrondi(meilleur), `exemption sans objet, à retirer : ${jeton}`).toBeLessThan(4.5);
    }
  });
});
