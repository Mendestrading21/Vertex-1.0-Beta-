# ADR-015 — Edge dédié aux sources officielles

- Statut : Accepté
- Date : 2026-09-01
- Portée : SEC EDGAR, FRED/ALFRED, BCE, BNS et OpenFIGI

## Contexte

ADR-013 autorise les sources primaires mais aucun bord réseau dédié ne les
isolait. Les intégrer dans le worker mélangerait transport externe, politique
de droits, normalisation et production de snapshots. Les fournisseurs payants
ne peuvent par ailleurs être activés sans choix humain de coût et de licence.

## Décision

- Créer `apps/edge-official`, adaptateur lecture seule sans calcul financier.
- N'autoriser que cinq hôtes HTTPS exacts, refuser les redirections et borner
  chaque réponse à 5 Mio.
- Transporter chaque réponse dans `DataEnvelope` avec source, schéma, droits,
  heure de réception, TTL brut et hash canonique.
- Conserver `observed_at` et `published_at` à `None` tant qu'un normaliseur
  propre au schéma n'a pas extrait une heure prouvée du payload.
- Ne jamais résoudre automatiquement une ambiguïté OpenFIGI.
- Garder FMP et ORATS désactivés jusqu'à validation humaine du plan, du coût,
  des endpoints inclus, des droits de stockage et d'affichage.
- Continuer à traiter Wall Street Horizon par l'adaptateur IBKR existant ;
  l'entitlement séparé reste sondé et fail-closed.

## Conséquences

Les connecteurs officiels peuvent être testés sans secrets ni réseau avec un
transport simulé. Ce lot ne les branche pas encore aux normaliseurs, à la base,
aux snapshots ou aux pages : ces passages exigent un lot borné par famille de
données et des contrats consommateurs explicites.

## Options rejetées

| Option | Motif |
|---|---|
| Requêtes HTTP dans le worker | Mélange des responsabilités et tests de panne plus difficiles |
| Agrégateur payant comme vérité unique | Droits, coût et provenance insuffisamment décidés |
| Fallback automatique | Masque une panne ou un changement de nature |
| Clé API dans le manifeste ou Git | Secret durable et révocation difficile |
