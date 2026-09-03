import { Card } from '../../components/Card.tsx';
import { Metric } from '../../components/Metric.tsx';
import { signGroupOfText } from '../../components/widgets/KpiDelta.tsx';
import { portfolioModule } from './portfolioModules.ts';
import type { CurrencyBlockView, ValuationContentView } from './portfolioView.ts';

/**
 * Module « Valorisation publiée » (planche §7) — chiffres = chaînes serveur
 * VERBATIM, avec provenance (calcul, méthode, hash) et `as_of` du snapshot.
 *
 * LOT P4 — POURQUOI CE MODULE PASSE DE LA LISTE À LA BANDE DE MESURES. Les
 * trois chiffres qui répondent à « que vaut ce portefeuille » étaient des
 * puces de phrase : ils se lisaient à la même taille que leur libellé, et
 * l'œil ne les trouvait pas. Ce sont les mesures de tête de la page ; elles
 * prennent la forme `Metric` du socle (libellé en capitales, valeur en taille
 * d'affichage, unité servie à côté). Rien n'est ajouté ni retiré : les mêmes
 * chaînes serveur, la même provenance, le même aveu sur les espèces.
 *
 * LE SIGNE VIENT DU SERVEUR, PAS D'UNE DÉDUCTION. La couleur de sens n'est
 * portée que si la chaîne servie porte elle-même son signe
 * (`signGroupOfText`, socle v2) : une chaîne positive publiée SANS « + » n'a
 * pas de signe publié, donc pas de couleur. Deux règles de signe sur la même
 * page se contrediraient ; il n'y en a qu'une.
 *
 * - Le badge « Marks : DONNÉES SYNTHÉTIQUES » est TOUJOURS rendu tant que la
 *   population des marques publiée est SYNTHETIC (elle l'est par contrat en
 *   1.0 Beta) : une marque synthétique ne se présente jamais comme réelle.
 * - Le solde d'espèces n'existe PAS dans le snapshot de valorisation publié :
 *   il est affiché comme absent avec sa raison, jamais recalculé côté client
 *   depuis le journal (aucun total TypeScript). Le module « Espèces » de la
 *   planche porte le même aveu à sa place.
 */

function ValueMetric({
  label,
  status,
  reason,
  value,
  currency,
  testId,
}: {
  readonly label: string;
  readonly status: string | null;
  readonly reason: string | null;
  readonly value: string | null;
  readonly currency: string;
  readonly testId: string;
}) {
  const served = status === 'OK' ? value : null;
  const raison = `${status ?? 'ABSENT'}${reason !== null ? ` — ${reason}` : ''}`;
  return (
    <Metric
      label={label}
      value={served}
      {...(served === null ? {} : { unit: currency, sign: signGroupOfText(served) })}
      absentLabel={`${label} : ${raison}`}
      {...(served === null ? { note: <span className="vx-cell-absent">{raison}</span> } : {})}
      testId={testId}
    />
  );
}

/**
 * Les espèces, dites comme elles sont : non publiées. Le compte d'événements
 * de trésorerie du journal est un DÉNOMBREMENT servi — quand il n'est pas
 * publié, il est dit non publié. Écrire « 0 événement » là où le serveur ne
 * publie rien inventerait un fait de journal.
 */
function CashAbsence({ cashEvents }: { readonly cashEvents: number | null }) {
  return (
    <p className="vx-pf-cash">
      <span className="vx-metric-label">Espèces</span>{' '}
      <span className="vx-cell-absent" data-testid="pf-cash-absent">
        non publié — le snapshot de valorisation ne contient pas de solde d'espèces et l'interface
        n'en calcule aucun (
        {cashEvents === null
          ? 'nombre d’événements de trésorerie non publié'
          : `${cashEvents} événement(s) de trésorerie au journal`}
        )
      </span>
    </p>
  );
}

function ValueBlock({
  block,
  lotMethod,
}: {
  readonly block: CurrencyBlockView;
  readonly lotMethod: string | null;
}) {
  return (
    <div className="vx-pf-summary-block">
      <h3>
        Devise <code>{block.currency}</code>
      </h3>
      <div className="vx-metrics-row">
        <ValueMetric
          label="Valeur marquée des lots ouverts"
          status={block.concentrationStatus}
          reason={block.concentrationReason}
          value={block.totalValue}
          currency={block.currency}
          testId="pf-value-total"
        />
        <ValueMetric
          label="P&L latent (marques synthétiques)"
          status={block.unrealizedStatus}
          reason={block.unrealizedReason}
          value={block.totalUnrealized}
          currency={block.currency}
          testId="pf-value-unrealized"
        />
        <ValueMetric
          label={`P&L réalisé (journal, ${lotMethod ?? 'méthode non publiée'})`}
          status={block.realizedStatus}
          reason={block.realizedReason}
          value={block.totalRealized}
          currency={block.currency}
          testId="pf-value-realized"
        />
      </div>
      <p className="vx-pf-provenance">
        Provenance :{' '}
        {block.unrealizedCalculation !== null ? (
          <>
            <code>{block.unrealizedCalculation.calculationId ?? 'non publié'}</code> (
            {block.unrealizedCalculation.engineVersion ?? 'version non publiée'},{' '}
            <code className="vx-pf-hash">{block.unrealizedCalculation.inputHash ?? 'hachage non publié'}</code>)
          </>
        ) : (
          'aucun calcul latent publié'
        )}
        {' · '}
        {block.realizedCalculation !== null ? (
          <>
            <code>{block.realizedCalculation.calculationId ?? 'non publié'}</code> (
            {block.realizedCalculation.engineVersion ?? 'version non publiée'})
          </>
        ) : (
          'aucun calcul réalisé publié'
        )}
      </p>
    </div>
  );
}

export function PortfolioSummary({ valuation }: { readonly valuation: ValuationContentView }) {
  const module = portfolioModule('value');
  return (
    <Card
      rank="quiet"
      kicker="Snapshot du worker"
      title={module.title}
      titleId="vx-pf-summary-title"
      className="vx-pf-value"
      aside={
        valuation.markPopulation === 'SYNTHETIC' ? (
          <span className="vx-badge vx-badge-synthetic" data-testid="pf-marks-badge">
            Marks : DONNÉES SYNTHÉTIQUES
          </span>
        ) : (
          <span className="vx-badge vx-badge-warning" data-testid="pf-marks-badge">
            Population de marques : {valuation.markPopulation ?? 'inconnue'}
          </span>
        )
      }
      footer={
        <>
          <code>as_of</code>{' '}
          {valuation.asOf !== null ? (
            <time dateTime={valuation.asOf}>{valuation.asOf}</time>
          ) : (
            'non publié'
          )}
          {' · '}lots <code>{valuation.lotMethod ?? 'non publiés'}</code>
          {' · '}moteur <code>{valuation.engineVersion ?? 'non publié'}</code>
          {' · '}marques :{' '}
          {valuation.marks.status === 'OK' ? (
            <>
              snapshot marchés v{valuation.marks.snapshotVersion ?? 'non publiée'} (
              {valuation.marks.tickersMarked ?? 'nombre non publié'} tickers,{' '}
              {valuation.marks.asOf !== null ? (
                <time dateTime={valuation.marks.asOf}>{valuation.marks.asOf}</time>
              ) : (
                'as_of non publié'
              )}
              )
            </>
          ) : (
            <span className="vx-cell-absent">
              {valuation.marks.status ?? 'ABSENT'}
              {valuation.marks.reason !== null ? ` — ${valuation.marks.reason}` : null}
            </span>
          )}
        </>
      }
    >
      {valuation.blocks.length === 0 ? (
        <p className="vx-cell-absent">
          Aucune position dérivée du journal — aucun agrégat n'est fabriqué.
        </p>
      ) : (
        <>
          {/* L'aveu sur les espèces est HORS de la grille des devises : il ne
              concerne aucune devise en particulier, et compté comme une
              cellule de plus il ouvrait une seconde colonne qui écrasait la
              bande de mesures (mesuré sur capture 1440). */}
          <div className="vx-pf-summary-grid" data-testid="pf-summary-grid">
            {valuation.blocks.map((block) => (
              <ValueBlock key={block.currency} block={block} lotMethod={valuation.lotMethod} />
            ))}
          </div>
          <CashAbsence cashEvents={valuation.coverage.cashEvents} />
        </>
      )}
    </Card>
  );
}
