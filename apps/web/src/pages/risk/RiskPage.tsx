import { useState } from 'react';

import type { RiskMatrixResponse } from '../../api/client.ts';
import { useRiskMatrix } from '../../api/decisionApi.ts';
import { pageStateOf } from '../../api/hooks.ts';
import { AuthRequiredNotice } from '../../components/AuthRequiredNotice.tsx';
import { Card } from '../../components/Card.tsx';
import { DataStateBoundary } from '../../components/DataStateBoundary.tsx';
import { SyntheticBanner } from '../../components/SyntheticBanner.tsx';
import { CorrelationMatrix } from './CorrelationMatrix.tsx';
import { InstrumentInspector, MatrixInspector } from './RiskInspector.tsx';
import {
  AbsentRiskModule,
  AlignmentModule,
  CoverageModule,
  DiscardsModule,
  DrawdownModule,
  ExtremesModule,
  RegisterConcentrationModule,
} from './RiskModules.tsx';
import { riskModule } from './riskModules.ts';
import { riskViewOf } from './riskView.ts';
import type { RiskView } from './riskView.ts';

/**
 * Page Risques (`TL / 09`) — question : « Qu'est-ce qui bouge ensemble dans
 * mon périmètre, et qu'est-ce qui protège de quoi ? »
 *
 * Tout ce qui est CORRÉLATION vient du snapshot `risk_matrix/global` publié
 * par le worker et relayé verbatim par l'API. L'interface ne calcule AUCUN
 * coefficient et ne reclasse aucune case : les nombres arrivent en chaînes
 * rendues, les bandes arrivent sous forme de noms.
 *
 * LOT-A6 — LA PLANCHE §9 EN ENTIER. `pages-09-10-risks-catalysts.png`
 * (moitié gauche) compose dix-neuf modules. Sept sont SERVIS : la matrice en
 * DOMINANTE (`REFONTE_TITANIUM_LEDGER.md` §4), les paires extrêmes et
 * l'avertissement de synchronicité, la couverture, le coût de l'alignement,
 * les instruments écartés — tous du même snapshot — puis la concentration du
 * registre manuel et le drawdown de sa performance, lus par les hooks des
 * pages propriétaires. Douze n'ont ni source ni contrat : score de risque,
 * VaR, risque relatif, volatilité, liquidité, rotation, chocs, facteurs,
 * budget de risque, radar, registre des risques, journal d'alertes.
 * `PAGE_ARBITRATION.md` le mesure : aucune source ne publie sévérité ni
 * horizon par risque — et le contrat interdit un score global dérivé de
 * mesures partielles. Ils tiennent leur place avec le motif de leur absence.
 *
 * TROIS ÉTATS DE MATRICE, JAMAIS CONFONDUS.
 *
 * - `ok` : la matrice est servie ;
 * - `refus` : le worker A publié, mais il n'a PAS pu bâtir la matrice —
 *   périmètre trop court, séances communes insuffisantes, variance nulle. Le
 *   motif et la conclusion française s'affichent dans la dominante. Ce n'est
 *   pas un écran vide : c'est une réponse ;
 * - `empty` : rien n'a jamais été publié, soit qu'aucun périmètre ne soit
 *   déclaré, soit qu'aucune barre n'ait été collectée. La planche reste
 *   composée : la dominante porte l'aveu, les autres modules leur état.
 *
 * L'AVERTISSEMENT DE SYNCHRONICITÉ EST AFFICHÉ, PAS RANGÉ. Les places ne
 * ferment pas à la même heure : mesuré le 2026-09-01, SPX/N225 tombe à
 * +0,168 parce que Tokyo ferme avant l'ouverture de New York, et non parce
 * que le Japon serait décorrélé du monde. Sans cette phrase à l'écran, un
 * artefact de fuseau se lirait comme un fait de marché.
 *
 * L'INSPECTEUR MONTRE L'INSTRUMENT OUVERT depuis la matrice — coefficients
 * avec chacun, bande publiée, séances perdues, motif d'écart — sinon la
 * vérité du snapshot.
 */

function MatrixModule({
  data,
  view,
  selected,
  onSelect,
}: {
  readonly data: RiskMatrixResponse;
  readonly view: RiskView | null;
  readonly selected: string | null;
  readonly onSelect: (ticker: string) => void;
}) {
  const module = riskModule('correlations');
  return (
    <Card
      rank="dominant"
      kicker="Corrélations publiées"
      title={module.title}
      titleId="vx-risk-matrix-title"
      className="vx-risk-matrix-card"
      aside={view === null ? undefined : <>{view.instruments.length} instrument(s) · population {view.population}</>}
      footer={<>rendements quotidiens sur les séances communes ; coefficients et bandes publiés par le worker, jamais recalculés</>}
    >
      {view === null || view.serverState === 'empty' ? (
        <DataStateBoundary
          state="empty"
          detail={`Aucun instantané publié — soit aucun périmètre n'est déclaré, soit aucune barre n'a encore été collectée (raison serveur : ${
            data.reason ?? 'non fournie'
          }). Rien n'est inventé à la place.`}
        />
      ) : (
        <>
          <p className="vx-module-sentence" data-testid="risk-conclusion">
            {view.conclusion}
          </p>
          {view.refusalReason !== null ? (
            // La conclusion du serveur est DÉJÀ juste au-dessus : la répéter
            // ici la ferait lire deux fois. Le bandeau porte le seul motif.
            <DataStateBoundary state="empty" detail={`Aucune matrice n'a pu être construite : ${view.refusalReason}.`} />
          ) : (
            <CorrelationMatrix instruments={view.instruments} matrix={view.matrix} bands={view.bands} selected={selected} onSelect={onSelect} />
          )}
        </>
      )}
    </Card>
  );
}

function RiskBoard({ data, view }: { readonly data: RiskMatrixResponse; readonly view: RiskView | null }) {
  const [selected, setSelected] = useState<string | null>(null);
  const opened = view !== null && selected !== null && view.instruments.some((entry) => entry.ticker === selected) ? selected : null;
  return (
    <>
      <div className="vx-risk-grid vx-board" data-testid="risk-grid">
        <AbsentRiskModule id="risk-score" />
        <AbsentRiskModule id="var-cvar" />
        <div data-module="max-drawdown">
          <DrawdownModule />
        </div>
        <AbsentRiskModule id="benchmark-relative" />

        <AbsentRiskModule id="volatility" />
        <div data-module="concentration">
          <RegisterConcentrationModule />
        </div>
        <AbsentRiskModule id="liquidity" />

        <div data-module="correlations">
          <MatrixModule
            data={data}
            view={view}
            selected={opened}
            onSelect={(ticker) => {
              setSelected((previous) => (previous === ticker ? null : ticker));
            }}
          />
        </div>
        <AbsentRiskModule id="turnover" />
        <div data-module="extremes">
          {view === null ? (
            <Card rank="quiet" kicker="Publiées avec la matrice" title={riskModule('extremes').title} titleId="vx-risk-extremes-title">
              <p className="vx-module-sentence" role="status">
                Matrice non publiée : aucune paire à nommer.
              </p>
            </Card>
          ) : (
            <ExtremesModule view={view} />
          )}
        </div>

        <AbsentRiskModule id="stress-loss" />
        <AbsentRiskModule id="factor-exposures" />
        <AbsentRiskModule id="risk-budget" />
        <AbsentRiskModule id="radar" />

        <div data-module="coverage">
          {view === null ? (
            <Card rank="quiet" kicker="Périmètre déclaré" title={riskModule('coverage').title} titleId="vx-risk-coverage-title">
              <p className="vx-module-sentence" role="status">
                Matrice non publiée : aucune couverture à décrire.
              </p>
            </Card>
          ) : (
            <CoverageModule view={view} />
          )}
        </div>
        <div data-module="alignment">
          {view === null ? (
            <Card rank="quiet" kicker="Séances perdues" title={riskModule('alignment').title} titleId="vx-risk-alignment-title">
              <p className="vx-module-sentence" role="status">
                Matrice non publiée.
              </p>
            </Card>
          ) : (
            <AlignmentModule view={view} />
          )}
        </div>
        <div data-module="discards">
          {view === null ? (
            <Card rank="quiet" kicker="Écartés avec leur raison" title={riskModule('discards').title} titleId="vx-risk-discards-title">
              <p className="vx-module-sentence" role="status">
                Matrice non publiée.
              </p>
            </Card>
          ) : (
            <DiscardsModule view={view} />
          )}
        </div>
        <AbsentRiskModule id="risk-register" />
        <AbsentRiskModule id="alert-log" />
      </div>

      {opened === null || view === null ? (
        <MatrixInspector data={data} view={view} />
      ) : (
        <InstrumentInspector
          ticker={opened}
          view={view}
          onClose={() => {
            setSelected(null);
          }}
        />
      )}
    </>
  );
}

export function RiskPage() {
  const query = useRiskMatrix();
  const state = pageStateOf(query);
  const data = query.data;
  const view = data === undefined || data.state === 'empty' ? null : riskViewOf(data);

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
      ) : data === undefined ? (
        <DataStateBoundary state="error" detail="Réponse absente — rien n'est affiché à la place." />
      ) : (
        <>
          {/*
            Le bandeau est TOUJOURS rendu quand un contenu est publié, avec
            l'aveu tel quel. Il juge lui-même : une population non déclarée ou
            non reconnue est signalée plutôt que passée sous silence.
          */}
          {view !== null ? <SyntheticBanner population={view.population} /> : null}
          {view !== null && view.serverState === 'stale' ? (
            <DataStateBoundary state="stale" {...(typeof data.reason === 'string' ? { detail: data.reason } : {})} />
          ) : null}
          <RiskBoard data={data} view={view} />
        </>
      )}
    </article>
  );
}
