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
| `/follow-up` | Suivi | status, due | Effectuer une revue |
| `/performance` | Performance | from, to, basis | Comparer une période |
| `/vertex-ai` | Vertex AI | context | Poser une question sourcée |
| `/system` | Système | tab | Diagnostiquer une source |

`instrumentId`, `snapshot` et `draft` sont des identifiants Vertex opaques. Symbole, exchange et expiry ne suffisent jamais à identifier un contrat. Les filtres longs sont enregistrés côté serveur sous un identifiant, pas sérialisés intégralement dans l'URL.

