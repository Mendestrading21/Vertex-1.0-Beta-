import { FreshnessBadge } from '../components/FreshnessBadge.tsx';
import { resolvePopulationNature } from '../components/SyntheticBanner.tsx';
import { flattenTickers, frDecimal } from '../components/markets/marketsView.ts';
import { pageStateOf, useMarketsOverview } from '../api/hooks.ts';
import type { PageDataState } from '../api/hooks.ts';

/**
 * Ticker horizontal du shell — point 4 de l'anatomie canonique : « ticker
 * horizontal compact en haut, dans une surface vitrée continue ».
 *
 * POURQUOI IL ARRIVE MAINTENANT, ET PAS AU LOT-09.
 *
 * `docs/99-status/DEBT.md` le déclarait OUVERT au motif qu'il « exige […] un
 * contrat ». C'était FAUX, et la vérification refaite le 2026-09-01 contre le
 * contrat OpenAPI le montre : `/api/v1/markets/overview` publie déjà
 * `MarketsTicker` — `ticker`, `last_close`, `return_1d_pct`, `currency`,
 * `quality`, `synthetic`, `trading_day` — TOUS calculés et formatés par le
 * worker. Ce qui restait n'était pas un contrat manquant mais une décision de
 * CHARGE RÉSEAU. Elle est prise ici, et elle est bornée :
 *
 *   - la clé de requête est `markets_overview/global`, EXACTEMENT celle
 *     qu'utilise la page Marchés. Sur `/markets`, react-query dédoublonne :
 *     une seule requête, pas deux ;
 *   - `staleTime: Infinity` (déclaré dans `useMarketsOverview`) : aucun
 *     re-fetch périodique, donc aucun trafic de fond. Le ticker ne « bat » pas.
 *
 * CE QU'IL NE FAIT PAS, ET POURQUOI.
 *
 * 1. AUCUN CALCUL. Cours et rendement sont des chaînes décimales du serveur,
 *    affichées verbatim (seul le point devient une virgule française). Le
 *    classement de signe vient de `signGroupOf`, propriétaire unique de cette
 *    règle, déplacé au LOT-14 sous `components/markets/` précisément pour que
 *    le shell n'en écrive PAS une seconde copie.
 * 2. AUCUN TRI. L'ordre est celui du worker, secteur par secteur. Reclasser
 *    ici produirait un classement financier, interdit.
 * 3. AUCUN MOUVEMENT. Le contrat canonique l'écrit : « aucun ticker animé
 *    faisant croire à une donnée live ». Le défilement est celui de
 *    l'utilisateur, jamais une animation.
 * 4. AUCUNE PORTÉE APPLICATIVE. La population, la fraîcheur et l'heure
 *    affichées sont celles de CE snapshot, et elles sont portées PAR le
 *    ticker. Les poser dans un coin haut-droit SÉPARÉ leur donnerait une
 *    portée « Vertex » qu'aucune source ne publie : il n'existe ni mode de
 *    données global, ni fraîcheur globale, ni heure globale.
 *
 * LOT-A1 — POINTS 4 ET 5 : L'HEURE SERVIE, À DROITE.
 *
 * Les planches canoniques posent une heure UTC à l'extrémité droite de la
 * bande. Deux décisions la rendent honnête.
 *
 * A. L'HEURE EST CELLE DE L'INSTANTANÉ, JAMAIS `Date.now()`. Une horloge
 *    murale qui AVANCE à côté d'un instantané FIGÉ fabrique une impression de
 *    courant — exactement ce que `.claude/rules/financial-safety.md` interdit
 *    quand il refuse qu'un cache soit présenté comme du live. Sans `as_of`
 *    servi, il n'y a AUCUNE heure à afficher : `servedClockOf` sort `null` et
 *    rien n'est rendu. Aucune heure de repli, jamais.
 *
 * B. LE DÉPLACEMENT À DROITE EST VISUEL, PAS STRUCTUREL. L'ordre du DOM reste
 *    l'ordre de lecture — y compris au lecteur d'écran — et il place la
 *    DÉGRADATION (`PÉRIMÉ`, `COUVERTURE PARTIELLE`) AVANT les cours qu'elle
 *    qualifie : c'est ce que le LOT-14 avait établi, « un cours lu avant son
 *    étiquette est un cours lu sans elle », et le retirer serait une
 *    régression. Seul le PLACEMENT DE GRILLE en CSS pose le bloc de
 *    métadonnées à droite. La répartition n'est pas arbitraire : ce qui
 *    QUALIFIE les valeurs reste devant, ce qui IDENTIFIE l'instantané passe
 *    derrière.
 *
 * Le ticker couvre ses huit états : sans instantané, sans session, hors ligne
 * ou en erreur, il n'affiche AUCUN chiffre — il dit ce qui manque. Un ticker
 * qui garderait ses derniers cours en cas de coupure présenterait un cache
 * comme du courant, ce que `.claude/rules/financial-safety.md` interdit.
 */

/** Ce que la bande a le droit d'afficher, dérivé du seul état observé. */
type TickerMode = 'values' | 'notice';

export interface TickerFrame {
  readonly mode: TickerMode;
  /** Message affiché à la place des valeurs. `null` en mode `values`. */
  readonly notice: string | null;
  /** Marque de dégradation affichée À CÔTÉ des valeurs. `null` si aucune. */
  readonly caveat: string | null;
}

/**
 * Décide entre valeurs et message, à partir de l'état de requête et de l'état
 * canonique publié par le worker. Exporté pour être testé sans navigateur.
 *
 * `stale` et `partial` gardent les valeurs — le serveur les sert et dit
 * lui-même qu'elles sont dégradées — mais ne peuvent JAMAIS les montrer nues :
 * le `caveat` accompagne alors chaque affichage.
 */
export function tickerFrameOf(
  queryState: PageDataState,
  dataState: 'ok' | 'partial' | 'stale' | null | undefined,
  snapshotState: 'ok' | 'stale' | 'empty' | undefined,
): TickerFrame {
  if (queryState === 'loading') {
    return { mode: 'notice', notice: 'Ticker — chargement de l’instantané.', caveat: null };
  }
  if (queryState === 'auth-required') {
    return { mode: 'notice', notice: 'Ticker — session requise.', caveat: null };
  }
  if (queryState === 'offline') {
    return { mode: 'notice', notice: 'Ticker — API locale injoignable.', caveat: null };
  }
  if (queryState === 'error' || snapshotState === undefined) {
    return { mode: 'notice', notice: 'Ticker — instantané illisible.', caveat: null };
  }
  if (snapshotState === 'empty') {
    return { mode: 'notice', notice: 'Ticker — aucun instantané publié.', caveat: null };
  }
  if (snapshotState === 'stale' || dataState === 'stale') {
    return { mode: 'values', notice: null, caveat: 'PÉRIMÉ' };
  }
  if (dataState === 'partial') {
    return { mode: 'values', notice: null, caveat: 'COUVERTURE PARTIELLE' };
  }
  return { mode: 'values', notice: null, caveat: null };
}

/**
 * L'instant SERVI, formaté en UTC. `null` dès que rien n'est qualifiable.
 *
 * POURQUOI UNE FONCTION PURE ET EXPORTÉE. C'est la seule façon d'éprouver
 * l'invariant sans navigateur : `null` sur absence, `null` sur illisible,
 * aucune valeur de repli, et un résultat identique quel que soit le fuseau de
 * la machine qui lit.
 *
 * POURQUOI DES COMPOSANTS `getUTC*` ET PAS `toLocaleString`. `toLocaleString`
 * dépend du fuseau et de la locale du navigateur : deux lecteurs verraient
 * deux heures pour le MÊME instantané, et aucun des deux ne saurait laquelle
 * est celle du marché. Le suffixe `UTC` est écrit en clair pour la même
 * raison — une heure sans fuseau n'est pas une heure.
 *
 * Ce n'est pas un calcul financier : aucune quantité de marché n'est dérivée,
 * seul un instant déjà servi change de représentation.
 */
export function servedClockOf(asOf: string | null | undefined): string | null {
  if (asOf === null || asOf === undefined || asOf === '') {
    return null;
  }
  const instant = new Date(asOf);
  if (Number.isNaN(instant.getTime())) {
    return null;
  }
  const deuxChiffres = (valeur: number): string => String(valeur).padStart(2, '0');
  const jour = deuxChiffres(instant.getUTCDate());
  const mois = deuxChiffres(instant.getUTCMonth() + 1);
  const annee = String(instant.getUTCFullYear()).padStart(4, '0');
  const heures = deuxChiffres(instant.getUTCHours());
  const minutes = deuxChiffres(instant.getUTCMinutes());
  return `${jour}/${mois}/${annee} ${heures}:${minutes} UTC`;
}

export function ShellTicker() {
  const query = useMarketsOverview();
  const queryState = pageStateOf(query);
  const data = query.data;
  const frame = tickerFrameOf(queryState, data?.data_state, data?.state);

  const entries = frame.mode === 'values' && data !== undefined ? flattenTickers(data.sectors) : [];
  const { key: populationKey, nature } = resolvePopulationNature(data?.population ?? null);
  const horloge = servedClockOf(data?.as_of);

  // `data-ticker-state`, surtout PAS `data-state` : cet attribut appartient à
  // `DataStateBoundary`. Le poser ici faisait résoudre `[data-state="offline"]`
  // à DEUX éléments sur chaque page — le bandeau de la page et la bande — et
  // 58 tests e2e l'ont dit d'un coup.
  return (
    <section
      className="vx-ticker"
      aria-label="Ticker des marchés"
      data-mode={frame.mode}
      data-ticker-state={queryState}
      aria-busy={queryState === 'loading' ? true : undefined}
    >
      {frame.mode === 'notice' ? (
        <p className="vx-ticker-notice">{frame.notice}</p>
      ) : (
        <>
          {/*
            LA DÉGRADATION D'ABORD, dans le DOM comme à l'écran. Elle QUALIFIE
            les cours qui suivent : la lire après eux, ce serait les avoir déjà
            lus sans elle. C'est le seul bloc que le LOT-A1 ne déplace pas.
          */}
          {frame.caveat !== null ? (
            <p className="vx-ticker-caveat" data-ticker-slot="caveat" data-caveat={frame.caveat}>
              {frame.caveat}
            </p>
          ) : null}
          {/*
            Nature, fraîcheur et heure IDENTIFIENT l'instantané. Elles restent
            AVANT la liste dans le DOM — donc lues avant les cours par un
            lecteur d'écran — et ne passent à droite que par le placement de
            grille en CSS, comme le posent les planches. Aucun élément
            focalisable ici : l'ordre de tabulation ne s'en trouve donc pas
            dissocié de l'ordre visuel.
          */}
          <div className="vx-ticker-meta" data-ticker-slot="meta">
            <p
              className="vx-ticker-nature"
              data-vx-nature={populationKey}
              data-vx-tone={nature.tone}
            >
              {nature.label}
            </p>
            {/*
              LOT V1 — CE LIBELLÉ ÉCRIVAIT « instantané v— ».

              Le tiret y tenait lieu de numéro de version, et se lisait comme
              un numéro : rien ne disait au lecteur que le serveur n'avait
              PUBLIÉ aucune version. Le défaut vivait dans le shell, donc sur
              les douze destinations, et échappait à la porte anti-tiret ambigu
              parce que `src/shell` n'était dans son périmètre — ce que ce même
              lot corrige.

              L'absence est maintenant DITE, avec la formulation que la
              primitive de provenance emploie déjà partout ailleurs.
            */}
            <p className="vx-ticker-freshness">
              <FreshnessBadge
                ageSeconds={data?.age_seconds ?? null}
                sourceLabel={
                  data?.snapshot_version == null
                    ? 'instantané, version non publiée'
                    : `instantané v${data.snapshot_version}`
                }
              />
            </p>
            {/*
              L'HEURE DE L'INSTANTANÉ. `dateTime` porte la chaîne servie telle
              quelle : la même vérité, lisible par un outil. Rien n'est rendu
              quand le serveur n'a pas daté son instantané — une heure de repli
              serait une valeur que personne n'a servie.
            */}
            {horloge !== null && data?.as_of != null ? (
              <time className="vx-ticker-clock" data-testid="ticker-clock" dateTime={data.as_of}>
                {horloge}
              </time>
            ) : null}
          </div>
          {/*
            Région défilante : `tabIndex` obligatoire, sinon son contenu est
            inatteignable au clavier (axe `scrollable-region-focusable`,
            impact « serious », seuil zéro).
          */}
          <ul className="vx-ticker-list" data-ticker-slot="list" tabIndex={0}>
            {entries.map((entry) => (
              <li
                key={entry.ticker.ticker}
                className="vx-ticker-item"
                data-group={entry.group}
                data-testid={`ticker-${entry.ticker.ticker}`}
              >
                <span className="vx-ticker-symbol">{entry.ticker.ticker}</span>
                <span className="vx-ticker-close">
                  {frDecimal(entry.ticker.last_close)}
                  {entry.ticker.currency !== null ? (
                    <span className="vx-ticker-currency"> {entry.ticker.currency}</span>
                  ) : null}
                </span>
                {/*
                  Le signe est DANS la chaîne du serveur (« +1,23 » / « -0,40 ») :
                  la couleur n'est donc jamais le seul vecteur, comme l'exige
                  `.claude/rules/frontend.md`.
                */}
                <span className="vx-ticker-return">{frDecimal(entry.ticker.return_1d_pct)} %</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
