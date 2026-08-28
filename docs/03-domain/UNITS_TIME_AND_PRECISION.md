# Unités, temps et précision

- UTC en stockage ; timezone de l'exchange et timezone d'affichage conservées séparément.
- Calendriers de marché versionnés ; DST, demi-séances et jours fériés testés.
- `exchange_calendars` fournit une bibliothèque épinglée, mais une date critique est vérifiée contre l'exchange primaire ; la bibliothèque n'est pas une source réglementaire infaillible.
- `Decimal` pour monnaie, prix contractuels, quantités et frais aux frontières.
- `float64` pour modèles numériques avec tolérances documentées.
- Pourcentage API : ratio décimal canonique, par exemple `0.253`, formaté `25,3 %` par l'UI.
- IV interne : décimal annuel, par exemple `0.24`; points d'IV explicitement nommés.
- Taux : convention, base de jour, composition, courbe et date obligatoires.
- Greeks : unité documentée par contrat et par point de variable.
- Rendements : brut/net, simple/log, période et annualisation obligatoires.
- Aucune conversion implicite de devise, multiplicateur ou unité.
- `NaN`, infini, `-0`, timestamp naïf et valeur sentinelle sont interdits dans les DTO.
