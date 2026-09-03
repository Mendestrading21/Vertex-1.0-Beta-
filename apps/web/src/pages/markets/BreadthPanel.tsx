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

function counts(breadth: MarketsBreadth): string {
  return `${breadth.above_count} en hausse, ${breadth.down_count} en baisse, ${breadth.flat_count} stables sur ${breadth.covered_count} couverts (univers ${breadth.universe_size})`;
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
          valueText={`${frDecimal(breadth.coverage_pct)} % (seuil ${frDecimal(breadth.coverage_threshold_pct)} %)`}
          boundsText={PCT_BOUNDS}
          markers={[
            {
              pct: breadth.coverage_threshold_pct,
              // Le chiffre du seuil est DÉJÀ dans le texte de la jauge : le
              // répéter sous le rail donnait deux fois la même mesure.
              label: 'seuil de couverture exigé',
            },
          ]}
        />
      </div>
      )}

      <CountBars breadth={breadth} />
      <p className="vx-breadth-counts">{counts(breadth)}</p>
    </section>
  );
}
