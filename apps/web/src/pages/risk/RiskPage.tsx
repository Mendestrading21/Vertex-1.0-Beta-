import { useRiskMatrix } from '../../api/decisionApi.ts';
import { pageStateOf } from '../../api/hooks.ts';
import { AuthRequiredNotice } from '../../components/AuthRequiredNotice.tsx';
import { DataStateBoundary } from '../../components/DataStateBoundary.tsx';
import { SyntheticBanner } from '../../components/SyntheticBanner.tsx';
import { CorrelationMatrix } from './CorrelationMatrix.tsx';
import { riskViewOf } from './riskView.ts';
import type { RiskView } from './riskView.ts';

/**
 * Page Risques — question : « Qu'est-ce qui bouge ensemble dans mon
 * périmètre, et qu'est-ce qui protège de quoi ? »
 *
 * Tout vient du snapshot `risk_matrix/global` publié par le worker et relayé
 * verbatim par l'API. L'interface ne calcule AUCUN coefficient et ne
 * reclasse aucune case : les nombres arrivent en chaînes rendues, les bandes
 * arrivent sous forme de noms.
 *
 * TROIS ÉTATS, JAMAIS CONFONDUS.
 *
 * - `ok` : la matrice est servie ;
 * - `refus` : le worker A publié, mais il n'a PAS pu bâtir la matrice —
 *   périmètre trop court, séances communes insuffisantes, variance nulle. Le
 *   motif et la conclusion française s'affichent. Ce n'est pas un écran vide :
 *   c'est une réponse ;
 * - `empty` : rien n'a jamais été publié, soit qu'aucun périmètre ne soit
 *   déclaré, soit qu'aucune barre n'ait été collectée.
 *
 * L'AVERTISSEMENT DE SYNCHRONICITÉ EST AFFICHÉ, PAS RANGÉ. Les places ne
 * ferment pas à la même heure : mesuré le 2026-09-01, SPX/N225 tombe à
 * +0,168 parce que Tokyo ferme avant l'ouverture de New York, et non parce
 * que le Japon serait décorrélé du monde. Sans cette phrase à l'écran, un
 * artefact de fuseau se lirait comme un fait de marché.
 */

function RiskFrame({ view }: { readonly view: RiskView }) {
  return (
    <>
      {/*
        Le bandeau est TOUJOURS rendu, avec l'aveu tel quel. Il juge lui-même :
        une population non déclarée ou non reconnue est signalée plutôt que
        passée sous silence — c'est exactement ce qu'un rendu conditionnel sur
        la seule valeur « SYNTHETIC » aurait masqué.
      */}
      <SyntheticBanner population={view.population} />

      <section className="vx-panel" aria-labelledby="vx-risk-matrix-title">
        <header className="vx-panel-head">
          <p className="vx-panel-kicker">Corrélations</p>
          <h2 id="vx-risk-matrix-title">Qu'est-ce qui bouge ensemble ?</h2>
          <p>{view.conclusion}</p>
        </header>

        {view.refusalReason !== null ? (
          // La conclusion du serveur est DÉJÀ dans l'en-tête juste au-dessus :
          // la répéter ici la ferait lire deux fois et donnerait au refus un
          // air d'erreur redoublée. Le bandeau porte donc le seul motif.
          <DataStateBoundary
            state="empty"
            detail={`Aucune matrice n'a pu être construite : ${view.refusalReason}.`}
          />
        ) : (
          <CorrelationMatrix
            instruments={view.instruments}
            matrix={view.matrix}
            bands={view.bands}
          />
        )}

        {view.extremes !== null ? (
          <dl className="vx-risk-extremes">
            <div>
              <dt>Paire la plus liée</dt>
              <dd>
                {view.extremes.mostCorrelated.pair}{' '}
                <strong>{view.extremes.mostCorrelated.value}</strong>
              </dd>
            </div>
            <div>
              <dt>Paire la plus opposée</dt>
              <dd>
                {view.extremes.mostOpposed.pair} <strong>{view.extremes.mostOpposed.value}</strong>
              </dd>
            </div>
          </dl>
        ) : null}

        {view.synchronicityWarning !== null ? (
          <p className="vx-risk-caveat" role="note">
            {view.synchronicityWarning}
          </p>
        ) : null}
      </section>

      <section className="vx-panel" aria-labelledby="vx-risk-coverage-title">
        <header className="vx-panel-head">
          <p className="vx-panel-kicker">Couverture</p>
          <h2 id="vx-risk-coverage-title">Sur quoi cette matrice est-elle bâtie ?</h2>
          <p>
            Le périmètre est DÉCLARÉ, jamais deviné : comparer qui à qui est une décision, pas
            une déduction du code.
          </p>
        </header>

        <dl className="vx-risk-coverage">
          <div>
            <dt>Instruments retenus</dt>
            <dd>
              {view.coverage.retained} sur {view.coverage.perimeterSize} déclarés
            </dd>
          </div>
          <div>
            <dt>Séances communes</dt>
            <dd>
              {view.coverage.commonDays} (minimum déclaré&nbsp;: {view.coverage.minimumDays})
            </dd>
          </div>
          {view.coverage.window !== null ? (
            <div>
              <dt>Fenêtre</dt>
              <dd>{view.coverage.window}</dd>
            </div>
          ) : null}
          <div>
            <dt>Seuils des bandes</dt>
            <dd>
              modéré à partir de {view.coverage.moderateThreshold}, fort à partir de{' '}
              {view.coverage.strongThreshold}
            </dd>
          </div>
        </dl>

        {view.coverage.alignmentLoss.length > 0 ? (
          <div className="vx-risk-alignment">
            <h3>Ce que l'alignement a coûté</h3>
            <p>
              Une séance manquante chez un seul instrument la retire à TOUS : le calcul exige une
              matrice complète et refuse un trou plutôt que de le combler.
            </p>
            <ul>
              {view.coverage.alignmentLoss.map((entry) => (
                <li key={entry.ticker}>
                  <span>{entry.ticker}</span> {entry.lost} séance
                  {entry.lost > 1 ? 's' : ''} perdue{entry.lost > 1 ? 's' : ''}
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {view.coverage.discarded.length > 0 ? (
          <div className="vx-risk-discards">
            <h3>Instruments écartés</h3>
            <ul>
              {view.coverage.discarded.map((entry) => (
                <li key={entry.instrument}>
                  <span>{entry.instrument}</span> {entry.reason}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </section>
    </>
  );
}

export function RiskPage() {
  const query = useRiskMatrix();
  const state = pageStateOf(query);
  const data = query.data;
  const view = data === undefined ? null : riskViewOf(data);

  return (
    <article className="vx-page" aria-labelledby="vx-page-title-risk">
      <div className="vx-page-header">
        <h1 id="vx-page-title-risk">Risques</h1>
        <p className="vx-page-question">
          Qu'est-ce qui bouge ensemble dans mon périmètre, et qu'est-ce qui protège de quoi ?
        </p>
      </div>

      {state === 'auth-required' ? (
        <AuthRequiredNotice />
      ) : state === 'loading' || state === 'offline' || state === 'error' ? (
        <DataStateBoundary
          state={state}
          {...(state === 'offline'
            ? { detail: "L'API locale est injoignable — la matrice ne peut pas être affichée." }
            : state === 'error'
              ? { detail: "Réponse invalide ou inattendue de l'API — aucune matrice affichée." }
              : {})}
        />
      ) : view === null || view.serverState === 'empty' ? (
        <DataStateBoundary
          state="empty"
          detail={`Aucun instantané publié — soit aucun périmètre n'est déclaré, soit aucune barre n'a encore été collectée (raison serveur : ${
            data?.reason ?? 'non fournie'
          }). Rien n'est inventé à la place.`}
        />
      ) : view.serverState === 'stale' ? (
        <DataStateBoundary
          state="stale"
          {...(typeof data?.reason === 'string' ? { detail: data.reason } : {})}
        >
          <RiskFrame view={view} />
        </DataStateBoundary>
      ) : (
        <RiskFrame view={view} />
      )}
    </article>
  );
}
