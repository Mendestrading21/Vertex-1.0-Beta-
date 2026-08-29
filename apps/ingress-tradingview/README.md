# Ingress TradingView — LOT-05 (socle local)

Statut : **PRÊT À DÉPLOYER, NON DÉPLOYÉ.** La décision humaine **B-03**
(création du projet Cloudflare isolé) est en attente : tout est développé et
testé **en local avec des fakes** — aucun appel réseau, aucune ressource
Cloudflare créée, aucune facturation.

Références : `docs/09-adr/005-tradingview-ingress.md`,
`docs/04-integrations/TRADINGVIEW.md`, `docs/04-integrations/TRADINGVIEW_EXPLOITABLE_FIELDS.md`,
`docs/08-runbooks/TRADINGVIEW_SETUP.md`, `docs/06-quality/DATA_LATENCY_BUDGETS.md` (HP-02),
`contracts/json-schema/tradingview-alert-v1.schema.json`.

## Architecture

```text
TradingView (Pine, barre confirmée)
   └─ POST JSON ≤ 16 Ko sur /hook/<capacité secrète>
        └─ Worker Cloudflare (worker/src/worker.js)
             POST only · JSON only · capacité comparée en temps constant ·
             allowlist IP CF (env) · fenêtre sent_at ±X s · dédup alert_id+nonce (KV) ·
             rate limit IP (KV) · 202 UNIQUEMENT après queue.send()
                  └─ Cloudflare Queue (+ DLQ au déploiement)
                       └─ pull HTTP sortant local (aucun port entrant)
                            └─ vertex_ingress_tv (Python)
                                 schema.py   : revalidation stricte du contrat v1
                                 registry.py : alertes autorisées (rejet auditable)
                                 orchestrator.py :
                                   RECEIVED → PERSISTED → WAITING_FOR_IBKR
                                            → REVALIDATED | BLOCKED | EXPIRED
```

Invariants : ack local **uniquement après persistance confirmée** ; 100 rejeux
= 1 signal (clé `event_id = alert_id + ":" + nonce`) ; revalidation exigeant
une quote IBKR `observed_at >= received_at` **et** epoch de connexion courant,
sinon `BLOCKED` (raison explicite) ; deadline HP-02 (10 s par défaut, injectée)
→ `EXPIRED`, qui est un état d'ingress terminal et **jamais un verdict** ;
l'alerte n'est **jamais une preuve de prix** (`price_context.authoritative =
false`) ; aucun calcul financier dans le Worker ni dans ce paquet.

## Tests (exécutés localement, fakes uniquement)

```bash
# Worker (Node 22, node:test, fakes queue/KV) — 50 tests
cd apps/ingress-tradingview/worker && node --test test/*.test.mjs

# Python (pytest, fakes queue/store/quotes/horloge) — 83 tests
PYTHONPATH=packages/python/vertex_core/src:apps/ingress-tradingview/src \
  python3 -m pytest apps/ingress-tradingview/tests -q -p no:cacheprovider --override-ini "addopts="
```

Couverts : alerte valide → 202 après enqueue ; invalide / oversize / GET /
mauvais secret / IP hors liste / hors fenêtre / dupliquée → 4xx sans enqueue ;
échec queue → 5xx (jamais 202, marqueur dédup non écrit) ; comparaison
constante testée fonctionnellement ; idempotence 100 rejeux ; désordre ;
crash avant persistance → message non acké ; quote antérieure / epoch ancien →
`BLOCKED` ; deadline → `EXPIRED` ; alerte forgée/vieille/future/oversize et
version de registre inattendue → rejet auditable.

## Déploiement futur (après décision humaine B-03 uniquement)

1. Créer un compte/projet Cloudflare **isolé** (runbook `TRADINGVIEW_SETUP.md`).
2. `wrangler queues create vertex-tv-alerts` et `wrangler queues create
   vertex-tv-alerts-dlq` ; configurer le **consommateur pull HTTP** avec DLQ et
   politique de retry (https://developers.cloudflare.com/queues/configuration/pull-consumers/).
3. `wrangler kv namespace create VERTEX_TV_INGRESS` puis reporter l'`id` dans
   `worker/wrangler.toml` (`INGRESS_KV`).
4. Secrets **uniquement** par `wrangler secret put ROUTE_CAPABILITY`
   (>= 32 caractères aléatoires). **Jamais** de secret dans un fichier, dans
   Git, dans un log ou dans un corps d'alerte.
5. Renseigner `TV_ALLOWED_IPS` dans `[vars]` après **revérification le jour
   même** de la liste officielle TradingView
   (https://www.tradingview.com/support/solutions/43000529348-how-to-configure-webhook-alerts/).
   Le Worker refuse tout (fail-closed) si la liste est absente ou invalide.
6. `wrangler deploy` puis test de bout en bout avec un payload synthétique.

## Limites Free tier (vérifiées le 2026-08-28/29 — à revérifier au déploiement)

- **Queues** : ~10 000 opérations/jour et 24 h de rétention sur Free
  (runbook, https://developers.cloudflare.com/queues/platform/pricing/).
  Une opération = write + read + ack : dimensionner le volume d'alertes en
  conséquence (alerte de budget exigée par LOT-05 avant mise en service).
- **Workers** : 100 000 requêtes/jour, CPU borné par requête sur Free.
- **KV** : ~100 000 lectures/jour et **~1 000 écritures/jour** sur Free. Le
  rate limiter écrit ~1 clé par requête admise : un flood soutenu épuise le
  quota d'écritures — le limiteur est « best effort » (KV est de plus
  éventuellement cohérent) ; la défense principale reste capacité secrète +
  allowlist IP + validation stricte. À réévaluer au déploiement.
- TradingView annule un webhook au-delà de ~3 s : le Worker ne fait que
  valider + enqueue (budget HP-02 : p95 100 ms).

Aucune montée d'offre ni facturation sans validation humaine explicite.

## Checklist de mise en service

Référence : `docs/08-runbooks/TRADINGVIEW_SETUP.md`.

- [ ] Décision B-03 approuvée (projet Cloudflare isolé, Free tier suffisant).
- [ ] 2FA TradingView actif ; watchlist Vertex `EXCHANGE:TICKER` prête.
- [ ] Limites Free (Queues/Workers/KV) revérifiées le jour même + estimation
      de volume comparée (LOT-05, livrable 13).
- [ ] Queue + DLQ + consommateur pull créés ; KV créé ; `wrangler.toml` complété.
- [ ] `ROUTE_CAPABILITY` généré et posé par `wrangler secret put` (jamais en fichier).
- [ ] `TV_ALLOWED_IPS` renseigné depuis la liste officielle du jour.
- [ ] Scripts Pine compilés sur TradingView (pack `tradingview/`,
      **NON TESTÉS EN PLATEFORME** jusqu'à cette étape) ; golden payloads
      validés contre le JSON Schema.
- [ ] Alertes créées avec message JSON v1 + webhook ; entrées correspondantes
      ajoutées au registre local (`alert_id` + `script_version`).
- [ ] Test de bout en bout synthétique : 202 après enqueue, rejeu → 409,
      pull local → persistance idempotente → revalidation IBKR.
- [ ] Contrôle Webhook Status / Alert Log TradingView documenté (une absence
      d'alerte n'est pas une absence d'événement).

## Écarts documentés (socle local)

1. **Nonce hors schéma v1** : le JSON Schema v1 n'a pas de champ `nonce` de
   premier niveau et interdit les champs additionnels. Le nonce voyage donc
   dans `values.nonce` (map autorisée par le schéma) et son exigence est une
   **politique d'ingress** (plus stricte que le schéma, jamais plus laxiste).
   Une promotion en champ de premier niveau relèverait d'un schéma v2
   (contrat hors périmètre de ce lot).
2. **Non couvert par ce socle** (livrables LOT-05 restants, hors périmètre de
   cette étape) : déploiement réel (B-03), DLQ et runbook opérationnel,
   persistance PostgreSQL réelle derrière l'interface `SignalStore`,
   assistant d'import TXT/CSV, tableau de santé, estimation chiffrée du
   volume d'opérations.
3. **Rate limit KV « best effort »** : compteur non atomique, cohérence
   éventuelle, quota d'écritures Free faible — documenté ci-dessus.
4. **`received_at`** : stampé par le Worker dans l'enveloppe de queue ; le
   côté local le revalide (UTC aware obligatoire) et l'utilise comme ancre de
   la fenêtre anti-rejeu et de la deadline HP-02 — un drain tardif route les
   messages vers `EXPIRED` sans les requalifier.
5. **Scripts Pine non exécutables ici** : marqués `NON TESTÉS EN PLATEFORME —
   validation au déploiement humain` (compilation TradingView en checklist).
