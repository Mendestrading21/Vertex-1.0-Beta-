import type { MarketsBreadth } from '../../api/client.ts';
import { CensusBars } from '../../components/CensusBars.tsx';
import { ArcGauge } from '../../components/widgets/ArcGauge.tsx';
import { LinearGauge } from '../../components/widgets/LinearGauge.tsx';
import { frDecimal } from '../../components/markets/marketsView.ts';

/**
 * BreadthPanel — les trois faits servis de la breadth, chacun dans sa forme.
 *
 * LOT P1 — POURQUOI TROIS FORMES ET NON DEUX BARRES. La breadth est une part
 * BORNÉE servie avec sa position en pourcentage : ADR-017 lui donne l'arc
 * gradué. Sa couverture est une part bornée servie AVEC UN SEUIL : elle garde
 * la jauge linéaire, où le seuil se lit à sa place sur la même échelle. Les
 * trois comptes (hausses, baisses, inchangés) sont des DÉNOMBREMENTS : ils
 * prennent les barres de dénombrement, jamais un anneau — un compte n'est pas
 * une part tant que le serveur n'en publie pas le pourcentage.
 *
 * OÙ LE SEUIL VIT, ET POURQUOI PAS SUR L'ARC. `coverage_threshold_pct` est un
 * seuil de COUVERTURE : le poser sur l'arc de la breadth le placerait sur une
 * autre échelle que la sienne et ferait lire « 80 % de breadth » là où le
 * serveur dit « 80 % de couverture exigée ». Le plan v2 l'écrivait en
 * raccourci ; la lecture juste le met sur la jauge de couverture.
 *
 * Toutes les largeurs et tous les pourcentages viennent du SERVEUR (chaînes
 * déjà rendues) : le navigateur ne calcule ni pourcentage, ni seuil, ni
 * position de marqueur.
 *
 * `status = "INVALID"` (couverture sous le seuil) : aucune valeur de
 * remplacement, et AUCUNE forme — pas même la jauge de couverture, qui
 * offrirait un chiffre à regarder à la place de celui que le serveur refuse.
 * Le panneau nomme la raison, écrit la couverture et son seuil dans la
 * phrase de refus, et garde les comptes : le ratio est refusé, pas les faits.
 */

/** Bornes de l'échelle de pourcentage, DÉCLARÉES par l'unité, pas mesurées. */
const PCT_BOUNDS = { min: '0', max: '100' } as const;

/**
 * LA POPULATION, ET RIEN QUE LA POPULATION.
 *
 * La phrase disait « 10 en hausse, 12 en baisse, 0 stables sur 22 couverts
 * (univers 24) » — or les trois premiers nombres sont exactement ceux que les
 * barres de dénombrement affichent JUSTE AU-DESSUS, avec leur libellé et leur
 * longueur. Une même donnée rendue deux fois à dix pixels d'écart n'informe
 * pas deux fois : elle occupe deux fois la place et fait douter de laquelle
 * fait foi.
 *
 * Ce que les barres ne disent PAS, en revanche, c'est sur combien
 * d'instruments ces comptes portent, ni combien l'univers en contient. Cette
 * information-là reste, seule.
 */
function population(breadth: MarketsBreadth): string {
  return `${breadth.covered_count} couverts sur un univers de ${breadth.universe_size}`;
}

function CountBars({ breadth }: { readonly breadth: MarketsBreadth }) {
  return (
    <CensusBars
      entries={[
        { key: 'above', label: 'En hausse', count: breadth.above_count },
        { key: 'down', label: 'En baisse', count: breadth.down_count },
        { key: 'flat', label: 'Inchangés', count: breadth.flat_count },
      ]}
      ariaLabel="Dénombrement des instruments couverts par sens du jour"
      testIdPrefix="markets-breadth-count"
      emptyLabel="Aucun compte publié."
    />
  );
}

export function BreadthPanel({ breadth }: { readonly breadth: MarketsBreadth }) {
  const invalide = breadth.status === 'INVALID' || breadth.value_pct === null;

  return (
    <section className="vx-breadth" aria-labelledby="vx-breadth-title">
      <h3 id="vx-breadth-title">Breadth globale</h3>

      {invalide ? (
        <p className="vx-breadth-invalid" role="status">
          <strong>Breadth non calculable</strong>
          <span>
            Couverture {frDecimal(breadth.coverage_pct)} % sous le seuil requis de{' '}
            {frDecimal(breadth.coverage_threshold_pct)} % (raison serveur :{' '}
            {breadth.reason ?? 'non fournie'}). Aucune valeur de remplacement.
          </span>
        </p>
      ) : (
      <div className="vx-breadth-figures">
        <ArcGauge
          label="Breadth"
          valuePct={breadth.value_pct}
          valueText={breadth.value_pct === null ? null : frDecimal(breadth.value_pct)}
          unit="%"
          boundsText={PCT_BOUNDS}
          thresholds={[]}
          tone="macro"
          status={breadth.status}
        />
        <LinearGauge
          label="Couverture"
          valuePct={breadth.coverage_pct}
          valueText={`${frDecimal(breadth.coverage_pct)} %`}
          boundsText={PCT_BOUNDS}
          markers={[
            {
              pct: breadth.coverage_threshold_pct,
              // LOT T3 — LE SEUIL VIT SUR SON MARQUEUR, PAS DANS LA MESURE.
              // Réunis, « 91,7 % (seuil 80,0 %) » se coupait en deux lignes
              // dont la seconde ne portait que « %) » — mesuré sur capture
              // d'Aujourd'hui, carte de 200 px. Deux mesures servies, deux
              // textes, chacun à sa place sur la même échelle : le chiffre
              // n'est ni répété ni perdu.
              label: `seuil exigé ${frDecimal(breadth.coverage_threshold_pct)} %`,
            },
          ]}
        />
      </div>
      )}

      <CountBars breadth={breadth} />
      <p className="vx-breadth-counts">{population(breadth)}</p>
    </section>
  );
}
