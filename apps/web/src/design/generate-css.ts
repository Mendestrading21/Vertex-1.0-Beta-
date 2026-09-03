/**
 * Générateur de `src/design/tokens.css` depuis la source typée unique
 * `src/design/tokens.ts`.
 *
 * Usage : `pnpm tokens:css` (script Node commité, type-stripping natif Node 22+).
 * Le fichier généré est commité et vérifié par `src/design/tokens-css.test.ts`.
 */
import { writeFileSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';

import {
  color,
  fontFamily,
  fontSize,
  motionDuration,
  motionEase,
  pageAccent,
  radius,
  shadow,
  space,
  zIndex,
} from './tokens.ts';

export const GENERATED_HEADER =
  '/* GÉNÉRÉ — ne pas éditer. Source : src/design/tokens.ts — régénérer via `pnpm tokens:css`. */';

function block(indent: string, prefix: string, entries: Record<string | number, string>): string {
  return Object.entries(entries)
    .map(([key, value]) => `${indent}--${prefix}${key}: ${value};`)
    .join('\n');
}

/**
 * Blocs `[data-page-accent="<famille>"]` (ADR-017) : la teinte secondaire d'une
 * page est une famille EXISTANTE, résolue par variables — aucune couleur ici,
 * et aucune valeur par défaut dans `:root`.
 */
function pageAccentBlocks(): string {
  return Object.entries(pageAccent)
    .map(([page, family]) =>
      [
        `[data-page-accent="${page}"] {`,
        `  --vx-page-accent: var(--vx-${family});`,
        `  --vx-page-accent-soft: var(--vx-${family}-soft);`,
        `  --vx-page-accent-gradient-start: var(--vx-${family}-gradient-start);`,
        `  --vx-page-accent-gradient-end: var(--vx-${family}-gradient-end);`,
        '}',
      ].join('\n'),
    )
    .join('\n\n');
}

export function renderTokensCss(): string {
  const reducedMotion = Object.keys(motionDuration)
    .map((key) => `    --vx-motion-${key}: 0ms;`)
    .join('\n');

  return `${GENERATED_HEADER}

:root {
  /* Couleurs — Black Glass, Titanium Ledger */
${block('  ', 'vx-', color)}

  /* Espacements — grille 4 px */
${block('  ', 'vx-space-', space)}

  /* Rayons */
${block('  ', 'vx-radius-', radius)}

  /* Ombres */
${block('  ', 'vx-shadow-', shadow)}

  /* Mouvements */
${block('  ', 'vx-motion-', motionDuration)}
${block('  ', 'vx-ease-', motionEase)}

  /* Plans z nommés */
${block('  ', 'vx-z-', zIndex)}

  /* Typographie */
${block('  ', 'vx-font-', fontFamily)}
${block('  ', 'vx-font-size-', fontSize)}
}

/* Teinte sémantique secondaire par page (ADR-017) : une famille existante,
   déclarée par le catalogue de la page ; aucune valeur par défaut. */
${pageAccentBlocks()}

/* Reduced motion : toutes les durées tombent à 0 ms. */
@media (prefers-reduced-motion: reduce) {
  :root {
${reducedMotion}
  }
}
`;
}

const entryPoint = process.argv[1];
if (entryPoint !== undefined && import.meta.url === pathToFileURL(entryPoint).href) {
  const outFile = fileURLToPath(new URL('./tokens.css', import.meta.url));
  writeFileSync(outFile, renderTokensCss(), 'utf8');
  process.stdout.write(`tokens.css written: ${outFile}\n`);
}
