/**
 * Indicateurs techniques — valeurs SERVEUR, affichées telles quelles.
 *
 * Aucun calcul ici : la forme en pourcentage arrive du serveur, comme
 * `return_1d_pct` sur Marchés. Aucune interprétation non plus : un ATR est une
 * amplitude, pas un jugement, et aucun seuil n'est déclaré qui permettrait de
 * dire « élevé ».
 */
import { ServedNumber } from '../../components/widgets/ServedNumber.tsx';

export function IndicatorsPanel({
  indicators,
  currency,
}: {
  readonly indicators: Readonly<Record<string, unknown>> | null | undefined;
  readonly currency: string;
}) {
  if (indicators === null || indicators === undefined) {
    return null;
  }

  const lire = (nom: string): Readonly<Record<string, unknown>> | null => {
    const bloc = indicators[nom];
    return typeof bloc === 'object' && bloc !== null
      ? (bloc as Readonly<Record<string, unknown>>)
      : null;
  };
  const texte = (bloc: Readonly<Record<string, unknown>>, cle: string): string | null => {
    const valeur = bloc[cle];
    return typeof valeur === 'string' && valeur !== '' ? valeur : null;
  };
  const nombre = (bloc: Readonly<Record<string, unknown>>, cle: string): number | null =>
    typeof bloc[cle] === 'number' ? (bloc[cle] as number) : null;

  const volatilite = lire('realized_volatility');
  const atr = lire('atr');
  // LOT-A4 : la force relative contre l'indice DÉCLARÉ, publiée par le
  // worker sur des calendriers alignés (`market.relative_strength`).
  const force = lire('relative_strength');
  if (volatilite === null && atr === null && force === null) {
    return null;
  }

  const methode = (bloc: Readonly<Record<string, unknown>> | null): string | null => {
    if (bloc === null) return null;
    const calcul = bloc.calculation;
    if (typeof calcul !== 'object' || calcul === null) return null;
    const m = (calcul as Record<string, unknown>).method;
    return typeof m === 'string' ? m : null;
  };

  function Ligne({
    bloc,
    libelle,
    valeurAffichee,
    unite,
    fenetreCle,
    fenetreLibelle,
    testid,
  }: {
    readonly bloc: Readonly<Record<string, unknown>> | null;
    readonly libelle: string;
    /** La chaîne SERVIE, seule. L'unité voyage à part — voir ci-dessous. */
    readonly valeurAffichee: string | null;
    /**
     * L'UNITÉ NE PEUT PAS ÊTRE ROGNÉE, donc elle n'entre pas dans la boîte
     * bornée. Elle y était : « 4.413571428571428 SYN » formait une seule
     * chaîne, et borner le rendu a fait disparaître « SYN » derrière
     * l'ellipse. Un nombre sans son unité n'est pas une information abrégée,
     * c'est une information fausse — `architecture.md` l'exige aux frontières.
     */
    readonly unite: string | null;
    readonly fenetreCle: string;
    readonly fenetreLibelle: string;
    readonly testid: string;
  }) {
    if (bloc === null) return null;
    const statut = texte(bloc, 'status');
    const fenetre = nombre(bloc, fenetreCle);
    return (
      <div className="vx-indicator" data-testid={testid}>
        <dt>
          {libelle}
          {fenetre === null ? null : (
            <span className="vx-indicator-window">
              {' '}
              — {fenetreLibelle} {fenetre}
            </span>
          )}
        </dt>
        <dd>
          {statut === 'OK' && valeurAffichee !== null ? (
            /*
              La valeur SERVIE est bornée AU RENDU, jamais arrondie. Le moteur
              publie ses flottants entiers — « 4.413571428571428 » pour un ATR —
              et rendus tels quels dans une carte de deux cents pixels ils
              passaient à la ligne au milieu d'un chiffre. Personne ne lit la
              seizième décimale d'un ATR à l'écran ; la valeur entière reste au
              survol, et une porte e2e vérifie ce recours.
            */
            <>
              <ServedNumber className="vx-indicator-value" value={valeurAffichee} />
              {unite === null ? null : <span className="vx-indicator-unit"> {unite}</span>}
            </>
          ) : (
            <span className="vx-cell-absent" data-testid={`${testid}-absent`}>
              {statut ?? 'ABSENT'}
              {texte(bloc, 'detail') === null ? null : ` — ${texte(bloc, 'detail')}`}
            </span>
          )}
        </dd>
      </div>
    );
  }

  const volPct = volatilite === null ? null : texte(volatilite, 'value_pct');
  const atrValeur = atr === null ? null : texte(atr, 'value');
  const forceValeur = force === null ? null : texte(force, 'value');
  const forceIndice = force === null ? null : texte(force, 'benchmark');

  return (
    <section className="vx-indicators" aria-labelledby="vx-indicators-title">
      <h2 id="vx-indicators-title">Indicateurs techniques</h2>
      <p className="vx-indicators-note">
        Valeurs calculées par le moteur serveur et relayées telles quelles. Aucun seuil
        n’est déclaré : la mesure est publiée, son interprétation ne l’est pas.
      </p>
      <dl className="vx-indicator-list">
        <Ligne
          bloc={volatilite}
          libelle="Volatilité réalisée annualisée"
          valeurAffichee={volPct}
          unite="%"
          fenetreCle="window"
          fenetreLibelle="fenêtre"
          testid="indicator-volatility"
        />
        <Ligne
          bloc={atr}
          libelle="ATR (Wilder)"
          valeurAffichee={atrValeur}
          unite={currency}
          fenetreCle="lookback"
          fenetreLibelle="sur"
          testid="indicator-atr"
        />
        <Ligne
          bloc={force}
          libelle={`Force relative${forceIndice === null ? '' : ` contre ${forceIndice}`}`}
          valeurAffichee={forceValeur}
          unite="(ratio)"
          fenetreCle="horizon"
          fenetreLibelle="horizon"
          testid="indicator-relative-strength"
        />
      </dl>
      <p className="vx-indicators-method">
        {methode(volatilite) === null ? null : (
          <span>
            <code>market.realized_volatility</code> : {methode(volatilite)}
          </span>
        )}
        {methode(atr) === null ? null : (
          <span>
            {' · '}
            <code>market.atr</code> : {methode(atr)}
          </span>
        )}
        {methode(force) === null ? null : (
          <span>
            {' · '}
            <code>market.relative_strength</code> : {methode(force)}
          </span>
        )}
      </p>
    </section>
  );
}
