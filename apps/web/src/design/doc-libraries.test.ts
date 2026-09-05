// @vitest-environment node
/**
 * PORTE DES BIBLIOTHÈQUES CONTRACTÉES PAR LA DOCUMENTATION.
 *
 * `docs/05-design/WIDGET_LIBRARY.md` écrivait, au présent de l'indicatif :
 * « `AdviceCard`, `OptionInspector`, `LegComposer`, `ThesisDetail`, `AiAnswer`
 * et les diagnostics système s'appuient sur les primitives **Radix**. Dialog,
 * AlertDialog, Accordion, Tooltip, Popover, Tabs et Select sont enveloppés une
 * seule fois dans le package UI Vertex. »
 *
 * MESURE : `apps/web/package.json` porte SEPT dépendances de production —
 * `@tanstack/react-query`, `echarts`, `geist`, `lightweight-charts`, `react`,
 * `react-dom`, `react-router-dom`. Ni Radix, ni Lucide n'y figurent, et aucun
 * « package UI Vertex » n'existe. Le document ne décrivait pas une intention :
 * il énonçait un fait faux.
 *
 * POURQUOI CELA COMPTE. Un document de design est lu AVANT d'écrire. Celui qui
 * le croit écrit `import * as Dialog from '@radix-ui/react-dialog'`, découvre
 * que rien ne résout, et conclut qu'il faut installer la dépendance — alors
 * que `architecture.md` interdit d'ajouter un framework sans ADR et que la
 * consigne permanente n'autorise une dépendance que pour un manque précis et
 * démontré. Un document qui contracte une bibliothèque absente fabrique donc
 * exactement la décision que les règles refusent.
 *
 * CE QUE CETTE PORTE NE FAIT PAS. Elle ne lit pas la prose et ne juge pas les
 * choix de design. Elle vérifie une chose : aucun document de `docs/05-design/`
 * n'affirme s'appuyer sur une bibliothèque tierce absente du manifeste. Une
 * mention historique reste possible — elle doit alors dire qu'elle est
 * historique, jamais « s'appuient sur ».
 */
import { readdirSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const racineDocs = fileURLToPath(new URL('../../../../docs/05-design/', import.meta.url));
const manifeste = JSON.parse(
  readFileSync(fileURLToPath(new URL('../../package.json', import.meta.url)), 'utf8'),
) as { dependencies?: Record<string, string>; devDependencies?: Record<string, string> };

const installees = new Set([
  ...Object.keys(manifeste.dependencies ?? {}),
  ...Object.keys(manifeste.devDependencies ?? {}),
]);

/**
 * Les bibliothèques d'interface qu'un document pourrait contracter, avec le
 * nom de paquet qui prouverait leur présence. Liste NOMMÉE, pas devinée : une
 * détection automatique par mot capitalisé attraperait « Vertex », « Black
 * Glass » ou « Chromium » et rendrait la porte inutilisable.
 */
const BIBLIOTHEQUES: readonly (readonly [string, string])[] = [
  ['Radix', '@radix-ui/react-dialog'],
  ['Lucide', 'lucide-react'],
  ['Tailwind', 'tailwindcss'],
  ['Material UI', '@mui/material'],
  ['Ant Design', 'antd'],
  ['Chakra', '@chakra-ui/react'],
  ['Headless UI', '@headlessui/react'],
];

/** Le document AFFIRME-t-il s'appuyer sur cette bibliothèque ? */
const AFFIRMATIONS = ['s’appuie', "s'appuie", 's’appuient', "s'appuient", 'utilise', 'utilisent'];

describe('les documents de design ne contractent aucune bibliothèque absente', () => {
  const documents = readdirSync(racineDocs).filter((f) => f.endsWith('.md'));

  it('énumère au moins un document — sinon cette porte ne mesure rien', () => {
    expect(documents.length).toBeGreaterThan(0);
  });

  for (const nom of documents) {
    it(`${nom}`, () => {
      const texte = readFileSync(`${racineDocs}${nom}`, 'utf8');
      const fautes: string[] = [];
      for (const [libelle, paquet] of BIBLIOTHEQUES) {
        if (installees.has(paquet)) {
          continue;
        }
        for (const ligne of texte.split('\n')) {
          if (!ligne.includes(libelle)) {
            continue;
          }
          if (!AFFIRMATIONS.some((verbe) => ligne.includes(verbe))) {
            continue;
          }
          fautes.push(`${libelle} (paquet ${paquet} absent) — « ${ligne.trim().slice(0, 120)} »`);
        }
      }
      expect(
        fautes,
        `${nom} affirme s'appuyer sur une bibliothèque qui n'est pas installée :\n  ${fautes.join('\n  ')}`,
      ).toEqual([]);
    });
  }
});
