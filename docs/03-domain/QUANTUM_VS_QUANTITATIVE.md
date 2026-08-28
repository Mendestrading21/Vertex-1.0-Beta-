# Quantitatif, pas « quantique » marketing

## Décision

Vertex One est un système **quantitatif** d'aide à la décision. Il n'est pas un
ordinateur quantique et ne promet aucune précision de 100 %. Aucun SDK ou
algorithme dit quantique n'entre dans le runtime tant qu'un protocole reproductible
ne démontre pas un gain hors échantillon après coûts, face à une baseline simple.

## Ce que « très intelligent » signifie ici

- données identifiées, datées, licenciées et contrôlées ;
- calculs déterministes testés par propriétés et oracles ;
- modèles calibrés, comparés à des baselines et suivis en dérive ;
- fusion de preuves avec contradictions visibles ;
- intervalles d'incertitude et droit de s'abstenir ;
- journal immuable permettant de rejouer ce que le système savait réellement ;
- humain seul décideur.

## Interdictions

- score de confiance inventé ;
- précision garantie ou vocabulaire de certitude ;
- modèle choisi parce qu'il est complexe ;
- backtest sans données point-in-time, coûts ou biais documentés ;
- LLM utilisé comme calculateur financier ou oracle de direction ;
- « quantum-inspired » comme justification sans test d'ablation.

## Bac de recherche éventuel

Une expérience quantique ou quantum-inspired reste hors production, isolée dans
`research/`, sans accès au moteur de décision. Elle doit fournir dataset figé,
baseline classique, protocole, budget de calcul, résultats négatifs inclus et
critère d'abandon. L'absence de gain ferme l'expérience.

