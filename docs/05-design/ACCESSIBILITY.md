# Accessibilité

Cible WCAG 2.2 AA.

- navigation complète au clavier et ordre logique ;
- focus visible, non masqué et restauré après fermeture d'un panneau ;
- zones de clic d'au moins 32×32 px et espacées sans ambiguïté ;
- zoom 200 % sans perte d'information ;
- contraste automatique et revue manuelle des tokens ;
- `prefers-reduced-motion` ;
- titres hiérarchiques et landmarks ;
- messages live limités aux changements utiles ;
- chaque graphique a un résumé et une table équivalente ;
- vert/rouge complétés par signe, texte et forme ;
- tables virtualisées testées avec lecteur d'écran et focus ;
- valeurs financières prononcées avec unité et devise ;
- aucune information essentielle dans un tooltip uniquement.

Validation : axe-core sans violation critique/sérieuse, parcours clavier,
NVDA/VoiceOver desktop sur parcours clés et Storybook aux états complets aux
largeurs 1280, 1440 et 1600 px. Le smoke test 1024 px conserve le contenu et le
focus ; aucune QA mobile n'est requise dans la Beta.
