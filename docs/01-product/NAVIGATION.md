# Navigation

## Modèle mental

La navigation suit quatre verbes et non la structure technique :

| Groupe | Pages | Question |
|---|---|---|
| Décider | Aujourd'hui, Opportunités, Analyse, Options, Simulateur | Que mérite une décision ou une simulation ? |
| Observer | Calendrier, Marchés | Quel est le contexte et qu'est-ce qui arrive ? |
| Piloter | Portefeuille, Suivi, Performance | Que suis-je, pourquoi et avec quel résultat ? |
| Assistance | Vertex AI, Système | Que signifie l'information et peut-on lui faire confiance ? |

## Desktop

Vertex 1.0 Beta est **desktop only**. Rail gauche 232 px rétractable à 68 px. Le groupe courant est explicite, le libellé reste disponible au focus et l'état actif n'est pas porté par la couleur seule. La barre de contexte conserve instrument, snapshot, heure, type de donnée et qualité entre les pages compatibles.

La navigation est conçue et testée à 1280, 1440 et 1600 px. À 1024 px, le rail démarre replié à 68 px, sans changer l'ordre, les routes, la hiérarchie des groupes ni les commandes clavier ; les modules de page gèrent leur propre dégradation laptop.

## Mobile — LATER

Aucune navigation ni UI Vertex pour téléphone n'est incluse dans Vertex 1.0 Beta. Les routes, libellés, ordre logique, états actifs, focus et contrats de contexte restent des invariants sémantiques pour une phase mobile ultérieure. Sur téléphone, seul Claude Remote Control pilote la session desktop ; son interface n'est pas une surface Vertex.

## Liens profonds

L'URL transporte uniquement des identifiants non sensibles et filtres partageables. Aucun secret webhook, identifiant de compte, contenu de portefeuille ou prompt brut. Un lien vers une donnée supprimée mène vers un état explicite, jamais vers une autre donnée par défaut.

## Retour et contexte

- retour restaure scroll, filtres et sélection ;
- ouvrir un instrument conserve le snapshot initial jusqu'à rafraîchissement explicite ou signal SSE ;
- le changement de contexte avertit si une simulation ou une note non sauvegardée existe ;
- les URL sont canoniques et testées en navigation clavier, refresh et accès direct.
