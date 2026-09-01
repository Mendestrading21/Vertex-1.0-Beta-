# Dette technique et limites connues

Ce registre liste les défauts **connus et non corrigés**, ainsi que les limites
de preuve. Il est tenu à jour à chaque audit adversarial. Une entrée n'est
retirée que lorsqu'un test reproducteur rouge d'abord la ferme.

Ce fichier ne contient pas de décision humaine ; celles-ci restent dans
`BLOCKERS.md`.

## Défauts ouverts (3ᵉ audit adversarial, commit `2bc75cc`)

| ID | Sévérité | Fichier | Défaut | État |
|---|---|---|---|---|
| P1-C | P1 | `apps/api/src/vertex_api/ai_explain.py` | Le détecteur de langage d'ordre est une **liste noire best-effort** : contourné par une autre langue (espagnol), une formulation en toutes lettres (« Trois chances sur quatre ») ou un homoglyphe (U+0251). | ouvert — aucune garantie d'exhaustivité ne doit être annoncée |
| P1-D | P1 | `apps/api/src/vertex_api/ai_explain.py` | Le même détecteur **refuse des libellés financiers légitimes** (« Marge brute de 42 % », « Dividende de 2,5 % ») : faux positifs qui peuvent masquer une donnée réelle. | ouvert |
| P2-préc. | P2 | `docs/` | Les rapports de commit des vagues 3 à 5 ont **sur-promis** : ils annonçaient des fermetures que la reproduction contredisait. Correction de méthode appliquée (ne décrire que ce que le test prouve), mais l'historique Git conserve les messages fautifs. | méthode corrigée, historique inchangé |

## Limites de preuve (aucune n'est un défaut de code)

| Sujet | Limite exacte |
|---|---|
| Version Python | La suite tourne localement sur **3.11** (plancher). Le workflow CI exécute la cible **3.13** et il est **vert** — c'est là, et seulement là, que la version de production est prouvée. |
| CI | Le workflow `.github/workflows/ci.yml` existe et couvre 15 portes (actions épinglées à un SHA de commit complet, images par digest immuable). Il a **été exécuté et est vert** sur les 6 jobs et les 15 portes (dernier run vérifié : `1c782fe`), sur les versions CIBLES — Python 3.13, Node 24, PostgreSQL 18.6. C'est la seule preuve existante sur ces versions ; l'environnement de développement tourne sur 3.11 / Node 22 / PostgreSQL 16. |
| Intégration | `tools/run_checks.sh --integration` couvre désormais les trois suites (`vertex_persistence`, `worker`, `api`), **en série obligatoire** : elles partagent la même base et recréent le schéma. Avant ce correctif, seule la suite `vertex_persistence` tournait — les mentions « TOUT VERT » antérieures ne couvraient donc **pas** les suites worker et api. |
| Lint et typage Python | **Porte `python-quality` livrée et verte.** `ruff check .` : **1653 → 0** ; `mypy --strict` : **0 erreur sur 114 fichiers source**. Les deux sont câblés dans `.github/workflows/ci.yml` (job `python-quality`) et dans `tools/run_checks.sh`, et échouent sur la moindre violation. Cause structurelle corrigée d'abord : `ruff==0.15.8` et `mypy==1.19.1` sont désormais épinglés en versions EXACTES dans `pyproject.toml` et verrouillés dans `uv.lock` — auparavant épinglés NULLE PART, d'où un compte non reproductible. **Le chiffre de départ réel est 1653, pas 1634** : la ligne précédente avait été mesurée avec une version de Ruff non épinglée et donc inconnue (septième chiffre erroné de ce registre) ; l'écart par règle était bien plus large que l'écart total (`UP017` 86 → 164, `E501` 102 → 146). Périmètre du typage : sources de production + portes `tools/` ; **aucune suite de tests n'est typée** (frontière uniforme, déclarée par `exclude` dans `[tool.mypy]`). Deux règles restent désactivées AVEC motif écrit dans `pyproject.toml` : `RUF001-003` (texte français, préexistant) et **`UP042`** — la conversion `class X(str, Enum)` → `StrEnum` change la sémantique (`f"{A.X}"` vaut `"A.X"` contre `"x"`, mesuré sur CPython 3.11.15) sur les 30 énumérations de CONTRAT qui traversent PostgreSQL, JSON et OpenAPI ; la lever est un lot à part entière (inventaire des interpolations + tests de sérialisation sur 3.13). Suppressions locales ajoutées par ce lot : **102 `# noqa`**, chacune avec un motif écrit — 36 `DTZ001`, 31 `S101`, 7 `S603`, 7 `B017`, 5 `S311`, 5 `B008`, 4 `S607`, 3 `S104`, 2 `S105`, 1 `S608`, 1 `S314` — plus **1 `# type: ignore[method-assign]`** (surcharge `app.openapi` documentée par FastAPI) et **4 `# type: ignore` RETIRÉS** devenus inutiles une fois `types-PyYAML` verrouillé. Les **36 `DTZ001`** sont des tests NÉGATIFS vérifiant le REJET d'un instant naïf : les « corriger » aurait supprimé l'invariant qu'ils protègent — le brief supposait l'inverse, la mesure dit le contraire. Les 3 `S104` sont de même nature (refus d'un hôte non-loopback) et les 31 `S101` sont des narrowings placés APRÈS une garde réelle. Les **7 `B017`** (`pytest.raises(Exception)` trop large) restent une **dette de test réelle non traitée** : les resserrer changerait le contrat des tests, ce que ce lot s'interdit. |
| Portes CI manquantes | Par rapport à `docs/06-quality/CI_GATES.md` (`python-quality` est désormais LIVRÉE) : `web-quality` (Biome), `migrations` (rollback + restauration), `performance` (Lighthouse, Locust), `build` (images non-root/digest). La porte `policy` existe désormais (`tools/check_policy.py`) et le volet **notices** de `release` aussi (`tools/check_notices.py`) ; **provenance** et **signature** restent NON FAISABLES ici — voir la section dédiée en fin de fichier, elles ne sont ni implémentées ni simulées. |
| Sauvegarde | `infra/backup/` : cycle `pg_dump` → chiffrement AES-256 → déchiffrement → contrôle d'empreinte → restauration dans une base vide → 4 contrôles → `verified_restore_at` **exécuté et vert sur PostgreSQL réel**. Manquent : archivage WAL/PITR (donc **RPO ≤ 5 min NON atteint**), troisième copie hors machine, ordonnancement, purge de rétention 7/4/12. |
| Compose et images | `infra/compose/` : 4 services, images épinglées par digest immuable, utilisateurs non privilégiés, systèmes de fichiers en lecture seule, ports publiés sur `127.0.0.1` uniquement. **Jamais exécuté** : cet environnement n'a pas de démon Docker. Validé syntaxiquement, pas prouvé. La preuve appartient au LOT-24. |
| Supervision | **Aucune.** Pas de métriques, série temporelle, tableau de bord, alerte ni trace. `opentelemetry-sdk` et `prometheus-client` sont prévus au manifeste mais ne sont ni installés ni câblés (absents de `uv.lock`). Voir `infra/monitoring/README.md`. |
| Budget de fraîcheur au relais — ASYMÉTRIE SYSTÉMIQUE — **FERMÉE au LOT-24c** | **CHIFFRE CORRIGÉ : 10 relais, pas 8.** `build_*_response` existe pour attention, markets, analysis, option_chain, capabilities, calendar, follow_up, opportunities, performance, portfolio. Seuls `calendar` et `opportunities` recalculent la fraîcheur contre l'horloge du relais ; `snapshot_views.py` (5 relais) n'en recalcule **aucune**. `attention/today` et `system/capabilities` n'ont jamais été examinés sous cet angle. L'asymétrie portait donc sur **8 relais sur 10**, pas 6 sur 8. **FERMÉE au LOT-24c** : `apps/api/src/vertex_api/freshness.py` est le propriétaire unique ; les dix relais publient `age_seconds` dans tous les états datables et basculent sur `stale` au-delà du budget de séance fermée de leur politique déclarée. La matrice de capacités publie son âge SANS budget, faute de politique au registre : sa péremption appartient au `expires_at` de la sonde, champ par champ. Preuve : `apps/api/tests/test_relay_freshness_is_published.py` (29 tests) et `apps/api/tests/test_freshness_relay.py` (10). |
| Rendu des états dégradés | `/opportunities` affiche désormais la cause publiée pour `clock_inconsistent`. Les pages `/performance`, `/follow-up` et `/portfolio` ne traitent pas `state="stale"` — ce qui est **correct aujourd'hui** puisque leurs relais ne le servent jamais, mais devra être ajouté en même temps que le budget de fraîcheur ci-dessus. |
| Recherche | `research/` fournit les OUTILS d'évaluation (walk-forward purgé, calibration, abstention) et une frontière testée contre les imports de runtime **écrits littéralement** — un `importlib.import_module`, un `__import__` ou un `subprocess.run(["psql", …])` n'était PAS détecté (5e audit), et les notebooks `.ipynb` n'étaient pas inspectés. **Rien n'a été évalué** : aucun modèle, aucun jeu de données, aucune probabilité calibrée. `datasets-manifest/` reste vide tant que B-04 n'est pas tranché. |
| Contrat de valeur des relais | **Cette ligne a été fausse DEUX FOIS ; voici la mesure faite après le dernier correctif, sur les fixtures réelles, avec une valeur forgée RESPECTANT la forme du champ.** Payload hostile (5038 caractères, BEL + ANSI) : **0 %** relayé verbatim sur les 7 relais mesurés — cela tient. Mais une valeur bien formée passe encore largement : `analysis` **30/57 feuilles chaîne = 53 %**, dont **24 non-prose** (`schema_version`, `engine_version`, `bars.currency` — `SYN` devient `USD` —, `adjustment_basis`, `source_event_id`, `rights`, `sources`, `cluster_id`, `gate_id`, `reason_code`, `advice_id`…) ; `markets_overview` **31/70 = 44 %**, dont **22 non-prose**. Mes formulations antérieures (« 5 % à 30 % », « exclusivement des champs de PROSE ») étaient fausses : la première était un artefact du payload choisi (il contenait un espace), la seconde ne décrivait pas le résidu. Le contrat contraint la FORME, pas le CONTENU : un champ techniquement bien formé mais faux passe. |
| Falsification complète de la nature — LIMITE HAUTE CONNUE | Le garde refuse désormais une contradiction interne : un contenu qui revendique `population: REAL`/`DELAYED` ne peut pas porter en même temps un marqueur synthétique (`rights`/`sources`/`source` = `SYNTHETIC`, `synthetic: true`). **Mais une falsification COMPLÈTE passe** : `population=REAL` avec tous les marqueurs effacés est acceptée et servie `REAL`. Un test la fige noir sur blanc. Le relais n'a pas observé la donnée ; le fermer exigerait une provenance signée par le worker, qui n'existe pas. C'est la limite haute de ce qui est vérifiable côté API. |
| Vocabulaires laissés OUVERTS, avec la raison | `rights` (habilitation) : aucun module de `vertex_core` ne possède ce vocabulaire — l'edge publie `IBKR_MARKET_DATA_DISPLAY_ONLY` via un argument de constructeur configurable, le générateur `SYNTHETIC`, une sonde `DEMO` ; le fermer inventerait une autorité. `rights` est **affiché** (`AttentionQueue`, `ThesisSheet`, `EventAgenda`). `ticker`, `exchange`, `sector`, `source` : univers ouverts, aucun registre. `status` générique : au moins huit espaces de noms non reliés ; leur union mettrait un statut de cotation là où un verdict est attendu et casserait la rétrogradation fail-closed voulue d'un statut de capacité inconnu. Fermé par chemin là où une autorité existe (`bars.status`, `markets.unit`), ouvert ailleurs. |
| Détecteur de langage d'ordre — couverture MESURÉE | **Ce chiffre a été faux TROIS FOIS (72, puis 21).** Compte réel, collecté depuis le code commité par le 6e audit : `test_adversarial_corpus_is_covered_by_the_detector` = **20** formulations, `test_detector_is_not_bypassed_by_unicode_tricks` = **11**, soit **31 détectées** ; plus `UNCOVERED_BY_THE_BLACKLIST` = **8** explicitement non couvertes. Dénominateur honnête du corpus commité : **31/39 = 79 %**. Les libellés légitimes non signalés sont **36** (6 dans `LEGITIMATE_TEXTS`, 30 dans `FACTUAL_PERCENTAGE_HEADLINES`), pas 6 ni 8. La mesure indépendante du 5e audit sur un corpus EXTERNE de 24 formulations (italien, néerlandais, polonais, turc, japonais, translittération russe, idiomes anglais) donne **29 %** : c'est l'écart entre « couvert par le corpus qu'on s'est écrit » et « couvert en général ». La seule garantie qui tient reste STRUCTURELLE, pas lexicale. |
| Worker Cloudflare — porte AJOUTÉE | Ses **53 tests de contrat** (le point d'entrée du webhook PUBLIC) n'étaient exécutés par AUCUNE porte, ni en CI ni dans `run_checks.sh`. Découvert en vérifiant une commande qui échouait pour une autre raison. Branchés dans les deux. `node --test <répertoire>` n'est pas accepté par Node 22 : il faut nommer les fichiers. |
| Horodatages fournisseur encore non bornés — 5 points SIGNALÉS, non corrigés | Trouvés en cherchant la même classe que les deux défauts d'ingress fermés. (1) `pacing.LineBudget(detected_lines)` : plafond calculé depuis un nombre de lignes qui viendrait du provider — latent, aucun appelant ne passe aujourd'hui de valeur externe, et un `hard_cap` existe. (2) `adapter.server_time` : l'horloge serveur TWS est renvoyée telle quelle, sans comparaison à l'horloge injectée ; aucune limite n'y est ancrée aujourd'hui. (3) `adapter._envelope` : `observed_at` est borné dans le futur mais **pas dans le passé** — un horodatage provider de 1970 est conservé ; la fraîcheur n'est pas compromise (`stale_after` est ancré sur l'horloge locale) mais un `as_of` aberrant peut être affiché. (4) `bar_time` côté passé : non borné, faute de seuil défendable sans connaître l'intervalle maximal autorisé des alertes. (5) `_pending` : borné en TEMPS, pas en NOMBRE — si `pull_and_ingest` est appelé sans jamais appeler `advance_pending`, l'ensemble croît avec le nombre d'alertes valides distinctes. |
| Seuils d'ingress et de qualité : jugements, pas mesures | `REQUIRED_GREEK_FIELDS` (5 champs de risque contre 3 de contexte), et les bornes 2 s / 300 s / 60 s de l'ingress, sont des défauts **injectables et raisonnés**, pas des valeurs mesurées : aucune dérive d'horloge réelle entre Cloudflare et la machine locale n'a été observée, aucune latence TradingView réelle non plus, et ce qu'IBKR livre réellement par base (`bid`/`ask`/`last`/`model`) en live et en delayed n'a jamais été vu. C'est le point le plus susceptible d'être révisé après une sonde d'entitlement réelle. |
| Chaîne PARTIAL non prouvée de bout en bout | Il est prouvé que l'enveloppe de greeks incomplets porte `PARTIAL` ; il n'est PAS prouvé qu'un avis construit dessus est effectivement dégradé. Le mappage `EnvelopeQuality.PARTIAL -> SnapshotQuality.PARTIAL -> DEGRADE` est LU dans `vertex_core/decision/gates.py`, pas exécuté de bout en bout. |
| Bandeau portefeuille — maillon web NON durci | Le garde d'API refuse désormais une `mark_population` sur-revendiquée, donc la charge ne peut plus SORTIR du relais. Mais `PortfolioPage.tsx:105` et `PortfolioSummary.tsx:45` sont inchangés : ils afficheraient toujours « DONNÉES RÉELLES » en ton neutre et recopieraient l'étiquette verbatim. La défense est à un seul étage, côté serveur. Aucune preuve navigateur. |
| Marqueurs synthétiques — filet incomplet par construction | Le test de dérive contre `vertex_core.synthetic` ne couvre que `__all__` : une constante PRIVÉE du générateur ou un futur marqueur non exporté y échappe. Et `vertex_core.synthetic` n'est délibérément PAS importé dans le processus API (décision antérieure : ne pas charger un générateur de données dans l'API) — les constantes sont donc restatées, avec 12 exceptions justifiées épinglées par test. Changer cela est un ADR, pas une ligne de code. |
| Faux positif assumé sur les identifiants | Un instrument réel nommé exactement `SYN`, `SYN1..9`, `SYNTH` ou `SYN-XXXX(-NN)` ferait REFUSER un snapshot honnête. Direction fail-closed, donc la bonne — mais c'est un refus, pas une neutralité. |
| Fusion — le conflit de polarité n'atteint PAS l'utilisateur | Le bloc `conflicts` est écrit dans le snapshot du worker, mais ni `snapshot_views.py` ni l'interface ne le relaient. L'effet visible aujourd'hui est uniquement l'ABSENCE de l'item et une entrée `rejected` typée `QUALITY_OK_FAILED` : l'écran ne dit pas « contradiction détectée ». À traiter dans une vague web. |
| Fusion — la qualité du cluster vient du seul REPRÉSENTANT | `handlers.py` agrège `rights` et `sources` en fail-closed sur TOUS les membres, mais prend `quality` du représentant élu. Un membre `INVALID` ou `STALE` ne ferme donc pas la gate. Même forme d'aveuglement à l'élection que le défaut de polarité, cause différente, portée plus large (des fixtures `STALE` existantes changeraient de compte). Signalé, non corrigé. |
| Fusion — sens encore effacé par la normalisation | Non corrigés, avec la raison : les **parenthèses comptables** (`(5)` vaut −5) — l'appliquer à des titres libres INVENTERAIT un signe (`Apple (AAPL)`), à trancher par ADR ; les **unités et devises** (`100 $` = `100 €` = `100`, `30 %` = `30`) — perte d'unité, pas inversion, mais `financial-safety.md` les exige aux frontières ; l'**approximation** (`≈`, `~`) ; le **ratio** `/`. Les mots de polarité (`hausse`/`baisse`) ne sont délibérément PAS mappés : la polarité lexicale dépend de la langue et relève d'une couche d'extraction. Conséquence assumée : `SPX en baisse de 3,2 %` et `SPX -3,2 %` ne sont ni fusionnés ni déclarés en conflit. |
| Fusion — portée de la détection | Un conflit n'est détecté que là où les titres se RESSEMBLENT déjà : deux titres opposés formulés très différemment (Jaccard < 60 %, sans entité partagée, ou hors fenêtre de 24 h) ne sont ni liés ni signalés. Et le taux de faux scindements sur un vrai flux de dépêches est **inconnu** — toutes les fixtures sont SYNTHETIC. La direction d'erreur est toutefois contrôlée : ajouter un marqueur ne peut produire qu'un scindement visible, jamais une fusion d'opposés. |
| Portefeuille — la borne est à l'ÉCRITURE, pas à la lecture | Une ligne écrite AVANT ce correctif avec `1E+100` (et jusqu'à `1E+131071`, ce que PostgreSQL `numeric` non contraint accepte) reste stockée et sera toujours rendue EN ENTIER par `GET /portfolio` et `/portfolio/export`. Aucune borne n'a été posée en lecture : refuser de servir le journal de l'utilisateur serait pire que l'amplification. La base réelle de l'utilisateur n'a pas été inspectée — on ne sait pas si de telles lignes existent. |
| Portefeuille — aucune pagination | `GET /portfolio` et l'export rendent TOUT le journal, sans pagination ni plafond de lignes. Amplification proportionnelle, pas exponentielle, mais bornée par rien. |
| Décimales hors du relais API | `vertex_worker` et `vertex_core` manipulent aussi des `Decimal` venus du journal ; aucune borne de magnitude n'y a été vérifiée. Le correctif porte sur la frontière d'écriture de l'API, pas sur le domaine. |
| Erreurs SQLAlchemy hors `StatementError` | `ArgumentError`, `NoSuchTableError`, `TimeoutError`… ne sont délibérément PAS couvertes par le gestionnaire : elles ne portent pas de paramètres liés, et les couvrir masquerait de vraies erreurs de programmation derrière un code propre. Leurs messages n'ont pas été audités un par un. |
| Mutation, charge, chaos | Non exécutés (LOT-23). Le seuil de mutation ≥ 95 % sur les modules critiques n'est **pas** vérifié, aucun test de charge ni de chaos n'existe. La campagne de résilience exigée par LOT-23 (codes TWS 1100/1101/1102/1300/502, pacing, doublon/rejeu/désordre/DLQ TradingView, timeout IA, perte réseau, redémarrage PostgreSQL, disque faible, dérive d'horloge) n'a pas été menée. |
| Assertions e2e sous condition | Biome relève **17 assertions sous condition**, dont 16 en e2e : une boucle qui ne trouve aucun cas laisse le test passer **à vide**. Certains sites voisins ont un compteur de garde, d'autres non. Faiblesse réelle de la matrice de preuve, signalée et non corrigée. |
| Fichiers non typés | `apps/web/tsconfig.json` n'inclut que `src` : `e2e/`, `scripts/gen-api.ts` et `playwright.config.ts` ne sont vérifiés par **aucun** `tsc` (Playwright transpile sans typer). Biome les couvre depuis la porte `web-quality`, mais un lint ne remplace pas un typage. |
| Formatage web | Le formateur Biome est **désactivé** : le meilleur réglage réécrirait 61 % des fichiers. La mise en forme n'est donc gardée par aucune porte. Décision mesurée, à reprendre dans un commit purement mécanique. |
| Supply-chain | `uv.lock` verrouille les 60 paquets Python en versions exactes + 1035 hachages sha256 ; `pip-audit --strict` et `pnpm audit --audit-level high` remontent **0 vulnérabilité** (exécutés localement) ; une SBOM CycloneDX 1.6 de 53 composants est produite PAR LA CI (le job supply-chain est vert sur GitHub ; aucun artefact SBOM n'est commité dans l'arbre, et il ne doit pas l'être). Manquent encore : **signature** (cosign), **provenance** SLSA, scan d'image de conteneur, et SBOM du volet Node. |
| Navigateurs | Playwright tourne sur **Chromium** en CI de branche ; Firefox et WebKit par `.github/workflows/nightly.yml`. Les binaires ne sont pas téléchargeables depuis l'environnement de développement (CDN Playwright injoignable) : **toute preuve hors Chromium ne peut venir que de la CI**, et aucune correction visant Firefox ou WebKit n'est vérifiable localement. Les deux premières exécutions et ce qu'elles ont donné sont détaillées dans la section « Trois moteurs de rendu » plus bas. |
| Données | **Aucune donnée réelle n'a jamais été observée.** Tout est `SYNTHETIC` étiqueté ; IBKR n'a jamais été contacté ; Cloudflare n'est pas déployé. |
| Détection de secrets | `tools/check_secrets.py` inspecte l'**arbre suivi**, pas l'historique Git. Un secret introduit puis retiré dans un commit antérieur ne serait pas vu. La détection est par motifs : une forme non listée passe. Le fichier d'allowlist est désormais balayé lui aussi — seules les valeurs de ses champs `match` en sont dispensées. |
| Probabilités | `probability.calibration` est `NOT_IMPLEMENTED` au registre : aucune probabilité prédictive n'est affichable, et aucune ne l'est. |

## Porte `release` — provenance et signature NON FAISABLES ici (décision écrite)

La porte `release` de `docs/06-quality/CI_GATES.md` exige « SBOM, provenance,
signature, notices ». Trois de ces quatre preuves ont un état précis :

| Preuve | État | Détail |
|---|---|---|
| SBOM | **produite** | CycloneDX Python par le job `supply-chain` (`cyclonedx-py`), publiée en artefact 30 jours. Le volet **Node n'a toujours pas de SBOM**. |
| notices | **vérifiée** | `tools/check_notices.py` : inventaire des verrous ↔ `manifests/licenses.yaml` ↔ tableau généré de `THIRD_PARTY_NOTICES.md`. Une licence absente, `UNKNOWN`, refusée ou non classée par la politique BLOQUE. |
| provenance | **NON FAISABLE en l'état** | voir ci-dessous |
| signature | **NON FAISABLE en l'état** | voir ci-dessous |

**Pourquoi rien n'a été ajouté pour provenance et signature.** Ce dépôt ne
publie **aucun artefact** : pas de paquet PyPI, pas de paquet npm, pas d'image
poussée dans un registre, pas de release GitHub. Il n'a pas non plus de démon
de conteneur dans l'environnement de développement (déjà inscrit ci-dessus pour
`infra/compose/`). Signer avec `cosign` suppose un artefact OCI ou une clé et
un registre : ni l'un ni l'autre n'existe. Produire une attestation sur un
fichier que personne ne consomme et qui est supprimé au bout de 30 jours
attesterait la construction d'un objet sans destinataire.

**Ce qui serait techniquement faisable, et ce qui reste à vérifier avant de
l'affirmer.** `actions/attest-build-provenance` produirait une attestation SLSA
signée par Sigstore sur `sbom-python.json`, vérifiable par
`gh attestation verify`. Cela exigerait : (1) une élévation `id-token: write` +
`attestations: write` sur le job `supply-chain` — la porte `policy` imposerait
alors un commentaire `MOTIF-PERMISSION:` nommant chaque portée ; (2) que les
*artifact attestations* soient **effectivement disponibles pour ce dépôt** selon
sa visibilité et le plan GitHub du compte — **ce point n'a pas été vérifié**, et
c'est la raison pour laquelle l'étape n'a pas été ajoutée : une porte ajoutée
sans savoir si elle peut passer n'est pas une preuve, c'est un pari. Trancher ce
point est une décision humaine (visibilité du dépôt et plan), pas un choix
technique réversible.

**Conclusion honnête.** `release` est **partielle** : SBOM Python et notices
sont prouvées par exécution ; provenance et signature sont **absentes et
déclarées absentes**. Aucune porte verte ne les représente. La ligne
`release` de `CI_GATES.md` ne doit pas être considérée comme satisfaite.

## Limites connues des deux portes ajoutées

| Porte | Ce qu'elle NE prouve PAS |
|---|---|
| `policy` | Elle vérifie que chaque `uses:` épingle un SHA de **commit** en le comparant à `manifests/actions-pins.yaml`, résolu à la main par `git ls-remote <dépôt> refs/tags/<tag>^{}`. Hors ligne, la preuve « ce SHA est un commit » vaut ce que vaut ce manifeste ; seule l'option `--resolve-remote` (exécutée par la CI, pas par `run_checks.sh`) le re-résout réellement. Elle ne lit pas le CONTENU de l'action épinglée : un commit épinglé peut être malveillant. |
| `policy` | `LOCK_DESYNC` compare les manifestes aux métadonnées **écrites dans** les verrous (`requires-dist` d'uv, `importers` de pnpm). Cela détecte une déclaration modifiée sans reverrouillage, **pas** une résolution périmée : seuls `uv lock --check` et `pnpm install --frozen-lockfile` prouvent celle-ci, et les deux exigent le réseau. |
| `policy` | `PR_TARGET_CHECKOUT` détecte l'extraction explicite d'une réf de PR sous `pull_request_target`. Un workflow qui exécuterait du code non fiable par un autre chemin (script téléchargé, artefact d'un run précédent) n'est pas détecté. |
| `policy` | Les capacités IBKR interdites restent la propriété de `tools/check_financial_boundary.py`. La porte `policy` vérifie seulement que ce script est **réellement appelé** par la CI et par `run_checks.sh` — c'est la régression qui s'est produite trois fois, pas le contenu du script. |
| `notices` | Elle croit la métadonnée publiée par PyPI et npm. Un paquet qui déclare `MIT` alors que son code est sous une autre licence n'est pas détecté : aucun fichier `LICENSE` n'est comparé, aucun audit juridique n'est fait. |
| `notices` | Hors ligne, elle ne prouve rien sur l'EXACTITUDE d'une licence : elle prouve que registre, verrous et notices sont cohérents entre eux, et trois documents peuvent être cohérents et tous faux. `--verify` les confronte à la source, mais exige le réseau — pendant une panne de registre, `supply-chain` signale sans bloquer et seule l'exécution nocturne (`--require-network`) échoue. |
| `notices` | `role: runtime` / `development` est dérivé du graphe des verrous, pas d'une observation de ce qui serait embarqué dans un artefact — ce dépôt n'en produit aucun. |
| `notices` | Elle ne vérifie pas la présence physique des textes de licence ni des fichiers `NOTICE` exigés par Apache-2.0, et ne dit rien de la compatibilité des licences entre elles. |
| `notices` | **`psycopg` v3 est sous `LGPL-3.0-only`**, seule licence copyleft du runtime. Elle est **reconnue** dans `manifests/policy.yaml` (`licenses.acknowledged_spdx`) avec motif écrit et ne bloque donc pas. Cette reconnaissance **documente une adoption déjà inscrite** (`manifests/dependencies.yaml`), elle ne la valide pas : une revue humaine de cette licence est requise avant toute distribution. |

## Porte `performance` — ce qui est mesuré et ce qui ne l'est pas

La porte `tools/check_performance_budgets.py` applique
`policy.missing_measurement_is_pass: false` : un budget sans mesure échoue.
Le périmètre exigé vit dans `manifests/performance-budgets.yaml`
(`required_measurements`), jamais dans le rapport — sinon livrer un rapport
vide rendrait la porte verte.

**Mesuré, vert, prouvé par exécution :**

| Mesure | Valeur réelle | Budget |
|---|---|---|
| `frontend.bundles.initial_gzip_bytes` | **118 291 octets** (index JS 110 003 + CSS 7 858 + runtime 430) | 307 200 |
| `frontend.bundles.chart_engines_route_chunked` | **vrai** — ECharts (205 ko gzip) et Lightweight Charts (53 ko gzip) hors fermeture statique | vrai exigé |

**Déclaré NON MESURÉ, avec propriétaire, motif, échéance et critère de
clôture** (la porte échoue si l'un de ces quatre champs manque, ou si
l'échéance passe) :

| Mesure | Pourquoi elle n'existe pas |
|---|---|
| `api.page_snapshot.hot_api_snapshot_server.latency_ms.p95` / `.p99` | Aucune mesure de latence API n'a jamais été exécutée. `measurement.minimum_samples` impose 1 000 échantillons pour un p95 et 10 000 pour un p99 : publier en dessous serait un chiffre inventé. Le profil P-LOCAL exige la machine cible, qui n'existe pas encore (LOT-24). |
| `api.page_snapshot.hot_postgresql_query.latency_ms.p95` | Le jeu de données de référence (`datasets`) n'est pas matérialisé. Mesurer sur une base de test vide donnerait un chiffre flatteur et faux. |
| `frontend.tables.rendered_dom_rows_max` | **Aucune table de l'interface n'est virtualisée.** Le nombre de lignes rendues dans le DOM suit le nombre de lignes reçues. Le budget (160 lignes rendues, seuil de virtualisation à 200) ne peut pas être satisfait par une mesure : il doit d'abord être rendu atteignable. Sur le scénario `table_row_counts` à 10 000 lignes, l'interface actuelle rendrait 10 000 lignes. |

**Ce que la porte ne mesure pas du tout** : Web Vitals (LCP, INP, CLS),
mémoire, backpressure, soak de 8 heures, scénarios de charge
(`load_scenarios`), chaîne d'options à 10 000 contrats. Ces sections du
manifeste n'ont aucune entrée `required_measurements` : elles ne sont donc ni
mesurées, ni déclarées non mesurées. C'est la dette la plus large de cette
porte, et elle est nommée ici pour qu'elle ne passe pas pour une couverture.

**Un profil `P-DEV` a été ajouté** au manifeste pour le miroir local : il
n'exige pas `runner_image`, qui n'a de sens que sur un coureur GitHub, et il
n'a **aucune autorité de publication** (`absolute_release_gate: false`).
Couverture, échantillons, échecs durs, étiquettes interdites et régressions
relatives y restent pleinement appliqués.

## Accessibilité — un critère AA non conforme, une revue non faite

Le rapport complet, avec ses mesures, est
`docs/06-quality/ACCESSIBILITY_REPORT.md`. Les deux écarts :

1. **WCAG 1.4.10 (Reflow) — NON CONFORME.** `min-width: 1024px` sur
   l'enveloppe applicative (`apps/web/src/styles/global.css`) fait déborder la
   page de **384 px exactement** à 640 px de large (soit 200 % de zoom sur
   1280 px), sur les 14 chemins mesurés. Aucun contenu n'est perdu — le bord
   droit du `main` se déplace réellement de la largeur manquante, mesuré — mais
   le défilement bidimensionnel que le critère interdit existe. Les tests
   (`apps/web/e2e/accessibility.spec.ts`) épinglent la largeur défilable au
   plancher déclaré : ils échouent si un composant ajoute sa propre largeur
   minimale, c'est-à-dire si la situation empire. Lever l'écart suppose de
   retirer le plancher et de refondre les mises en page larges — un chantier
   d'interface entier, en tension directe avec la décision « desktop only,
   mobile UI = LATER » de la phase 1.
2. **Revue lecteur d'écran — NON FAITE.** Aucune revue par NVDA, VoiceOver ou
   Orca conduite par une personne. `.claude/rules/testing.md` l'exige pour les
   parcours critiques. Aucun outil automatique ne la remplace : les trois
   défauts de libellé corrigés pendant la session (`aria-label` sur des
   éléments sans rôle, où un lecteur d'écran annonçait « tiret » au lieu de
   « bid absent ») avaient été trouvés par le lint, pas par axe.

Ce qui est en revanche **mesuré vert** : **168 cas de test** sur 14 chemins ×
3 viewports — axe restreint aux étiquettes WCAG 2.0/2.1/2.2 A et AA, tous
impacts confondus, zéro violation ; focus visible atteint à la première
tabulation, mesuré par différentiel avant/après `Tab` ;
`prefers-reduced-motion` respecté (zéro animation > 100 ms). Les libellés
antérieurs — « 144 assertions », « 12 routes » — étaient faux deux fois : ce
sont des cas de test, et trois des douze routes étaient mesurées à VIDE parce
qu'elles sont paramétrées et étaient visitées sans paramètre.

## Trois moteurs de rendu — première mesure réelle

`.github/workflows/nightly.yml` a tourné deux fois.

**Exécution 1 (`33311874652`, sur `main`) — ÉCHEC avant toute mesure.** Le job
installait `firefox webkit` sans Chromium ; `e2e/global.setup.ts:169` appelle
`chromium.launch()` pour créer la première passkey via l'authentificateur
WebAuthn virtuel (CDP). Aucun test n'a démarré. Corrigé : le job installe les
trois moteurs.

**Exécution 2 (`33312346908`) — première mesure réelle : 659 passés, 3
échoués, 11,1 min.** Deux causes distinctes, aucune masquée :

1. **`auth.spec.ts:38` sur Firefox ET WebKit** — `context.newCDPSession()`
   lève « CDP session is only available in Chromium ». L'authentificateur
   WebAuthn virtuel n'existe que derrière CDP et Playwright n'expose aucun
   équivalent ailleurs : la cérémonie de connexion par passkey est
   **intestable** hors Chromium. Le test est désormais sauté sur les deux
   autres moteurs, avec le motif écrit.
   **CE QUE CELA LAISSE OUVERT** : la connexion par passkey n'est prouvée que
   sur Chromium. Ce qui reste prouvé partout : l'état « Session requise » sans
   session, et les 659 tests qui tournent authentifiés par l'état de session
   enregistré au setup.
2. **`performance.spec.ts:92` sur WebKit seul — DÉFAUT PRODUIT.** L'export
   « CSV + manifeste » de la page Performance ne produisait **qu'un fichier sur
   deux** : le CSV partait, le manifeste d'audit jamais. Un utilisateur Safari
   ne l'aurait jamais reçu. L'utilitaire de téléchargement existait en **trois
   copies** ; elles sont remplacées par `src/app/downloadFile.ts`,
   propriétaire unique.

**Exécution 3 (`33313838830`) — 659 passés, 2 sautés, 1 ÉCHOUÉ, 9,7 min.** La
limite CDP est réglée (2 sautés, avec motif écrit). Le défaut WebKit, lui, a
**résisté au premier correctif** : différer `URL.revokeObjectURL()` et rendre
la main entre les deux enregistrements n'a rien changé, l'échec s'est reproduit
à l'identique.

Ce que la mesure dit vraiment : **un** téléchargement par geste utilisateur
passe sur les trois moteurs, deux ne passent pas sur WebKit. Plutôt qu'une
troisième variante invérifiable localement, la dépendance au
multi-téléchargement est SUPPRIMÉE : la page Performance a deux boutons —
« Exporter les points » et « Exporter le manifeste ». Le contenu exporté est
inchangé, les deux fichiers restent ceux servis par l'API. La révocation
différée est conservée comme hygiène, mais elle reste une **hypothèse non
prouvée** : rien ne montre qu'elle corrige quoi que ce soit.

**Exécution 4 (`33314910817`) — VERTE : 665 passés, 2 sautés, 0 échoué,
11,2 min sur Chromium, Firefox ET WebKit.** Le produit passe pour la première
fois sur les trois moteurs de rendu. Les 2 sautés sont la cérémonie passkey,
intestable hors Chromium, avec son motif écrit ; le trou qu'ils laissent est
nommé ci-dessus et reste ouvert.

Ce que cette campagne a coûté à la confiance dans les chiffres antérieurs : il
a fallu QUATRE exécutions, dont trois rouges, pour obtenir la première mesure
verte hors Chromium. 234 tests Chromium verts n'avaient rien dit d'un export
cassé sur un moteur sur trois, et le premier correctif de ce défaut était une
hypothèse fausse — seule la troisième exécution l'a démontré.

Ce que cette campagne a coûté à la confiance dans les chiffres antérieurs :
234 tests Chromium verts n'avaient rien dit d'un export cassé sur un moteur
sur trois. Le produit n'a jamais été observé hors Chromium avant le 30 août.

## Campagne chaos LOT-23 — ce qu'elle couvre, ce qu'elle ne couvre pas

`apps/worker/tests_integration/test_chaos_degradation.py` : 12 scénarios sur
PostgreSQL réel. Duplication de livraison, rejeu complet après traitement,
désordre temporel, dérive d'horloge (données venant du futur), population
périmée à 2 / 30 / 400 jours, interruption en plein drain, et l'invariant
transversal « aucune dégradation ne produit un avis affirmatif ».

Cette campagne a trouvé une régression P0 pendant sa propre écriture :
`isinstance(envelope, DataEnvelope)` avait été remplacé par
`isinstance(envelope, DataEnvelope[Any])` lors d'une passe de typage. Avec les
génériques Pydantic, `DataEnvelope[Any]` est une classe concrète distincte de
`DataEnvelope[dict[str, Any]]` : toute la chaîne d'ingestion était cassée. Le
cas général — une annotation d'apparence cosmétique qui change un comportement
runtime — mérite d'être surveillé à chaque passe de typage.

**Non couvert, et non simulé** :

- disque plein et échec d'écriture PostgreSQL : aucune simulation honnête
  possible sans conteneur ni quota ; un faux donnerait une fausse assurance ;
- redémarrage réel de PostgreSQL en cours de transaction (il n'y a pas de
  démon de conteneur dans l'environnement de construction) ;
- codes TWS 1100 / 1101 / 1102 / 1300 / 502 : couverts par
  `apps/edge-ibkr/tests/test_state_machine.py` au niveau de la machine à
  états, **pas** de bout en bout jusqu'à un verdict publié ;
- alertes TradingView forgées, vieilles, futures, dupliquées, désordonnées et
  trop grosses : couvertes par le contrat du Worker Cloudflare
  (`node --test`) et `apps/ingress-tradingview/tests`, **pas** de bout en bout ;
- timeout du fournisseur d'IA : le fournisseur est désactivé (décision B-05) ;
  il n'y a rien à faire expirer.

**Comportement documenté, découvert par la campagne** : au-delà de la fenêtre
`AnalysisConfig.lookback` (72 heures), aucun dossier d'analyse n'est publié —
la fenêtre bornée ne contient plus de barres. Le silence est propre (aucun
message échoué, aucun mort, aucun bloqué) et le dossier précédent garde sa
version et son `as_of` d'origine : l'ancienneté n'est pas blanchie par une
activité ultérieure. La fraîcheur est donc jugée **à la lecture**, sur
`as_of`, et non republiée. C'est cohérent avec l'architecture par snapshots
immuables ; ce n'était écrit nulle part avant ce test.

## Matrice de traçabilité — 24 interdictions prouvées sur 30, 6 écarts

`manifests/traceability.yaml` relie chaque interdiction absolue de
`CLAUDE.md` et de `.claude/rules/financial-safety.md` à la preuve qui
l'établit. La porte `tools/check_traceability.py` imprime les écarts à chaque
exécution. Ce qu'elle a révélé :

| Interdiction | Écart |
|---|---|
| Afficher une probabilité prédictive non calibrée (deux formulations, `CLAUDE.md` et `financial-safety.md`) | La règle d'abstention est prouvée **côté recherche** (`research/tests/test_calibration.py`), pas **au point d'affichage**. Aucune probabilité n'atteint l'interface aujourd'hui, et aucun test ne prouve que l'interface en refuserait une mal formée. |
| Copier un fichier du dépôt donneur sans inventaire | `tools/inventory_donor.py` et l'inventaire existent, mais aucun test ne vérifie qu'une copie non inventoriée serait détectée. La règle repose sur la discipline, pas sur une porte. |
| Ajouter un framework sans ADR | La porte `policy` prouve l'épinglage et le verrouillage, `notices` l'inventaire et la licence. **Rien ne relie une dépendance à un ADR accepté.** |
| Travailler sur `main`, force-push, fusionner sans validation humaine | Déclarée **NON PROUVABLE PAR TEST** : protections de branche et droits de fusion vivent dans la configuration GitHub, qu'aucun test exécuté dans un checkout ne peut lire. Reste une vérification humaine. |

Le sixième écart est `EXCEPTION-JAMAIS-QUALIFIED`, rétrogradé de `PROVEN` à
`NOT_YET_PROVEN` : sa seconde moitié — « ni conserver silencieusement un
ancien verdict » — est **contredite par une mesure**, celle des +71 heures
décrite plus bas.

Une version antérieure de ce paragraphe affirmait qu'« il n'existe aucun
balayage statique du dépôt web équivalent à `check_financial_boundary` pour
les calculs financiers en TypeScript ». **C'est faux depuis `fdc9dfc`** :
`no-authoritative-calculation.test.ts` balaie tout `apps/web/src` par AST et
refuse toute arithmétique sur une grandeur financière relayée (vocabulaire
fermé de 35 noms, 9 injections à détecter, 6 à ignorer), et
`no-uncalibrated-probability.test.ts` réserve la lecture de
`probability_evidence`. Ce qui reste vrai : les deux gardes lisent
`apps/web/src` et rien d'autre, et aucune ne voit une expression construite
dynamiquement.

Ce que la matrice ne prouve toujours pas, et qui est désormais écrit dans
chaque entrée concernée : `NATURES-JAMAIS-CONFONDUES` et
`FALLBACK-JAMAIS-PRESENTE-COMME-REEL` sont prouvées au niveau des
**composants**, sans qu'aucun balayage n'établisse qu'une page ne peut pas les
contourner ; `UNITES-AUX-FRONTIERES` est prouvée aux **quatre frontières
citées**, pas à toutes ; `AUCUN-VOCABULAIRE-D-ORDRE` ne balaie que
l'interface, donc un impératif d'ordre écrit dans une réponse serveur
atteindrait l'écran sans être vu.

## Mutation testing — TENTÉ, ÉCHOUÉ, aucun score publiable

`.claude/rules/testing.md` exige un score de mutation d'au moins 95 % sur les
modules critiques, sans mutant dangereux survivant. **Le score réel est
inconnu.** Ce n'est pas une estimation basse : c'est une absence de mesure.

Deux tentatives ont été faites avec `mutmut==3.7.0` (déjà adopté par
`manifests/dependencies.yaml`, `adopt.test`), sur `vertex_core.decision` —
les gates et l'`AdviceEngine`, seule autorité de verdict du produit. Les deux
ont rendu **exactement le même résultat : 6 017 mutants générés, 6 017
ignorés, 0 tué, 0 survivant, « 0.00 mutations/second »**. Un score de zéro qui
ne mesure rien.

Cause identifiée : `mutmut` 3 recopie l'arbre source dans `mutants/` et y
exécute pytest, mais le dépôt est un workspace `uv` en disposition `src`
installé en ÉDITABLE. Les tests importent donc le paquet réel, pas la copie
mutée ; la phase de statistiques n'associe aucun test aux fichiers mutés, et
tous les mutants sont classés « non couverts ». Forcer
`PYTHONPATH=mutants/packages/python/vertex_core/src` fait bien pointer un
`import vertex_core.decision.gates` vers la copie — vérifié — mais ne suffit
pas à `mutmut`, y compris avec l'arbre `mutants/` déjà présent au démarrage
(seconde tentative, faite précisément pour écarter l'hypothèse du répertoire
inexistant au lancement).

**L'outil et sa configuration ont été RETIRÉS du dépôt** plutôt que laissés
en place. Un `setup.cfg` configuré qui produit « 0 tué / 6 017 ignorés » est
un artefact qui ressemble à une campagne et n'en est pas une ; c'est
exactement le type de vert sans preuve que ce dépôt interdit. Le
reverrouillage a aussi entraîné trois composants tiers de plus (`rich`,
`setproctitle`, `textual`) et la porte `notices` en rouge — coût inutile pour
une mesure inexistante.

Ce qu'une prochaine tentative doit résoudre AVANT de recommencer : faire en
sorte que la copie de `mutants/` soit la seule `vertex_core` importable
pendant toute la campagne, statistiques comprises. Les pistes non explorées
sont une installation non éditable dans un environnement dédié à la campagne,
ou un outil dont le modèle d'exécution ne repose pas sur la recopie de
l'arbre (`cosmic-ray` mute en place).

## Neuvième audit — deux verdicts REJECT, et ce qui reste ouvert

Deux audits adversariaux indépendants, l'un sur les cinq nouvelles portes,
l'autre sur la matrice et les campagnes. Chaque constat repris ici a été
**confirmé par exécution** avant d'être écrit.

### Corrigé dans ce lot

| Défaut | Preuve exécutée |
|---|---|
| `run_checks.sh` invoquait onze portes en `porte && echo OK` : sous `set -e`, l'opérande gauche d'un `&&` est exemptée de l'arrêt sur erreur | la porte rend 1, le script rend 0 et imprime « TOUT VERT ». **Quatrième** contournement de la frontière financière |
| `check_policy` vérifiait le câblage par `script in text` | un commentaire, `if: ${{ false }}`, `\|\| true` et `continue-on-error` passaient tous les quatre |
| `known_not_wired` endormait n'importe quelle porte pour une phrase | la frontière financière endormie avec « suspendue le temps d'un refactor », porte verte |
| Trois littéraux concurrents de la partition de statut, dont un sans `OBSERVE` | `vertex_worker.opportunities`, `test_advice.py` et la campagne chaos ne s'accordaient pas |
| La garde anti-ordre ne contenait que de l'anglais | `<button>Acheter</button>` passait au vert dans une interface française |
| La campagne chaos ne discriminait rien | en substituant `INSUFFICIENT_DATA` à l'ensemble affirmatif, seuls 4 tests sur 8 rougissaient : quatre bouclaient sur un statut constant, quatre sur **zéro dossier** |

### DÉFAUT PRODUIT OUVERT — un dossier publié se dit encore frais 71 h plus tard

Mesuré : un dossier d'analyse publié conserve
`snapshot_fresh_and_coherent = PASS / FRESH_AND_COHERENT` à +47 h et +71 h,
alors que `AnalysisConfig.bars_freshness` vaut 48 h. Aucune observation
nouvelle ne déclenche de republication, et le snapshot est immuable.

Pris isolément ce n'est pas faux : la fraîcheur DOIT se juger à la lecture, sur
`as_of`. Mais ce registre mesurait par ailleurs que **8 relais sur 10** ne la
recalculaient pas. Verdict gelé plus relais permissif se combinaient en
« périmé présenté comme frais » — ce que `.claude/rules/financial-safety.md`
interdit sous le nom de « conserver silencieusement un ancien verdict ».

**La moitié RELAIS est fermée au LOT-24c.** Les dix relais publient désormais
`age_seconds` et basculent sur `stale` au-delà de leur budget déclaré : à +71 h
le dossier arrive avec ses 255 600 secondes. Le mot « silencieusement » ne
s'applique plus.

**La moitié WORKER reste ouverte, et le mot juste n'est plus « silencieux »
mais « contradictoire ».** La gate `snapshot_fresh_and_coherent` interne au
dossier continue d'affirmer `FRESH_AND_COHERENT` à +71 h alors que sa propre
fenêtre de 48 h est dépassée ; le budget de relais de `daily_bar` (72 h) ne la
contredit pas encore à cet instant. Le dossier porte donc, sur le même
message, un âge de 255 600 s À CÔTÉ d'une gate qui se dit fraîche. C'est une
amélioration réelle et une incohérence qui reste à traiter.

`test_defaut_connu_un_dossier_publie_se_dit_encore_frais_bien_plus_tard`
épingle la réalité mesurée et **échouera le jour où le défaut sera corrigé**,
forçant à revenir retirer la caractérisation. L'entrée
`EXCEPTION-JAMAIS-QUALIFIED` de `manifests/traceability.yaml` reste
`NOT_YET_PROVEN`, et ce n'est pas un oubli : son critère de fermeture ÉCRIT
(le recalcul de fraîcheur à la lecture, plus un test) est livré par le
LOT-24c, mais promouvoir l'entrée sur cette seule base serait gagner contre ma
propre formulation, pas contre la règle. Le critère a donc été RESSERRÉ sur ce
qui reste vrai : que la gate interne cesse elle-même de se déclarer fraîche
au-delà de la fenêtre qu'elle invoque. Le défaut LUI-MÊME reste ouvert.

### Fraîcheur au relais — ce qu'une sonde a mesuré avant d'écrire le lot

En préparant la correction, une sonde a mesuré un écart qui change le plan :
le TTL de séance FERMÉE de la politique `daily_bar` vaut **72 h**
(`vertex_core.data.freshness`), alors que le worker juge les barres fraîches
sous **48 h** (`AnalysisConfig.bars_freshness`). Un relais qui prendrait
`daily_bar` comme budget — c'est ce que fait déjà `opportunities.py`, avec
son motif écrit — ne déclarerait donc PAS périmé le dossier mesuré à +71 h.

Deux conséquences pour le lot à venir :

1. **Le correctif utile n'est pas de resserrer un budget.** Inventer un TTL
   plus court pour que le chiffre paraisse meilleur serait exactement la
   valeur non justifiée que ce dépôt refuse ailleurs. Ce qui ferme le défaut,
   c'est que le relais PUBLIE l'âge (`age_seconds`) et l'état dans tous les
   cas : à +71 h le dossier est servi avec « 255 600 s », donc le verdict gelé
   n'est plus présenté SANS SA DATE — et c'est le mot *silencieusement* que
   `financial-safety.md` interdit.
2. **Il reste une bande de 24 h** où un dossier est servi `ok` alors que sa
   propre gate a été calculée sous une règle plus stricte. Resserrer
   `daily_bar` a un coût réel (déclarer périmé pendant un long week-end) : la
   décision appartient au registre des politiques, pas à un relais, et exige
   un ADR.

Un module partagé `vertex_api.freshness` a été écrit puis RETIRÉ de ce lot :
sans appelant il aurait été du code mort, et migrer `calendar.py` et
`opportunities.py` dessus — ils dupliquent déjà cette logique, avec des
tolérances de dérive différentes (5 s côté opportunités) — est un lot à part
entière. `.claude/rules/architecture.md` interdit de mélanger une refonte du
chemin de fraîcheur avec un lot de démarrage.

### Encore ouverts, mesurés, non corrigés

- ~~**La matrice compte des déclarations, pas des preuves.**~~ — **FERMÉ**.
  Les 67 citations nomment maintenant un test précis, comparé par égalité
  EXACTE à la liste des fonctions `test_*` du fichier (les classes et les
  helpers ne sont plus collectés). Une citation de fichier entier échoue
  désormais (`proof_not_anchored`). Falsifié : `::t`, `::e`, `README.md` et
  un fichier de tests cité nu sont tous refusés, et l'ancre exacte passe.
  Le champ `text` est en outre confronté mot pour mot à la règle : 14 entrées
  sur 30 divergeaient, dont une énonçant une interdiction PLUS ÉTROITE que le
  document. Trace de l'ancien défaut : 58 citations sur 67
  n'avaient pas de `::` et étaient validées par le seul `path.is_file()` ; une
  citation `::nom` était résolue par SOUS-CHAÎNE contre tous les
  `FunctionDef`/`ClassDef`, helpers compris. `README.md` cité comme preuve
  d'« Envoyer un ordre IBKR » passe ; `test_ai_explain.py::t` aussi.
- ~~**Le champ `text:` de la matrice n'est jamais confronté à la règle**~~ —
  **FERMÉ** avec le point ci-dessus. `API-COMPTE-SAFETY` omettait « résumé de
  compte », « allocations » et « identifiants d'ordre » : un lecteur se fiant
  à la matrice aurait cru l'interdiction plus étroite qu'elle n'est.
- ~~**`check_secrets` ne balaie pas les commentaires de sa propre
  allowlist**~~ — **FERMÉ**. L'exemption ne porte plus sur le fichier entier
  mais sur les valeurs des champs `match`, et sur elles seules ; commentaires,
  champs `reason` et clés inconnues sont balayés comme partout ailleurs. La
  preuve passe par `main()`, pas par `scan_text` : le contournement vivait dans
  `main()`. Falsifié — en remettant le saut du fichier, le test vire au rouge.
- ~~**`check_notices` ne revérifie jamais une licence hors ligne**~~ —
  **FERMÉ**. `--verify` relit chaque licence chez le distributeur et échoue sur
  divergence, sans rien réécrire. Mesuré sur le dépôt réel : 245 licences
  relues, 0 injoignable, 0 divergence ; et le blanchiment `LGPL-3.0-only` → MIT
  rejoué est détecté et nommé. Câblé dans `supply-chain` (tolère un registre
  injoignable) et dans `nightly` avec `--require-network` (ne le tolère pas).
  Ce que cela ne ferme PAS : la porte croit toujours la métadonnée publiée, et
  la protection de branche dépend du réseau — un registre injoignable pendant
  une panne laisse passer une divergence jusqu'à l'exécution nocturne.
- ~~**La porte `performance` ne peut pas bloquer sur son budget
  numérique**~~ — **FERMÉ**. Un budget `max` doit désormais déclarer
  `machine_independent`, et un dépassement sur un budget indépendant de la
  machine bloque à TOUT profil : un compte d'octets gzip est le même sur
  chaque coureur, il n'existe aucune machine sur laquelle 10 Mo au lieu de
  300 ko soit acceptable. Omettre le champ échoue (`machine_independence_
  undeclared`) : la branche permissive était le défaut, c'est ainsi que le
  dépassement de 32× est passé. Les budgets sensibles à la machine (latences)
  restent soumis au profil — une latence mesurée sur un coureur partagé ne dit
  rien de la machine cible.
  Ce que cela ne ferme PAS : `enforcement.absolute_targets_block_pr` reste
  `false`, donc aucune latence n'est encore bloquante nulle part.
- ~~**Trois routes d'accessibilité mesuraient un état vide**~~ — **FERMÉ**.
  `/analysis` et `/options` sont désormais mesurées vides ET peuplées
  (`SYN-TECH-01`) : 14 chemins, 168 cas de test, tous verts. `/simulator` sans
  paramètre rend bien son composeur complet — c'était la page, pas un encart.
  **`/auth` a toujours ZÉRO couverture d'accessibilité** ; le rapport ne
  prétend plus le contraire, mais la route reste non mesurée.
- ~~**L'assertion « aucun contenu perdu » est une tautologie**~~ — **FERMÉ**.
  Elle mesure maintenant le déplacement observé du bord droit du `main`, qui
  doit valoir exactement le manque au plancher. Le test de plancher reste en
  revanche **aveugle aux sept conteneurs `overflow-x: auto`** de `global.css` :
  cette limite est écrite dans le rapport, elle n'est pas levée.
- ~~**« Focus visible » est satisfait par une ombre permanente**~~ — **FERMÉ**.
  Différentiel `blur()`/`focus()` avant/après `Tab`.
- ~~**Deux mutants survivants**~~ — **FERMÉS**. Retirer le CSS de la charge
  initiale (`measure_web_bundle.py`) fait rougir deux tests qui mesurent
  l'écart. Neutraliser la comparaison de `role` (`check_notices.py`) en fait
  rougir deux autres : ce champ décide de la SECTION du tableau des notices —
  `runtime`, embarqué chez l'utilisateur, ou `development` — et un composant
  copyleft reclassé à la main sortait de la section qui l'expose sans que rien
  ne bronche. Un rôle vide ou absent est traité comme une divergence, pas comme
  une absence de contrainte.
- ~~**`P-DESKTOP` porte `absolute_release_gate: true` sans aucune
  `required_metadata`**~~ — **FERMÉ**. Le profil exige `cpu`, `ram_mib`,
  `os_kernel`, `browser_version`, `viewport` et `device_pixel_ratio`, et un
  test balaie le manifeste réel : aucun profil à autorité absolue ne peut
  désormais se passer de décrire sa machine.

## Trouvé au LOT-07 (2026-08-31)

- **`LEDGER_CODE_BY_PAGE` retombait en silence sur `TL / —`** — **FERMÉ dans le
  même lot.** Renommer la clé de page `system` en `sources-reports` a laissé
  `apps/web/src/shell/AppShell.tsx` indexé sur l'ancienne clé ; la signature
  Titanium Ledger de la page basculait sur son repli sans qu'aucun des 397 tests
  ne bronche — le seul test existant vérifiait `/markets`. Corrigé, et un
  garde-fou balaie désormais **les douze** pages du rail : aucune ne peut
  retomber sur `TL / —`. Falsifié (remettre la clé `system` fait rougir
  `expected [ 'sources-reports' ] to deeply equal []`). Les trois absorptions
  suivantes passeront par cette porte.
- **L'ordre des signatures `TL / NN` diverge des planches canoniques**
  — **OUVERT**, hors périmètre du LOT-07. Les planches du skill imposent
  `01 today, 02 markets, 03 opportunities, 04 analysis, 05 options,
  06 simulator, 07 portfolio, 08 charts, 09 risks, 10 catalysts, 11 calendar,
  12 sources-reports`. `AppShell.tsx` porte aujourd'hui `02 opportunities,
  03 analysis, 04 options, 05 simulator, 06 calendar, 07 markets` — six codes
  attribués à d'autres destinations. Ce n'est pas une régression de ce lot :
  l'écart préexiste. Il ne peut pas non plus se corriger avant que Graphiques,
  Risques et Catalyseurs existent, faute de quoi `08`, `09` et `10` désigneraient
  des pages absentes. À traiter dans la refonte Titanium Ledger, après les
  créations.

## Trouvé au LOT-09 (2026-08-31)

- **Un masque CSS invalide échoue en silence** — **FERMÉ.** `BrandMark.tsx`
  écrivait `url(${dataUri})` sans guillemets. Une data URI SVG contient des
  apostrophes et des virgules : la déclaration `mask-image` était donc
  invalide, le navigateur la calculait à `none`, et `background-color:
  currentcolor` remplissait tout le carré. La « marque facettée argent » du
  point 1 de l'anatomie s'affichait en **pavé plein**, sans la moindre erreur
  console. `NavGlyph.tsx` guillemetait déjà son URL — le catalogue d'icônes
  était correct, la marque seule ne l'était pas. Corrigé, et
  `shell-canonical.spec.ts` assère désormais `maskImage !== 'none'` : une
  assertion de couleur ne pouvait pas voir ce défaut, seule une assertion sur
  l'application du masque le peut. Falsifié.
- **Le point 5 de l'anatomie canonique n'est pas livré** — **OUVERT, assumé.**
  La capture montre en haut à droite un badge de mode (`DONNÉES FICTIVES`),
  une cloche et une fraîcheur (`Dernière mise à jour ... UTC`). Aucun des trois
  n'a de propriétaire canonique côté shell : il n'existe ni file de
  notifications, ni mode de données au niveau du shell, ni fraîcheur globale.
  L'emplacement a été LIBÉRÉ (l'édition est partie au pied du rail) mais reste
  vide : une cloche sans notifications ou un badge de mode sans propriétaire de
  mode serait exactement la façade que l'article 17 interdit. À traiter quand
  ces trois sources existeront.

  **Précisé au LOT-14, et la nuance compte.** Le ticker publie bien une
  population et un âge, et la capture canonique montre bien un badge
  `DONNÉES FICTIVES` en haut à droite. Ce ne sont PAS les mêmes objets : ceux
  du ticker qualifient l'instantané `markets_overview`, celui de la capture
  qualifie l'application. Les déplacer dans le coin haut-droit leur donnerait
  une portée « Vertex » qu'aucune source ne publie — il n'existe ni mode de
  données global, ni fraîcheur globale, `population` étant un champ PAR
  instantané. Ils restent donc portés par la bande. L'emplacement du point 5
  reste vide, et c'est maintenant une décision argumentée, plus seulement un
  constat d'absence.
- **Le point 6 (inspecteur contextuel)** — **EMPLACEMENT LIVRÉ au LOT-11,
  REMPLISSAGE PARTIEL.** Le shell porte l'aside, sa largeur canonique et sa
  règle « aucune colonne morte ». Une seule destination le remplit
  aujourd'hui : Catalyseurs. Les dix autres n'ont pas encore d'élément
  inspectable déclaré — elles n'affichent donc aucune colonne, ce qui est le
  comportement voulu, pas un manque masqué. Le contrat des douze pages fixe le
  contenu attendu pour chacune ; il reste à le livrer page par page.
- ~~**Le point 4 (ticker horizontal) n'est pas livré**~~ — **FERMÉ au LOT-14,
  et la raison écrite ici était FAUSSE.** L'entrée disait qu'il exigeait « une
  décision de charge réseau ET UN CONTRAT ». La moitié « contrat » était
  inexacte : `/api/v1/markets/overview` publie `MarketsTicker` depuis la
  première vague — `ticker`, `last_close`, `return_1d_pct`, `currency`,
  `quality`, `synthetic`, `trading_day` — tous calculés et formatés par le
  worker. Rien ne manquait côté serveur.

  **Dixième chiffre ou affirmation erronée de ce registre**, et la même erreur
  que Catalyseurs au LOT-10 : une destination déclarée « sans contrat » l'était
  en réalité par défaut de vérification, pas par défaut de contrat. La
  vérification refaite le 2026-09-01 contre les 30 routes du contrat OpenAPI a
  suffi à la lever. Règle retenue : une entrée de dette qui affirme « le
  contrat manque » doit NOMMER la route absente ; sans nom, elle n'est qu'une
  supposition.
- **L'ordre des signatures `TL / NN`** reste ouvert (voir LOT-07) : rien n'a
  changé, les trois destinations manquantes sont toujours la condition
  préalable.

## Trouvé au LOT-12 (2026-09-01)

- **Un panneau accessoire pouvait faire tomber sa page hôte** — **FERMÉ.**
  `AiAnswerView` parcourait sans garde les six listes que le contrat `AiAnswer`
  promet. Une réponse hors contrat servie à `/v1/ai/explain` faisait échouer
  `ClaimsBlock` sur `catalog is not iterable`, et l'erreur remontait jusqu'à la
  frontière de route React Router : c'était la page ENTIÈRE — analyse, avis,
  barres — qui disparaissait à cause d'un panneau d'explication.

  Le défaut PRÉEXISTAIT ; il était invisible tant que l'explication vivait
  seule sur sa propre destination, où elle n'avait qu'elle-même à emporter.
  L'absorption dans l'inspecteur l'a rendu visible en la plaçant à côté d'un
  dossier financier. Corrigé par `isWellFormedAnswer` : une réponse hors
  contrat se dégrade en état `error` visible et le dossier de l'hôte reste
  intact. Falsifié — neutraliser la garde fait réapparaître l'erreur.

  **Règle générale à retenir pour les absorptions restantes :** un composant
  déplacé dans un hôte hérite de la responsabilité de ne jamais le faire
  tomber. À vérifier pour chaque panneau monté dans l'inspecteur.
- **Le bandeau B-05 n'est plus rendu hors ligne** — **ASSUMÉ, non régressif.**
  L'ancienne page le gardait visible en état dégradé. Le panneau n'étant plus
  monté quand aucun dossier n'est ouvert, le bandeau disparaît avec lui. Il ne
  disparaît PAS d'un écran qui montre une explication : c'est l'explication
  entière qui est absente, donc aucune phrase non qualifiée n'est jamais
  affichée. L'invariant qui compte — jamais d'explication sans le bandeau — est
  désormais asséré explicitement sur les deux pages hôtes.
- **Un test unitaire poussé cassé, faute d'avoir relancé la suite après un
  changement de structure** — **FERMÉ, et la cause est un manquement de
  process, pas un test instable.** Au LOT-12, le montage du panneau
  d'explication a été déplacé à l'intérieur de la branche « dossier chargé »
  d'Analyse pour supprimer un second état hors ligne. Ce déplacement a
  invalidé un test écrit quand le panneau était monté à l'extérieur : son mock
  ne servait pas `/v1/analysis/…`, donc le dossier ne chargeait jamais.

  Après ce déplacement, seule la campagne e2e a été relancée ; la suite
  unitaire ne l'a pas été. La CI l'a attrapé, et l'écart a été poussé en
  attendant. Le test échouait 3 fois sur 3 en isolation : il n'était pas
  flaky, il était faux.

  **Règle retenue :** toute modification de la STRUCTURE de rendu d'un
  composant (déplacement d'un montage, changement de branche conditionnelle)
  invalide potentiellement des mocks écrits pour l'ancienne structure. La
  suite unitaire doit être relancée après ce type de changement, pas seulement
  la campagne e2e qui l'a motivé.

## Trouvé au LOT-13 (2026-09-01)

- **Une capture d'écran lue sans vérifier que le run l'avait produite** —
  **incident de méthode, corrigé.** Après une modification CSS, deux captures
  ont été lues et commentées alors que le `pnpm build` de la campagne
  ÉCHOUAIT : les images étaient celles du build précédent. La conclusion tirée
  (« le correctif n'a rien changé ») était donc fausse, et fondée sur une
  preuve périmée.

  Cause du build cassé : une suppression de règle CSS par expression
  régulière avait laissé une accolade orpheline, que `lightningcss` refuse.
  Le test unitaire et `tsc` ne voient pas le CSS ; seul le build le compile.

  **Règle retenue :** ne jamais lire un artefact (capture, rapport, export)
  sans avoir vérifié le CODE DE SORTIE du run qui devait le produire. Et après
  toute édition de `global.css`, lancer `pnpm build` — la suite unitaire ne
  compile pas la feuille de style.
- ~~**Options porte encore un inspecteur modal**~~ — **FERMÉ.** Converti au
  LOT-13 avec la même recette qu'Aujourd'hui. Il ne reste plus aucun
  `role="dialog"` ni `aria-modal` dans l'application, et les deux pages
  asserent la propriété non modale : depuis le dernier élément du panneau, la
  tabulation SORT vers le reste de la page.

## Trouvé au LOT-14 (2026-09-01)

- **Le ticker squattait `data-state`** — **FERMÉ.** La bande portait
  `data-state={queryState}`, alors que cet attribut appartient à
  `DataStateBoundary`. Hors ligne, `[data-state="offline"]` résolvait donc à
  DEUX éléments sur chaque page, et la campagne e2e est tombée d'un coup :
  **58 échecs sur 435**, répartis sur onze fichiers. Renommé en
  `data-ticker-state`.

  **Ce qui a failli passer inaperçu, et c'est le vrai enseignement.** La
  première campagne a rendu un résumé « 377 passed » avec un code de sortie 0
  relayé par l'outillage. Les deux étaient trompeurs : `377 = 435 - 58`, et
  `e2e-artifacts/test-output/.last-run.json` disait `"status": "failed"` avec
  58 identifiants. Sans cette relecture, un lot rouge aurait été déclaré vert.

  **Règle retenue, qui prolonge celle du LOT-13 :** un résumé de campagne ne
  vaut que confronté au compte DÉCLARÉ (`playwright test --list`). Un total
  qui ne correspond pas au nombre de tests déclarés est un échec silencieux,
  quel que soit le code de sortie affiché.
- **Un composant de shell rend AMBIGUËS les assertions de page** — **FERMÉ,
  et généralisable.** Trois fichiers unitaires et sept fichiers e2e cherchaient
  `DONNÉES SYNTHÉTIQUES` dans TOUT le document. Le ticker portant sa propre
  étiquette de population, ces recherches en trouvaient deux. Les assertions
  sont désormais portées par `main` — ce qui est plus fort, pas plus faible :
  elles prouvent que la PAGE porte son bandeau, ce que la recherche globale ne
  prouvait déjà plus.

  **Troisième occurrence de la MÊME classe, trouvée à la campagne suivante :**
  `portfolio.spec.ts` remplissait un champ par `page.getByLabel(/^Ticker/)`.
  L'`aria-label` de la bande — « Ticker des marchés » — matche ce motif, donc
  le locator résolvait à deux éléments. Scopé à `main` lui aussi.

  Après cette troisième, la recherche a été faite EXHAUSTIVEMENT plutôt qu'une
  occurrence à la fois : balayage de tous les `page.getBy*` non scopés des 17
  fichiers e2e contre l'ensemble des textes et rôles que la bande introduit
  (nature, âge, marques de dégradation, symboles, les cinq messages, `region`,
  `list`, `listitem`). Deux seuls candidats restants, tous deux des
  `getByTestId` — un identifiant de test est unique à sa page, donc sans
  collision possible.

  **Règle retenue :** tout ajout au SHELL doit être confronté aux assertions
  non scopées des pages avant d'être poussé, et cette confrontation doit être
  EXHAUSTIVE dès la première collision. Le shell est rendu sur les douze
  destinations : ce qu'il ajoute, il l'ajoute partout. Trois campagnes ont été
  dépensées ici à découvrir une occurrence à la fois ce qu'un balayage
  donnait d'un coup.
- **`fetchMock.mockResolvedValue(uneRéponse)` est un piège** — **corrigé dans
  les tests touchés.** Un `Response` ne se lit qu'une fois. Depuis que le shell
  interroge le ticker, deux requêtes partent par rendu : la première consomme
  le corps, la seconde reçoit une réponse vide. `src/test/shellQueries.ts` route
  désormais par chemin et fabrique une réponse neuve à chaque appel.
- **« Aucune requête envoyée » n'est plus un invariant testable** —
  **remplacé par plus précis.** Deux tests du simulateur asseraient
  `expect(fetchMock).not.toHaveBeenCalled()`. Ce qu'ils protègent est qu'aucune
  PRÉVISUALISATION ne part, pas qu'aucun octet ne circule. Ils asserent
  maintenant l'absence de `/api/v1/simulations/preview` dans les chemins
  appelés, plus l'absence de tout appel autre que celui du shell.
