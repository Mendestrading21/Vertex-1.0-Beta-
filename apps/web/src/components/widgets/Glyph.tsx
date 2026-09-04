import attentionQueueUrl from '../../../../../design-assets/icons/custom/attention-queue.svg?url';
import auditTraceUrl from '../../../../../design-assets/icons/custom/audit-trace.svg?url';
import brandMarkUrl from '../../../../../design-assets/icons/custom/brand-mark.svg?url';
import evidenceRailUrl from '../../../../../design-assets/icons/custom/evidence-rail.svg?url';
import gateBlockUrl from '../../../../../design-assets/icons/custom/gate-block.svg?url';
import gateDegradeUrl from '../../../../../design-assets/icons/custom/gate-degrade.svg?url';
import gatePassUrl from '../../../../../design-assets/icons/custom/gate-pass.svg?url';
import greeksBasketUrl from '../../../../../design-assets/icons/custom/greeks-basket.svg?url';
import manualLedgerUrl from '../../../../../design-assets/icons/custom/manual-ledger.svg?url';
import marketRegimeUrl from '../../../../../design-assets/icons/custom/market-regime.svg?url';
import newsClusterUrl from '../../../../../design-assets/icons/custom/news-cluster.svg?url';
import optionChainUrl from '../../../../../design-assets/icons/custom/option-chain.svg?url';
import payoffCurveUrl from '../../../../../design-assets/icons/custom/payoff-curve.svg?url';
import scenarioBearUrl from '../../../../../design-assets/icons/custom/scenario-bear.svg?url';
import scenarioBullUrl from '../../../../../design-assets/icons/custom/scenario-bull.svg?url';
import scenarioNeutralUrl from '../../../../../design-assets/icons/custom/scenario-neutral.svg?url';
import snapshotSealedUrl from '../../../../../design-assets/icons/custom/snapshot-sealed.svg?url';
import sourceCoverageUrl from '../../../../../design-assets/icons/custom/source-coverage.svg?url';
import termStructureUrl from '../../../../../design-assets/icons/custom/term-structure.svg?url';
import thesisActiveUrl from '../../../../../design-assets/icons/custom/thesis-active.svg?url';
import volatilitySmileUrl from '../../../../../design-assets/icons/custom/volatility-smile.svg?url';

/**
 * Le catalogue SVG Vertex approuvé, et RIEN d'autre.
 *
 * POURQUOI CE FICHIER EXISTE (LOT T2). `NavGlyph` masquait dix de ces
 * vingt et une icônes pour le seul rail de navigation. Les tuiles de mesure
 * des tableaux de bord de référence portent une pastille d'icône ; sans
 * source unique, elle serait devenue un emoji, un caractère typographique ou
 * un SVG improvisé — trois façons d'ouvrir un second vocabulaire visuel.
 *
 * DEUX RÈGLES TENUES ICI.
 *   1. Le masque hérite de `currentColor` : AUCUNE couleur n'est encodée dans
 *      l'icône. La teinte vient du parent, donc d'une décision déclarée.
 *   2. L'icône est `aria-hidden` et ne porte JAMAIS seule une information —
 *      la règle « la couleur n'est jamais le seul vecteur » vaut aussi pour la
 *      forme. Le libellé textuel voisin dit tout.
 */
export const GLYPH_NAMES = [
  'attention-queue',
  'audit-trace',
  'brand-mark',
  'evidence-rail',
  'gate-block',
  'gate-degrade',
  'gate-pass',
  'greeks-basket',
  'manual-ledger',
  'market-regime',
  'news-cluster',
  'option-chain',
  'payoff-curve',
  'scenario-bear',
  'scenario-bull',
  'scenario-neutral',
  'snapshot-sealed',
  'source-coverage',
  'term-structure',
  'thesis-active',
  'volatility-smile',
] as const;

export type GlyphName = (typeof GLYPH_NAMES)[number];

/**
 * `satisfies Record<GlyphName, string>` : ajouter un nom au vocabulaire sans
 * son URL casse la COMPILATION, jamais l'écran.
 */
const GLYPH_URLS = {
  'attention-queue': attentionQueueUrl,
  'audit-trace': auditTraceUrl,
  'brand-mark': brandMarkUrl,
  'evidence-rail': evidenceRailUrl,
  'gate-block': gateBlockUrl,
  'gate-degrade': gateDegradeUrl,
  'gate-pass': gatePassUrl,
  'greeks-basket': greeksBasketUrl,
  'manual-ledger': manualLedgerUrl,
  'market-regime': marketRegimeUrl,
  'news-cluster': newsClusterUrl,
  'option-chain': optionChainUrl,
  'payoff-curve': payoffCurveUrl,
  'scenario-bear': scenarioBearUrl,
  'scenario-bull': scenarioBullUrl,
  'scenario-neutral': scenarioNeutralUrl,
  'snapshot-sealed': snapshotSealedUrl,
  'source-coverage': sourceCoverageUrl,
  'term-structure': termStructureUrl,
  'thesis-active': thesisActiveUrl,
  'volatility-smile': volatilitySmileUrl,
} as const satisfies Record<GlyphName, string>;

export interface GlyphProps {
  readonly name: GlyphName;
  /** Côté du carré, en jeton d'espace. Défaut : 20 px, la taille du rail. */
  readonly size?: string;
  readonly className?: string;
}

/** Icône purement décorative : le texte voisin conserve le sens. */
export function Glyph({ name, size = 'var(--vx-space-20)', className }: GlyphProps) {
  const mask = `url("${GLYPH_URLS[name]}") center / contain no-repeat`;

  return (
    <span
      aria-hidden="true"
      data-testid="glyph"
      data-glyph={name}
      {...(className === undefined ? {} : { className })}
      style={{
        display: 'inline-block',
        width: size,
        height: size,
        flex: '0 0 auto',
        backgroundColor: 'currentColor',
        mask,
        WebkitMask: mask,
      }}
    />
  );
}
