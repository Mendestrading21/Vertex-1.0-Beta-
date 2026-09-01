import attentionQueueUrl from '../../../../design-assets/icons/custom/attention-queue.svg?url';
import evidenceRailUrl from '../../../../design-assets/icons/custom/evidence-rail.svg?url';
import gatePassUrl from '../../../../design-assets/icons/custom/gate-pass.svg?url';
import manualLedgerUrl from '../../../../design-assets/icons/custom/manual-ledger.svg?url';
import marketRegimeUrl from '../../../../design-assets/icons/custom/market-regime.svg?url';
import newsClusterUrl from '../../../../design-assets/icons/custom/news-cluster.svg?url';
import optionChainUrl from '../../../../design-assets/icons/custom/option-chain.svg?url';
import payoffCurveUrl from '../../../../design-assets/icons/custom/payoff-curve.svg?url';
import sourceCoverageUrl from '../../../../design-assets/icons/custom/source-coverage.svg?url';
import thesisActiveUrl from '../../../../design-assets/icons/custom/thesis-active.svg?url';

/**
 * Glyphes du rail issus exclusivement du catalogue SVG Vertex approuvé.
 * Le masque hérite de `currentColor` : l'état actif reste piloté par le lien,
 * sans couleur financière encodée dans l'icône.
 */
const GLYPH_BY_PAGE: Readonly<Record<string, string>> = {
  today: attentionQueueUrl,
  opportunities: gatePassUrl,
  analysis: evidenceRailUrl,
  options: optionChainUrl,
  simulator: payoffCurveUrl,
  calendar: newsClusterUrl,
  markets: marketRegimeUrl,
  portfolio: manualLedgerUrl,
  catalysts: thesisActiveUrl,
  'sources-reports': sourceCoverageUrl,
};

export interface NavGlyphProps {
  readonly pageKey: string;
}

/** Icône purement décorative : le lien parent conserve le nom accessible. */
export function NavGlyph({ pageKey }: NavGlyphProps) {
  const glyphUrl = GLYPH_BY_PAGE[pageKey];
  if (glyphUrl === undefined) {
    return null;
  }

  const mask = `url("${glyphUrl}") center / contain no-repeat`;

  return (
    <span
      aria-hidden="true"
      className="vx-nav-glyph"
      style={{
        display: 'inline-block',
        width: 'var(--vx-space-20)',
        height: 'var(--vx-space-20)',
        flex: '0 0 auto',
        backgroundColor: 'currentColor',
        mask,
        WebkitMask: mask,
      }}
    />
  );
}
