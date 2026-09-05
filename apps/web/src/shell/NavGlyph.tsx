import { Glyph } from '../components/widgets/Glyph.tsx';
import type { GlyphName } from '../components/widgets/Glyph.tsx';

/**
 * Glyphes du rail, tirés du catalogue SVG approuvé (`Glyph`, LOT T2).
 *
 * Ce fichier ne décide plus QUE d'une chose : quelle icône du catalogue
 * appartient à quelle destination. Le masque, la couleur héritée et le
 * `aria-hidden` vivent dans la primitive, partagés avec les tuiles de mesure —
 * une seule source, donc un seul vocabulaire visuel.
 */
const GLYPH_BY_PAGE: Readonly<Record<string, GlyphName>> = {
  today: 'attention-queue',
  opportunities: 'gate-pass',
  analysis: 'evidence-rail',
  options: 'option-chain',
  simulator: 'payoff-curve',
  calendar: 'news-cluster',
  markets: 'market-regime',
  portfolio: 'manual-ledger',
  catalysts: 'thesis-active',
  'sources-reports': 'source-coverage',
};

export interface NavGlyphProps {
  readonly pageKey: string;
}

/** Icône purement décorative : le lien parent conserve le nom accessible. */
export function NavGlyph({ pageKey }: NavGlyphProps) {
  const name = GLYPH_BY_PAGE[pageKey];
  if (name === undefined) {
    return null;
  }

  return <Glyph name={name} className="vx-nav-glyph" />;
}
