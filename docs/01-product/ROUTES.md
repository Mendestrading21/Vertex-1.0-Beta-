# Routes produit

| Route | Page | Paramètres permis | Action principale |
|---|---|---|---|
| `/today` | Aujourd'hui | date, scope | Ouvrir l'élément prioritaire |
| `/calendar` | Calendrier | from, to, kinds, instruments | Filtrer l'agenda |
| `/markets` | Marchés | universe, horizon | Ouvrir un segment |
| `/opportunities` | Opportunités | saved_view, sort | Examiner un candidat |
| `/analysis/:instrumentId` | Analyse | snapshot, timeframe | Enregistrer une thèse |
| `/options/:instrumentId` | Options | expiry, snapshot | Inspecter un contrat |
| `/simulator` | Simulateur | draft | Lancer une simulation théorique |
| `/portfolio` | Portefeuille | view, as_of | Ajouter une opération manuelle |
| `/catalysts` | Catalyseurs | status, due | Effectuer une revue |
| `/sources-reports` | Sources & Rapports | tab | Diagnostiquer une source |

Trois routes de ce tableau ont été ABSORBÉES par
`docs/05-design/PAGE_ARBITRATION.md` et ne sont plus des destinations. Elles
restent atteignables par une redirection permanente, jamais par un 404 :

| Ancienne route | Destination | Ce qui la porte désormais |
|---|---|---|
| `/system` | `/sources-reports` | renommage de la destination (LOT-07) |
| `/performance` | `/portfolio` | module Performance de Portefeuille (LOT-08) |
| `/follow-up` | `/catalysts` | module de revue de Catalyseurs (LOT-10) |
| `/ai` | `/analysis` | panneau d'explication de l'inspecteur (LOT-12) |

L'explication IA n'a plus de destination du tout : le contrat serveur ne
connaît que trois sujets explicables — `analysis/<instrument>`,
`portfolio_valuation/<portefeuille>` et `performance/<portefeuille>` — qui sont
exactement les dossiers d'Analyse et de Portefeuille. Elle vit donc dans
l'inspecteur de ces deux pages.

Les routes **API** correspondantes n'ont pas bougé : `/v1/system/capabilities`,
`/v1/performance/{id}`, `/v1/follow-up/queue`, `/v1/ai/status` et
`/v1/ai/explain` restent servies telles quelles.
Seule la composition d'interface a changé.

`instrumentId`, `snapshot` et `draft` sont des identifiants Vertex opaques. Symbole, exchange et expiry ne suffisent jamais à identifier un contrat. Les filtres longs sont enregistrés côté serveur sous un identifiant, pas sérialisés intégralement dans l'URL.

