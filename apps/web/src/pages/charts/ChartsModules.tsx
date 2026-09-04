import { ArcGauge } from '../../components/widgets/ArcGauge.tsx';
import { DayBars } from '../../components/widgets/DayBars.tsx';
import type { DayBarEntry } from '../../components/widgets/DayBars.tsx';
import { MultiSeriesArea } from '../../components/widgets/MultiSeriesArea.tsx';
import type { MultiSeries, MultiTone } from '../../components/widgets/MultiSeriesArea.tsx';
import { SparkFigure } from '../../components/widgets/SparkFigure.tsx';
import { StatusChip } from '../../components/widgets/StatusChip.tsx';
import { Widget } from '../../components/widgets/Widget.tsx';
import type { BarsView } from '../analysis/analysisView.ts';
import { RebasedComparison } from './RebasedComparison.tsx';
import { chartsModule, indicatorFamilyOf } from './chartsView.ts';
import type { ComparisonView, IndicatorBlockView } from './chartsView.ts';

/**
 * Les modules SERVIS de la planche §8, hors la dominante (le cadre graphique,
 * porté par la page).
 *
 * LOT P5 — CE QUE LE SERVEUR PUBLIE DEPUIS S6. `indicators.overlays`
 * (`sma`, `ema`, `bollinger_bands`) et `indicators.oscillators` (`rsi`,
 * `macd`) arrivent RENDUS : chaque valeur est une chaîne décimale, chaque
 * série est alignée sur la fin des séances par le worker, chaque bloc porte
 * sa méthode, ses paramètres et sa lignée. La page ne lisse rien, ne moyenne
 * rien, ne réaligne rien.
 *
 * POURQUOI DEUX FORMES POUR TROIS LIGNES. Les bandes de Bollinger sortent
 * d'une MÊME liste de points : elles partagent leurs séances et se
 * superposent honnêtement. Les trois lignes du MACD commencent à des séances
 * différentes (leurs fenêtres diffèrent) : les superposer exigerait de les
 * réaligner dans le navigateur, ce que `references/charts.md` interdit. Elles
 * prennent donc chacune leur figure. `indicatorBlockOf` CONSTATE le fait
 * (`aligned`) ; il ne le corrige pas.
 */

/** Teintes de série de la planche : `macro` est l'accent déclaré de la page. */
const SERIES_TONES: readonly MultiTone[] = ['macro', 'silver', 'option'];

function toneAt(index: number): MultiTone {
  return SERIES_TONES[index % SERIES_TONES.length] ?? 'macro';
}

/**
 * Ce qu'un bloc d'indicateur montre quand il n'est pas servi.
 *
 * Un échantillon insuffisant n'est pas une panne : c'est le moteur qui REFUSE
 * de calculer une fenêtre partielle. Son détail serveur est repris tel quel —
 * il dit combien de clôtures manquent.
 */
function BlockAbsence({ block }: { readonly block: IndicatorBlockView }) {
  if (block.kind === 'refused') {
    return (
      <p className="vx-w2-absent" role="status">
        <StatusChip label={block.status} tone="warning" />{' '}
        {block.detail ?? 'aucun détail publié'} — aucune valeur de remplacement.
      </p>
    );
  }
  if (block.kind === 'unreadable') {
    return (
      <p className="vx-w2-absent" role="status">
        Bloc publié dans une forme que cette page ne sait pas lire — rien n’est affiché à la place.
      </p>
    );
  }
  return (
    <p className="vx-w2-absent" role="status">
      Aucun bloc publié pour cet indicateur dans ce dossier.
    </p>
  );
}

/** Paramètres, méthode et lignée SERVIS d'un bloc, en pied de module. */
function BlockProvenance({ block }: { readonly block: IndicatorBlockView }) {
  if (block.kind !== 'served') {
    return null;
  }
  return (
    <>
      {block.parameters.map((parametre) => `${parametre.label} ${parametre.value}`).join(' · ')}
      {block.parameters.length === 0 ? null : ' · '}
      unité <code>{block.unit}</code>
      {block.method === null ? null : (
        <>
          {' · '}méthode {block.method}
        </>
      )}
      {block.calculationId === null ? null : (
        <>
          {' · '}
          <code>{block.calculationId}</code>
        </>
      )}
      {block.engineVersion === null ? null : ` (${block.engineVersion})`}
    </>
  );
}

/** Une ligne servie, en aire à dégradé, avec sa table équivalente. */
function LineFigure({
  block,
  index,
  caption,
}: {
  readonly block: Extract<IndicatorBlockView, { kind: 'served' }>;
  readonly index: number;
  readonly caption: string;
}) {
  const ligne = block.lines[index];
  if (ligne === undefined) {
    return null;
  }
  return (
    <SparkFigure
      closes={ligne.values}
      labels={ligne.tradingDays}
      // Une moyenne mobile n'est ni « en hausse » ni « stable » : c'est une
      // mesure, pas une variation. Aucun signe n'est donc affirmé.
      sign={null}
      caption={caption}
      unit={block.unit}
      windowLabel={`${ligne.values.length} séances servies`}
      variant="area"
      tone={index === 0 ? 'macro' : 'silver'}
    />
  );
}

// ---------------------------------------------------------------------------

const VOLUME_WINDOW = 10;

/** Rang du mois dans une date ISO servie (`2026-09-02` → `09-02`). */
const SHORT_DAY_FROM = 5;

export function VolumeModule({ bars }: { readonly bars: BarsView | null }) {
  const module = chartsModule('volume');
  const servies = bars === null ? [] : bars.bars.slice(-VOLUME_WINDOW);
  const entries: readonly DayBarEntry[] = servies.map((barre) => ({
    key: barre.tradingDay,
    label: barre.tradingDay,
    // L'axe porte le mois et le jour ; la séance SERVIE entière reste dans
    // l'infobulle et dans la table équivalente. On raccourcit une DATE, pas
    // une valeur.
    shortLabel: barre.tradingDay.slice(SHORT_DAY_FROM),
    value: String(barre.volume),
  }));
  return (
    <Widget
      id="volume"
      size={module.size}
      kicker="Publié barre à barre"
      title={module.title}
      titleId="vx-charts-volume-title"
      state="ready"
      footer={<>titres échangés, entiers serveur ; les {VOLUME_WINDOW} dernières séances servies</>}
    >
      <DayBars
        entries={entries}
        unit="titres"
        ariaLabel="Volume par séance servie"
        emptyLabel="Aucun volume publié : aucune barre tracée."
      />
    </Widget>
  );
}

// ---------------------------------------------------------------------------

export function OverlaysModule({
  indicators,
}: {
  readonly indicators: Readonly<Record<string, unknown>> | null | undefined;
}) {
  const module = chartsModule('overlays');
  const [sma, ema, bollinger] = indicatorFamilyOf(indicators, 'overlays', [
    'sma',
    'ema',
    'bollinger_bands',
  ]);
  return (
    <Widget
      id="overlays"
      size={module.size}
      kicker="Moteur serveur (S6)"
      title={module.title}
      titleId="vx-charts-overlays-title"
      state="ready"
      footer={<>séries rendues par le worker ; aucune moyenne n’est calculée dans le navigateur</>}
    >
      <div className="vx-charts-figures">
        <section aria-labelledby="vx-charts-sma-title">
          <h4 id="vx-charts-sma-title">Moyenne mobile simple</h4>
          {sma?.kind === 'served' ? (
            <>
              <LineFigure block={sma} index={0} caption="SMA servie" />
              <p className="vx-charts-provenance">
                <BlockProvenance block={sma} />
              </p>
            </>
          ) : (
            <BlockAbsence block={sma ?? { kind: 'none', id: 'sma' }} />
          )}
        </section>

        <section aria-labelledby="vx-charts-ema-title">
          <h4 id="vx-charts-ema-title">Moyenne mobile exponentielle</h4>
          {ema?.kind === 'served' ? (
            <>
              <LineFigure block={ema} index={0} caption="EMA servie" />
              <p className="vx-charts-provenance">
                <BlockProvenance block={ema} />
              </p>
            </>
          ) : (
            <BlockAbsence block={ema ?? { kind: 'none', id: 'ema' }} />
          )}
        </section>

        <section aria-labelledby="vx-charts-bollinger-title" className="vx-charts-figure-wide">
          <h4 id="vx-charts-bollinger-title">Bandes de Bollinger</h4>
          {bollinger?.kind === 'served' && bollinger.aligned ? (
            <>
              <MultiSeriesArea
                series={bollinger.lines.map(
                  (ligne, index): MultiSeries => ({
                    key: ligne.key,
                    label: ligne.label,
                    points: ligne.values,
                    tone: toneAt(index),
                  }),
                )}
                xLabels={bollinger.lines[0]?.tradingDays ?? []}
                ariaLabel="Bandes de Bollinger servies"
                caption="Bandes servies sur les séances communes"
                unit={bollinger.unit}
                windowLabel={`${bollinger.lines[0]?.values.length ?? 0} séances servies`}
              />
              <p className="vx-charts-provenance">
                <BlockProvenance block={bollinger} />
              </p>
            </>
          ) : bollinger?.kind === 'served' ? (
            <p className="vx-w2-absent" role="status">
              Les bandes publiées ne partagent pas leurs séances : elles ne sont pas superposées —
              les aligner ici produirait une comparaison que personne n’a publiée.
            </p>
          ) : (
            <BlockAbsence block={bollinger ?? { kind: 'none', id: 'bollinger_bands' }} />
          )}
        </section>
      </div>
    </Widget>
  );
}

// ---------------------------------------------------------------------------

/**
 * Bornes de l'échelle `index_0_100` — DÉCLARÉES PAR L'UNITÉ SERVIE, jamais
 * mesurées. Le serveur publie `unit: "index_0_100"` : la valeur servie EST sa
 * position sur cette échelle, l'arc n'en dérive aucune. Si l'unité change, la
 * forme est refusée plutôt que réinterprétée.
 */
const INDEX_UNIT = 'index_0_100';
const INDEX_BOUNDS = { min: '0', max: '100' } as const;

export function RsiModule({
  indicators,
}: {
  readonly indicators: Readonly<Record<string, unknown>> | null | undefined;
}) {
  const module = chartsModule('rsi');
  const [rsi] = indicatorFamilyOf(indicators, 'oscillators', ['rsi']);
  const ligne = rsi?.kind === 'served' ? rsi.lines[0] : undefined;
  const surEchelle = rsi?.kind === 'served' && rsi.unit === INDEX_UNIT;
  return (
    <Widget
      id="rsi"
      size={module.size}
      kicker="Moteur serveur (S6)"
      title={module.title}
      titleId="vx-charts-rsi-title"
      state="ready"
      footer={
        rsi?.kind === 'served' ? <BlockProvenance block={rsi} /> : <>force relative publiée par le worker</>
      }
    >
      {rsi?.kind === 'served' && ligne !== undefined ? (
        <div className="vx-charts-figures">
          {surEchelle ? (
            <ArcGauge
              label={`Dernière valeur servie · ${rsi.lastTradingDay ?? 'séance non publiée'}`}
              valuePct={ligne.last}
              valueText={ligne.last}
              unit={rsi.unit}
              boundsText={INDEX_BOUNDS}
              thresholds={[]}
              tone="macro"
              status="OK"
              {...(rsi.method === null ? {} : { method: rsi.method })}
            />
          ) : (
            <p className="vx-w2-absent" role="status">
              Unité servie <code>{rsi.unit}</code> : hors de l’échelle bornée que l’arc exige,
              aucune jauge n’est tracée.
            </p>
          )}
          <LineFigure block={rsi} index={0} caption="RSI servi" />
        </div>
      ) : (
        <BlockAbsence block={rsi ?? { kind: 'none', id: 'rsi' }} />
      )}
    </Widget>
  );
}

// ---------------------------------------------------------------------------

export function MacdModule({
  indicators,
}: {
  readonly indicators: Readonly<Record<string, unknown>> | null | undefined;
}) {
  const module = chartsModule('macd');
  const [macd] = indicatorFamilyOf(indicators, 'oscillators', ['macd']);
  return (
    <Widget
      id="macd"
      size={module.size}
      kicker="Moteur serveur (S6)"
      title={module.title}
      titleId="vx-charts-macd-title"
      state="ready"
      footer={
        macd?.kind === 'served' ? (
          <BlockProvenance block={macd} />
        ) : (
          <>lignes publiées par le worker</>
        )
      }
    >
      {macd?.kind === 'served' ? (
        <>
          <p className="vx-charts-note">
            Les trois lignes publiées commencent à des séances différentes : chacune garde sa
            figure. Les superposer exigerait de les réaligner ici.
          </p>
          <div className="vx-charts-figures">
            {macd.lines.map((ligne, index) => (
              <section key={ligne.key} aria-label={`Ligne servie ${ligne.label}`}>
                <h4>{ligne.label}</h4>
                <LineFigure block={macd} index={index} caption={`${ligne.label} servie`} />
              </section>
            ))}
          </div>
        </>
      ) : (
        <BlockAbsence block={macd ?? { kind: 'none', id: 'macd' }} />
      )}
    </Widget>
  );
}

// ---------------------------------------------------------------------------

export function ComparisonModule({
  comparison,
  instrument,
}: {
  readonly comparison: ComparisonView;
  readonly instrument: string;
}) {
  const module = chartsModule('comparison');
  return (
    <Widget
      id="comparison"
      size={module.size}
      kicker="Rebasée par le serveur"
      title={module.title}
      titleId="vx-charts-comparison-title"
      state="ready"
      footer={
        comparison.kind === 'served' ? (
          <>
            base <code>{comparison.baseValue}</code> · {comparison.commonSessions ?? 'nombre non publié'}{' '}
            séances communes · {comparison.method ?? 'méthode non publiée'}
          </>
        ) : (
          <>deux séries ramenées à la même base sur leurs seules séances communes, par le worker</>
        )
      }
    >
      {comparison.kind === 'served' && comparison.points.length > 1 ? (
        <MultiSeriesArea
          series={[
            {
              key: 'instrument',
              label: instrument,
              points: comparison.points.map((point) => point.instrument),
              tone: 'macro',
            },
            {
              key: 'benchmark',
              label: comparison.benchmark,
              points: comparison.points.map((point) => point.benchmark),
              tone: 'silver',
            },
          ]}
          xLabels={comparison.points.map((point) => point.tradingDay)}
          ariaLabel={`Comparaison base ${comparison.baseValue} entre ${instrument} et ${comparison.benchmark}`}
          caption="Séries rebasées par le serveur, sur leurs seules séances communes"
          unit={comparison.unit}
          windowLabel={`${comparison.points.length} séances communes servies`}
        />
      ) : null}
      <RebasedComparison comparison={comparison} instrument={instrument} />
    </Widget>
  );
}
