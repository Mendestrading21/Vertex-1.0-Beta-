/**
 * Génération du client de types API — `pnpm gen:api`.
 *
 * Lit apps/api/openapi.json (document exporté, committé, propriété de l'API)
 * et produit src/api/schema.d.ts via openapi-typescript (devDependency
 * épinglée). Le fichier généré est commité avec un en-tête GÉNÉRÉ ; il ne se
 * modifie jamais à la main (règle : « générer le client TypeScript depuis
 * OpenAPI, aucun second modèle manuel concurrent »).
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

import openapiTS, { astToString } from 'openapi-typescript';

const SOURCE_URL = new URL('../../api/openapi.json', import.meta.url);
const TARGET_PATH = fileURLToPath(new URL('../src/api/schema.d.ts', import.meta.url));

const HEADER = `/**
 * GÉNÉRÉ — NE PAS MODIFIER À LA MAIN.
 * Source : apps/api/openapi.json (contrat OpenAPI de l'API Vertex One).
 * Régénération : pnpm gen:api (openapi-typescript, devDependency épinglée).
 */
`;

const document = JSON.parse(readFileSync(SOURCE_URL, 'utf8')) as Parameters<typeof openapiTS>[0];
const ast = await openapiTS(document);
writeFileSync(TARGET_PATH, HEADER + astToString(ast));
process.stdout.write(`schema.d.ts généré depuis ${fileURLToPath(SOURCE_URL)}\n`);
