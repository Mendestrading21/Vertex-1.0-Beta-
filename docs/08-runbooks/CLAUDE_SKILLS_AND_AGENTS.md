# Claude Code — skill, agents et pilotage

## Configuration livrée

- un skill maître : `.claude/skills/vertex-one/SKILL.md` ;
- six sous-agents d'audit en lecture seule ;
- prompts spécialisés pour migration, modèle, widget et profil ;
- lots numérotés comme seule unité de changement.

Le skill décide quelles références lire. Les agents inspectent en parallèle mais
n'écrivent pas. L'agent principal garde l'arbitrage, applique un seul lot et
produit la preuve finale. Cela évite plusieurs autorités et les changements
concurrents sur les mêmes fichiers.

## Depuis le téléphone

1. démarrer Claude Code sur l'ordinateur contenant le dépôt et TWS/IB Gateway ;
2. lancer Remote Control ;
3. ouvrir la session depuis l'application mobile ;
4. après bootstrap audité, lancer `PLAN PARCOURS COMPLET` ;
5. lire le parcours `DOSSIER 00` à `DOSSIER 25`, puis répondre
   `VALIDE LE PARCOURS — EXÉCUTE DOSSIER 00` ;
6. n'envoyer ensuite `EXÉCUTE DOSSIER NN` qu'après lecture du plan borné ;
7. utiliser `STATUT` pour un rapport adapté au téléphone.

Le code et les connexions restent sur l'ordinateur. Le téléphone ne devient pas
un serveur IBKR et ne reçoit aucun secret.

## Règles d'autonomie

Claude peut trancher seul les décisions réversibles déjà fixées par ADR et
catalogues. Il s'arrête uniquement pour un coût, une licence non standard, une
exposition externe, une donnée personnelle, une frontière financière, une
action destructive ou une ambiguïté qui change le produit.

## Skills et plugins candidats

Le manifeste `manifests/claude-tooling.yaml` sépare les outils déjà livrés des
candidats officiels à vérifier. Aucun catalogue « awesome », skill de forum ou
starter de dashboard n'est installé en bloc.

- `frontend-design`, issu du dépôt officiel Claude Code, peut assister les lots
  UI après pin et revue. Les tokens Black Glass, le catalogue de widgets et les
  contrats de données restent autoritaires ; le skill ne choisit ni calcul ni
  verdict.
- `code-review` peut lancer plusieurs regards indépendants sur une PR brouillon.
  Ses conclusions restent consultatives et ne remplacent ni tests, ni revue
  humaine, ni gates.
- `security-guidance` peut rappeler les risques avant un outil mutant. Les scans
  déterministes, la vérification du remote et les frontières IBKR restent les
  contrôles bloquants.
- l'Action officielle `claude-code-security-review` reste optionnelle : coût,
  permissions et sortie de code exigent une décision humaine.
- le skill officiel shadcn/ui est une référence d'API, pas une autorisation de
  copier un registry ou un template. Vertex garde ses wrappers Radix et son
  esthétique propre.

Un skill tiers trouvé sur GitHub, un réseau social ou un forum devient au mieux
un candidat. Il exige source, licence, pin, inventaire des permissions et flux,
test isolé et rollback. Il n'accède jamais aux secrets, au payload marché réel,
au donneur en écriture ou à une autorité financière.

## Sources officielles

- https://docs.anthropic.com/en/docs/claude-code/skills
- https://docs.anthropic.com/en/docs/claude-code/sub-agents
- https://docs.anthropic.com/en/docs/claude-code/hooks
- https://docs.anthropic.com/en/docs/claude-code/common-workflows
- https://docs.anthropic.com/en/docs/claude-code/remote-control
- https://github.com/anthropics/claude-code/tree/main/plugins/frontend-design
- https://github.com/anthropics/claude-code/tree/main/plugins/code-review
- https://github.com/anthropics/claude-code/tree/main/plugins/security-guidance
- https://github.com/anthropics/claude-code-security-review
- https://ui.shadcn.com/docs/skills
