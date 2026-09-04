import type { SignGroup } from '../markets/marketsView.ts';
import { Glyph } from './Glyph.tsx';
import type { GlyphName } from './Glyph.tsx';
import { KpiDelta } from './KpiDelta.tsx';
import { SparkFigure } from './SparkFigure.tsx';
import type { SparkTone } from './SparkFigure.tsx';

/**
 * La tuile de mesure : pastille d'icône, libellé, GRAND chiffre servi, unité,
 * variation servie, et — quand une série est publiée — sa figure.
 *
 * POURQUOI ELLE EXISTE (LOT T2). C'est la forme la plus répétée des tableaux
 * de bord de référence, et jusqu'ici Vertex l'assemblait à la main sur chaque
 * page : un `<p>` de libellé, un `<strong>` de valeur, une pastille parfois.
 * Trois assemblages différents pour une même mesure, et aucun endroit où la
 * règle de refus soit écrite UNE fois.
 *
 * CE QU'ELLE REFUSE, et c'est tout l'objet du composant.
 *
 *   1. SANS VALEUR SERVIE, elle DIT l'absence et se dépouille : pas de teinte
 *      (teinter, c'est qualifier un vide), pas de pastille de variation, pas
 *      de figure de série, pas même l'unité — une unité seule n'est pas une
 *      donnée, c'est le décor d'une donnée qui manque.
 *   2. Le SIGNE ne vient jamais de la tuile. `KpiDelta` lit le signe TEXTUEL
 *      de la chaîne servie ; une variation sans signe publié le dit et ne
 *      colore rien. La teinte de la tuile reste celle que l'appelant a
 *      déclarée, jamais dérivée d'une mesure.
 *
 * LE VOCABULAIRE DE TEINTES EXCLUT LE VERT ET LE ROUGE. Ils appartiennent au
 * signe financier SERVI, porté par `KpiDelta` seul. Une pastille d'icône qui
 * les prendrait affirmerait un sens sur une mesure qui n'en a pas — un
 * volume, une couverture, un compte de lignes n'ont pas de direction.
 */
export const KPI_TILE_TONES = ['neutral', 'silver', 'macro', 'option'] as const;
type KpiTileTone = (typeof KPI_TILE_TONES)[number];

interface KpiTileDelta {
  /** Chaîne SERVIE de la variation. `null` = non publiée. */
  readonly value: string | null;
  /** Sens tiré du SIGNE de la chaîne servie, par l'appelant. */
  readonly sign: SignGroup | null;
  /** Période SERVIE de la variation. */
  readonly period: string;
}

export interface KpiTileSeries {
  readonly closes: readonly string[];
  readonly labels?: readonly string[];
  readonly caption: string;
  readonly unit: string;
  /** Période SERVIE, obligatoire — `SparkFigure` refuse sans elle. */
  readonly windowLabel: string;
  readonly tone?: SparkTone;
}

export interface KpiTileProps {
  readonly glyph: GlyphName;
  readonly label: string;
  /** Chaîne SERVIE, rendue verbatim. `null` = mesure non publiée. */
  readonly value: string | null;
  /**
   * Sens financier de LA MESURE elle-même, tiré par l'appelant du SIGNE
   * textuel de la chaîne servie (`signGroupOfText`). `null` ou omis = la
   * mesure n'a pas de signe publié, ou n'en a pas du tout (un volume, une
   * couverture) : aucun attribut, donc aucune couleur.
   *
   * Il colore LE CHIFFRE, jamais la pastille d'icône — celle-ci n'a rien à
   * qualifier.
   */
  readonly valueSign?: SignGroup | null;
  /** Unité SERVIE. Rendue seulement s'il y a une valeur à qualifier. */
  readonly unit: string | null;
  /** Ce que le serveur n'a PAS publié — la phrase exacte, pas un tiret. */
  readonly absentNote: string;
  readonly tone?: KpiTileTone;
  readonly delta?: KpiTileDelta;
  readonly series?: KpiTileSeries;
  readonly testId?: string;
}

export function KpiTile({
  glyph,
  label,
  value,
  valueSign = null,
  unit,
  absentNote,
  tone = 'silver',
  delta,
  series,
  testId,
}: KpiTileProps) {
  // Une absence ne prend aucune teinte : la teinte qualifierait un vide.
  const teinte: KpiTileTone = value === null ? 'neutral' : tone;
  // Un signe SANS mesure ne qualifie rien : l'attribut n'existe pas.
  const signe = value === null ? null : valueSign;

  return (
    <div
      className="vx-w2-kpi"
      data-testid={testId ?? 'kpi-tile'}
      data-tone={teinte}
      data-absent={value === null}
      {...(signe === null ? {} : { 'data-sign': signe })}
    >
      <p className="vx-w2-kpi-head">
        <span className="vx-w2-kpi-badge">
          <Glyph name={glyph} size="var(--vx-space-16)" />
        </span>
        <span className="vx-metric-label">{label}</span>
      </p>

      {value === null ? (
        <p className="vx-cell-absent" data-testid="kpi-tile-absent">
          {absentNote}
        </p>
      ) : (
        <p className="vx-w2-kpi-figure">
          <span className="vx-metric-value" data-testid="kpi-tile-value">
            {value}
          </span>
          {unit === null ? null : (
            <span className="vx-w2-kpi-unit" data-testid="kpi-tile-unit">
              {unit}
            </span>
          )}
        </p>
      )}

      {/* Une variation ou une série SANS la mesure qu'elles qualifient n'ont
          rien à qualifier : elles ne sont pas rendues. */}
      {value !== null && delta !== undefined ? (
        <KpiDelta value={delta.value} sign={delta.sign} period={delta.period} />
      ) : null}

      {value !== null && series !== undefined ? (
        <div className="vx-w2-kpi-spark">
          <SparkFigure
            closes={series.closes}
            {...(series.labels === undefined ? {} : { labels: series.labels })}
            sign={null}
            caption={series.caption}
            unit={series.unit}
            windowLabel={series.windowLabel}
            variant="area"
            tone={series.tone ?? 'silver'}
          />
        </div>
      ) : null}
    </div>
  );
}
