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
 * 4. AUCUNE PORTÉE APPLICATIVE. La population et la fraîcheur affichées sont
 *    celles de CE snapshot, et elles sont portées PAR le ticker. Les poser
 *    dans le coin haut-droit (point 5) leur donnerait une portée « Vertex »
 *    qu'aucune source ne publie : il n'existe ni mode de données global, ni
 *    fraîcheur globale. Le point 5 reste donc vide, et c'est délibéré.
 *
 * Le ticker couvre ses huit états : sans instantané, sans session, hors ligne
 * ou en erreur, il n'affiche AUCUN chiffre — il dit ce qui manque. Un ticker
 * qui garderait ses derniers cours en cas de coupure présenterait un cache
 * comme du courant, ce que `.claude/rules/financial-safety.md` interdit.
 */

/** Ce que la bande a le droit d'afficher, dérivé du seul état observé. */
export type TickerMode = 'values' | 'notice';

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

export function ShellTicker() {
  const query = useMarketsOverview();
  const queryState = pageStateOf(query);
  const data = query.data;
  const frame = tickerFrameOf(queryState, data?.data_state, data?.state);

  const entries = frame.mode === 'values' && data !== undefined ? flattenTickers(data.sectors) : [];
  const { key: populationKey, nature } = resolvePopulationNature(data?.population ?? null);

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
            Nature et fraîcheur d'ABORD, avant le premier chiffre : la lecture
            en français va de gauche à droite, et un cours lu avant son
            étiquette est un cours lu sans elle.
          */}
          <p className="vx-ticker-nature" data-vx-nature={populationKey} data-vx-tone={nature.tone}>
            {nature.label}
          </p>
          <p className="vx-ticker-freshness">
            <FreshnessBadge
              ageSeconds={data?.age_seconds ?? null}
              sourceLabel={`instantané v${data?.snapshot_version ?? '—'}`}
            />
          </p>
          {frame.caveat !== null ? (
            <p className="vx-ticker-caveat" data-caveat={frame.caveat}>
              {frame.caveat}
            </p>
          ) : null}
          {/*
            Région défilante : `tabIndex` obligatoire, sinon son contenu est
            inatteignable au clavier (axe `scrollable-region-focusable`,
            impact « serious », seuil zéro).
          */}
          <ul className="vx-ticker-list" tabIndex={0}>
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
