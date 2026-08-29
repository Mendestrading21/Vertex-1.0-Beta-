/**
 * GÉNÉRÉ — NE PAS MODIFIER À LA MAIN.
 * Source : apps/api/openapi.json (contrat OpenAPI de l'API Vertex One).
 * Régénération : pnpm gen:api (openapi-typescript, devDependency épinglée).
 */
export interface paths {
    "/api/v1/advice/preview": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Evaluate gate inputs through the single AdviceEngine
         * @description Return the canonical ``AdviceResult`` for certified gate inputs.
         *
         *     Pass-through only: the route validates the wire payload and hands it to
         *     the single ``AdviceEngine``. Decimals serialize as strings and datetimes
         *     as ISO-8601 UTC. The result is analytical — the human decides outside
         *     Vertex.
         */
        post: operations["post_advice_preview"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/ai/explain": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Deterministic template explanation of one persisted snapshot
         * @description Explain ONE persisted snapshot through the DETERMINISTIC template.
         *
         *     Pure presentation of already-certified data: no network, no model, no
         *     financial computation, no clock beyond the snapshot's own ``as_of``.
         *     Every claim cites evidence really present in the snapshot (validated
         *     fail-closed); the answer is labeled ``DETERMINISTIC_TEMPLATE`` and its
         *     limitations always carry the B-05 notice. An absent snapshot is a clean
         *     404 — never an invented explanation.
         */
        post: operations["post_ai_explain"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/ai/status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * AI provider state: DISABLED pending human decision B-05
         * @description Report the honest AI state: no provider, deterministic template only.
         */
        get: operations["get_ai_status"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/analysis/{instrument}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Last published analysis dossier for one instrument (or honest empty state)
         * @description Serve the LAST ``analysis/{instrument}`` snapshot exactly as persisted.
         *
         *     The API relays the worker's published dossier — the canonical
         *     ``AdviceResult`` of the single ``AdviceEngine`` with its ten gates and
         *     reason codes, the validated OHLCV bars, the fusion evidence rail and the
         *     ``THEORETICAL`` scenario block (or its typed absence reason) — and
         *     computes nothing. With no snapshot ever published for this instrument
         *     the answer is a 200 with ``state = "empty"``: absent stays absent,
         *     nothing is invented.
         */
        get: operations["get_analysis"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/login/options": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Start a passkey authentication ceremony
         * @description Issue authentication options restricted to the registered passkeys.
         */
        post: operations["post_auth_login_options"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/login/verify": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Finish a passkey authentication ceremony and open a session
         * @description Verify the assertion, enforce the sign counter, issue the session.
         */
        post: operations["post_auth_login_verify"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/logout": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Revoke the current session and clear its cookies
         * @description Revoke the presented session server-side (requires session + CSRF).
         */
        post: operations["post_auth_logout"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/register/options": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Start a passkey registration ceremony
         * @description Issue registration options. Free only for the very first credential.
         */
        post: operations["post_auth_register_options"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/register/verify": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Finish a passkey registration ceremony
         * @description Verify the attestation response and store the credential.
         */
        post: operations["post_auth_register_verify"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/calendar": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Last published calendar snapshot (or honest empty state)
         * @description Serve the LAST ``calendar/global`` snapshot exactly as persisted.
         *
         *     The API relays the worker's published agenda — importance from the
         *     versioned rule, distinct ESTIMATED/CONFIRMED labels, revisions with
         *     their preserved previous values, conserved exchange timezones and the
         *     position/thesis event context — and computes nothing. The optional
         *     ``from``/``to`` query window (both bounds, aware datetimes, at most 90
         *     days) SELECTS events without altering any. With no snapshot ever
         *     published the answer is a 200 with ``state = "empty"``.
         */
        get: operations["get_calendar"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/events/stream": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Signal-only SSE: snapshot head version changes and pings
         * @description Stream head-version change signals (database polling, coalesced).
         */
        get: operations["get_events_stream"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/follow-up/queue": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Last published review queue snapshot (or honest empty state)
         * @description Serve the LAST ``review_queue/global`` snapshot exactly as persisted.
         *
         *     The API relays the worker's published content — projected thesis states,
         *     the documented lexicographic due ordering, urgency flags and reasons, the
         *     per-ticker information clusters with provenance, and the two SEPARATE
         *     population labels — and computes nothing. With no snapshot ever published
         *     the answer is a 200 with ``state = "empty"``: absent stays absent,
         *     nothing is invented.
         */
        get: operations["get_follow_up_queue"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/health": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Liveness probe
         * @description Report process liveness and the engine version. No sensitive data.
         */
        get: operations["get_health"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/markets/overview": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Last published markets overview snapshot (or honest empty state)
         * @description Serve the LAST ``markets_overview/global`` snapshot exactly as persisted.
         *
         *     The API relays the worker's published content — population (``SYNTHETIC``
         *     shown as-is), sectors/tickers with their server-computed returns and
         *     weights, breadth, coverage account and the deterministic conclusion — and
         *     computes nothing. With no snapshot ever published the answer is a 200
         *     with ``state = "empty"``: absent stays absent, nothing is invented.
         */
        get: operations["get_markets_overview"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/opportunities": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Last published opportunities snapshot (or honest empty state)
         * @description Serve the LAST ``opportunities/global`` snapshot exactly as persisted.
         *
         *     The API relays the worker's published candidates — the single
         *     ``AdviceEngine``'s statuses under the manifest profile (id + version),
         *     the documented lexicographic ordering, the honest evidence-presence
         *     checks and the exclusion-reason distribution — and computes nothing. A
         *     relay guard refuses a snapshot carrying a closed candidate in the
         *     qualified group. With no snapshot ever published the answer is a 200
         *     with ``state = "empty"``.
         */
        get: operations["get_opportunities"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/options/{underlying}/chain": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Last published option chain for one underlying (or honest empty state)
         * @description Serve the LAST ``option_chain/{underlying}`` snapshot exactly as persisted.
         *
         *     The API relays the worker's published content — per-(expiration,
         *     trading_class) groups with complete contract identities, verbatim quotes
         *     and their quality, the worker's Vertex IV/Greeks (``THEORETICAL``, with
         *     their ``CalculationRecord`` lineage) or their typed refusal reasons, the
         *     coverage account and the displayed row budget — and computes nothing.
         *     With no snapshot ever published for this underlying the answer is a 200
         *     with ``state = "empty"``: absent stays absent, nothing is invented.
         */
        get: operations["get_option_chain"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/performance/{portfolio_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Last published performance snapshot (or honest empty state)
         * @description Serve the LAST ``performance/{portfolio_id}`` snapshot as persisted.
         *
         *     The API relays the worker's published content — daily valuation series,
         *     explicit gross/net metrics with their ``CalculationRecord`` lineage,
         *     honest INSUFFICIENT_DATA / INVALID gate outcomes, monthly heatmap,
         *     coverage and the ``SYNTHETIC_MARKS_REAL_LEDGER`` population shown as-is —
         *     and computes nothing. With no snapshot ever published the answer is a
         *     200 with ``state = "empty"``: absent stays absent, nothing is invented.
         */
        get: operations["get_performance"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/performance/{portfolio_id}/export": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Reproducible export: CSV points + JSON manifest (methods, versions, hashes)
         * @description Export the daily points (CSV) and the audit manifest (JSON).
         *
         *     A PURE function of the persisted snapshot: two calls over the same
         *     snapshot version return byte-identical bodies; ``as_of`` is the
         *     snapshot's own instant (documented), never the request clock.
         */
        get: operations["export_performance"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/portfolio": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Manual journal, declared lots and last published valuation
         * @description Serve the manual ledger verbatim plus the LAST valuation snapshot.
         *
         *     The default portfolio ``main`` is created on first use (documented
         *     get-or-create). The valuation block relays the worker's snapshot exactly
         *     as persisted (``mark_population = "SYNTHETIC"`` shown as-is) or an honest
         *     empty state — the API computes no P&L, mark, weight or total.
         */
        get: operations["get_portfolio"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/portfolio/export": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * CSV export of the manual ledger (version stamp, ledger only)
         * @description Export the journal as CSV. Nothing but the ledger leaves the server.
         */
        get: operations["export_portfolio"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/portfolio/import/confirm": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Record the previewed rows (validation replayed, hash verified)
         * @description Record ONLY rows that re-pass the full validation with intact hashes.
         *
         *     The confirm never trusts the echo: each row's fields are re-validated
         *     exactly like at preview time and its integrity hash is recomputed; any
         *     divergence rejects the WHOLE request before any write. Accepted rows are
         *     recorded with source ``IMPORT_CONFIRMED`` and one revaluation is
         *     enqueued in the same transaction.
         */
        post: operations["confirm_portfolio_import"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/portfolio/import/preview": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Typed CSV preview: rows, per-row errors, duplicates — NO write
         * @description Validate a CSV import WITHOUT writing anything.
         *
         *     Every data row becomes either a typed, hash-stamped echo (to be sent
         *     back verbatim to the confirm endpoint) or a per-row error list. Valid
         *     rows matching already-recorded facts are flagged as potential duplicates
         *     — information for the user, never a silent drop.
         */
        post: operations["preview_portfolio_import"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/portfolio/transactions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Record one past transaction already executed outside Vertex
         * @description Append one accounting-journal fact and enqueue the revaluation.
         *
         *     The ledger write and the ``portfolio.valuation.refresh`` outbox message
         *     commit in the SAME transaction (outbox atomicity). This endpoint records
         *     what already happened outside Vertex — it never transmits anything to a
         *     broker and no such capability exists.
         */
        post: operations["record_transaction"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/portfolio/transactions/{transaction_id}/compensate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Correct one recorded fact by appending its compensating row
         * @description Append the compensating row of one recorded fact (never an edit).
         *
         *     The original row stays untouched forever; the compensating row negates
         *     amount, fees and quantity and carries the mandatory reason note. A second
         *     compensation of the same row is a clean 409 conflict.
         */
        post: operations["compensate_transaction"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/simulations/preview": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * THEORETICAL preview of one declared structure (no persistence)
         * @description Run one THEORETICAL simulation preview through vertex_core.
         *
         *     Orchestration only: the mandatory ``defined_risk_check``, the exact
         *     ``payoff_at_expiry``, the authority-certified breakevens and the bounded
         *     ``scenario_grid`` all run inside ``vertex_core.calculations.options`` on
         *     a worker thread (``run_in_threadpool`` — the event loop never computes).
         *     Nothing is persisted; nothing here is, or ever becomes, an order.
         */
        post: operations["post_simulations_preview"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/system/capabilities": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Declared capabilities crossed with really-probed statuses, plus health
         * @description Cross the FULL declared manifest with the latest persisted probes.
         *
         *     Every manifest entry is present (``total`` equals the manifest size); a
         *     capability never probed answers ``ERROR`` with reason ``NEVER_TESTED``.
         *     Health blocks report the database (``SELECT 1``), both snapshot heads,
         *     and the worker through the explicitly labeled ``heartbeat_proxy``.
         */
        get: operations["get_system_capabilities"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/system/engine": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Engine and contract versions
         * @description Report the engine, contract and per-gate versions. Never a secret.
         */
        get: operations["get_system_engine"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/theses": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Append one user-written thesis (statement + mandatory falsifier)
         * @description Record one thesis and enqueue the review-queue refresh, one transaction.
         *
         *     Revisions are append-only and the review-queue refresh commits WITH the
         *     write (outbox atomicity). Replaying the same ``idempotency_key`` answers
         *     200 with ``created=false`` and writes nothing — never a duplicate.
         */
        post: operations["create_thesis"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/theses/{thesis_id}/revisions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Append one review-lifecycle revision (append-only history)
         * @description Append one revision and enqueue the review-queue refresh, one transaction.
         *
         *     History is append-only: nothing edits or deletes an earlier revision;
         *     the projected status is recomputed by the repository, never stored.
         */
        post: operations["record_thesis_revision"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/today/attention": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Last published attention snapshot (or honest empty state)
         * @description Serve the LAST ``attention/global`` snapshot exactly as persisted.
         *
         *     The API relays the worker's published content — population (``SYNTHETIC``
         *     shown as-is), coverage, items with provenance — and computes nothing.
         *     With no snapshot ever published the answer is a 200 with ``state =
         *     "empty"``: absent stays absent, nothing is invented.
         */
        get: operations["get_today_attention"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /**
         * AdvicePreviewRequest
         * @description Complete certified input set for one advice preview.
         *
         *     Field-for-field the engine's own ``AdviceInputs`` (subclass — nothing is
         *     redefined), with the gate 6 mapping typed for the wire. A field left
         *     absent stays honestly absent and blocks its gate with ``UNEVALUABLE``.
         */
        AdvicePreviewRequest: {
            /**
             * As Of
             * Format: date-time
             */
            as_of: string;
            calculations?: components["schemas"]["CalculationStatusesInput"];
            constraints?: components["schemas"]["ConstraintsInput"];
            contradictions?: components["schemas"]["ContradictionsInput"];
            direction: components["schemas"]["Direction"];
            entitlements?: components["schemas"]["EntitlementsInput"];
            /**
             * Evidence Ids
             * @default []
             */
            evidence_ids: string[];
            /**
             * Explanation Facts
             * @default []
             */
            explanation_facts: string[];
            /** Horizon */
            horizon: string;
            /** Input Snapshot Id */
            input_snapshot_id: string;
            instrument?: components["schemas"]["InstrumentResolutionInput"];
            /** Instrument Id */
            instrument_id: string;
            /**
             * Limitations
             * @default []
             */
            limitations: string[];
            liquidity?: components["schemas"]["LiquidityInput"];
            portfolio_risk?: components["schemas"]["PortfolioRiskInput"];
            probability?: components["schemas"]["ProbabilityInput"];
            /**
             * Probability Evidence
             * @default null
             */
            probability_evidence: {
                [key: string]: unknown;
            } | null;
            /** Risk Summary */
            risk_summary: string;
            /**
             * Scenario Ids
             * @default []
             */
            scenario_ids: string[];
            session_event?: components["schemas"]["SessionEventInput"];
            snapshot?: components["schemas"]["SnapshotInput"];
            /**
             * Supersedes
             * @default null
             */
            supersedes: string | null;
            /**
             * Valid Until
             * Format: date-time
             */
            valid_until: string;
        };
        /**
         * AdviceResult
         * @description The single authoritative analytical verdict for one instrument.
         *
         *     Carries status, direction, gates, evidence, limitations and explanation
         *     facts. ``probability_evidence`` stays ``None`` unless calibrated evidence
         *     genuinely exists — absence is never converted into a fabricated figure.
         *     Contains no transactional field of any kind.
         */
        AdviceResult: {
            /** Advice Id */
            advice_id: string;
            /**
             * As Of
             * Format: date-time
             */
            as_of: string;
            direction: components["schemas"]["Direction"];
            /** Engine Version */
            engine_version: string;
            /**
             * Evidence Ids
             * @default []
             */
            evidence_ids: string[];
            /**
             * Explanation Facts
             * @default []
             */
            explanation_facts: string[];
            /** Gates */
            gates: components["schemas"]["GateResult"][];
            /** Horizon */
            horizon: string;
            /** Input Snapshot Id */
            input_snapshot_id: string;
            /** Instrument Id */
            instrument_id: string;
            /**
             * Limitations
             * @default []
             */
            limitations: string[];
            /** Probability Evidence */
            probability_evidence?: {
                [key: string]: unknown;
            } | null;
            /** Risk Summary */
            risk_summary: string;
            /**
             * Scenario Ids
             * @default []
             */
            scenario_ids: string[];
            status: components["schemas"]["AdviceStatus"];
            /** Supersedes */
            supersedes?: string | null;
            /**
             * Valid Until
             * Format: date-time
             */
            valid_until: string;
        };
        /**
         * AdviceStatus
         * @description Canonical verdict status of an ``AdviceResult`` (ADR-014).
         *
         *     ``BLOCKED`` (a gate closed), ``INSUFFICIENT_DATA`` (required inputs
         *     missing), ``OBSERVE`` (valid data, not enough for study), ``REVIEW``
         *     (worth analytical study), ``QUALIFIED`` (passes all gates). Distinct from
         *     :class:`Direction`; never a transactional instruction.
         * @enum {string}
         */
        AdviceStatus: "BLOCKED" | "INSUFFICIENT_DATA" | "OBSERVE" | "REVIEW" | "QUALIFIED";
        /**
         * AiAnswer
         * @description The structured deterministic answer (never presented as a model).
         *
         *     ``state = "ok"`` carries at least one grounded claim. ``state =
         *     "refused"`` is the STRUCTURED REFUSAL of an empty or unusable corpus:
         *     no claim, a readable ``refusal_reason`` and explicit missing data — it
         *     is never an empty explanation presented as complete.
         */
        AiAnswer: {
            /**
             * As Of
             * Format: date-time
             */
            as_of: string;
            /** Claims */
            claims: components["schemas"]["AiClaim"][];
            /** Content Hash */
            content_hash: string;
            /** Contradictions */
            contradictions: components["schemas"]["AiContradiction"][];
            /** Evidence Catalog */
            evidence_catalog: components["schemas"]["AiEvidenceCatalogEntry"][];
            /** External Excerpts */
            external_excerpts: components["schemas"]["AiExternalExcerpt"][];
            /** Limitations */
            limitations: string[];
            /**
             * Locale
             * @constant
             */
            locale: "fr";
            /** Missing Data */
            missing_data: string[];
            /**
             * Provider
             * @constant
             */
            provider: "DETERMINISTIC_TEMPLATE";
            /** Refusal Reason */
            refusal_reason: string | null;
            /** Snapshot Version */
            snapshot_version: number;
            /**
             * State
             * @enum {string}
             */
            state: "ok" | "refused";
            subject: components["schemas"]["AiSubject"];
            /**
             * Template Version
             * @constant
             */
            template_version: "vertex.ai-deterministic-template/1.0";
        };
        /**
         * AiClaim
         * @description One factual sentence, grounded on evidence really present.
         *
         *     A claim text is built ONLY from Vertex-owned canonical values; untrusted
         *     external content never enters it.
         */
        AiClaim: {
            /** Evidence Refs */
            evidence_refs: string[];
            /**
             * Kind
             * @constant
             */
            kind: "FACT";
            /** Text */
            text: string;
        };
        /**
         * AiContradiction
         * @description One contradiction carried by the snapshot (e.g. a closed gate).
         */
        AiContradiction: {
            /** Code */
            code: string;
            /** Reference */
            reference: string | null;
            /** Text */
            text: string;
        };
        /**
         * AiEvidenceCatalogEntry
         * @description One resolvable evidence id of the source snapshot (server catalog).
         */
        AiEvidenceCatalogEntry: {
            /** Evidence Id */
            evidence_id: string;
            /** Evidence Type */
            evidence_type: string;
            /** Path */
            path: string;
        };
        /**
         * AiExplainRequest
         * @description Wire contract of ``POST /api/v1/ai/explain``.
         */
        AiExplainRequest: {
            /**
             * Locale
             * @constant
             */
            locale: "fr";
            subject: components["schemas"]["AiSubject"];
        };
        /**
         * AiExternalExcerpt
         * @description One excerpt of UNTRUSTED external content — never a Vertex fact.
         *
         *     Carried in its own channel, typed ``EXTERNAL_UNVERIFIED``, escaped and
         *     truncated. It is displayed as quoted source material, never as a claim.
         */
        AiExternalExcerpt: {
            /** Evidence Ref */
            evidence_ref: string;
            /** Excerpt */
            excerpt: string;
            /**
             * Label
             * @constant
             */
            label: "EXTERNAL_UNVERIFIED";
            /** Truncated */
            truncated: boolean;
        };
        /**
         * AiStatusResponse
         * @description State of the AI provider: disabled until human decision B-05.
         */
        AiStatusResponse: {
            /**
             * Deterministic Template Available
             * @constant
             */
            deterministic_template_available: true;
            /**
             * Provider
             * @constant
             */
            provider: "DISABLED";
            /**
             * Reason
             * @constant
             */
            reason: "B-05_HUMAN_DECISION_PENDING";
        };
        /**
         * AiSubject
         * @description What the template explains: one persisted snapshot.
         */
        AiSubject: {
            /** Key */
            key: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "analysis" | "portfolio_valuation" | "performance";
        };
        /**
         * AnalysisResponse
         * @description The last ``analysis/{instrument}`` snapshot — or an honest empty state.
         *
         *     ``state = "empty"`` means NO dossier was ever published for this
         *     instrument: every snapshot-derived field is ``None`` (never invented)
         *     and ``reason`` says why. ``state = "ok"`` relays the persisted content
         *     verbatim:
         *
         *     - ``advice`` is the canonical ``AdviceResult`` produced by THE single
         *       ``AdviceEngine`` — status, direction, the ten gates with their reason
         *       codes, limitations — exactly as published; the API neither recomputes
         *       nor softens it;
         *     - ``bars`` carries the validated synthetic OHLCV series (decimal
         *       strings) with its per-bar discard account;
         *     - ``evidence`` is the fusion-cluster rail of the instrument;
         *     - ``scenarios`` is either the ``THEORETICAL`` scenario grid with its
         *       ``CalculationRecord`` lineage or an honest ``ABSENT`` block with its
         *       typed reason.
         */
        AnalysisResponse: {
            /** Advice */
            advice: {
                [key: string]: unknown;
            } | null;
            /** As Of */
            as_of: string | null;
            /** Bars */
            bars: {
                [key: string]: unknown;
            } | null;
            /** Coverage */
            coverage: {
                [key: string]: unknown;
            } | null;
            /** Engine Version */
            engine_version: string | null;
            /** Evidence */
            evidence: {
                [key: string]: unknown;
            } | null;
            /** Instrument */
            instrument: string;
            /** Population */
            population: string | null;
            /** Reason */
            reason: string | null;
            /** Scenarios */
            scenarios: {
                [key: string]: unknown;
            } | null;
            /** Snapshot Version */
            snapshot_version: number | null;
            /**
             * State
             * @enum {string}
             */
            state: "ok" | "empty";
        };
        /**
         * AssetClass
         * @description Canonical asset class of an identified instrument.
         * @enum {string}
         */
        AssetClass: "STOCK" | "ETF" | "INDEX" | "OPTION";
        /**
         * AttentionItem
         * @description One published attention item, relayed from the worker snapshot.
         *
         *     ``synthetic`` and the ``population`` label of the response are shown
         *     exactly as published — synthetic data never blends into a real
         *     presentation. ``provenance`` is the cluster provenance block verbatim
         *     (cluster id, member event ids, sources, rights, timestamps,
         *     instrument_ref); the API adds nothing and recomputes nothing.
         */
        AttentionItem: {
            /** Id */
            id: string;
            /** Provenance */
            provenance: {
                [key: string]: unknown;
            };
            /** Relevance Reasons */
            relevance_reasons: string[];
            /** Rights */
            rights: string[];
            /** Sources */
            sources: string[];
            /** Synthetic */
            synthetic: boolean;
            /** Title */
            title: string;
        };
        /**
         * AttentionSnapshotResponse
         * @description The last ``attention/global`` snapshot — or an honest empty state.
         *
         *     ``state = "empty"`` means NO snapshot was ever published: every
         *     snapshot-derived field is ``None`` (never zero, never invented) and
         *     ``reason`` says why. ``state = "ok"`` carries the persisted snapshot
         *     version, ``as_of``, ``population`` (``SYNTHETIC`` shown as-is),
         *     the full coverage block and the published items.
         */
        AttentionSnapshotResponse: {
            /** As Of */
            as_of: string | null;
            /** Coverage */
            coverage: {
                [key: string]: unknown;
            } | null;
            /** Items */
            items: components["schemas"]["AttentionItem"][];
            /** Population */
            population: string | null;
            /** Reason */
            reason: string | null;
            /** Rejected Count */
            rejected_count: number | null;
            /** Snapshot Version */
            snapshot_version: number | null;
            /**
             * State
             * @enum {string}
             */
            state: "ok" | "empty";
        };
        /**
         * CalculationStatus
         * @description Outcome of a deterministic calculation.
         *
         *     ``NOT_IMPLEMENTED`` names an absent capability honestly; it is never
         *     presented as a pending automation.
         * @enum {string}
         */
        CalculationStatus: "OK" | "INVALID" | "NOT_IMPLEMENTED";
        /**
         * CalculationStatusesInput
         * @description Wire form of the gate 6 facts.
         *
         *     Narrows the engine's ``Any``-valued mapping to ``CalculationStatus``
         *     members so JSON input (``{"iv_surface": "OK"}``) reaches the gate as
         *     canonical enum values. An absent mapping stays ``None`` (fail-closed at
         *     the gate), never an empty default.
         */
        CalculationStatusesInput: {
            /**
             * Calculation Statuses
             * @default null
             */
            calculation_statuses: {
                [key: string]: components["schemas"]["CalculationStatus"];
            } | null;
        };
        /**
         * CalendarResponse
         * @description The last published calendar snapshot — or an honest empty state.
         *
         *     ``state = "ok"`` relays the persisted agenda VERBATIM (importance from
         *     the versioned rule, distinct ESTIMATED/CONFIRMED labels, revisions and
         *     previous values, freshness, exchange timezones); the API invents no event
         *     and recomputes no importance. ``state = "empty"`` means nothing to show
         *     (never published, or nothing observed), ``state = "not_entitled"`` that
         *     the considered records were rejected for missing rights,
         *     ``state = "rejected"`` that they were all invalid, ``state = "stale"``
         *     that the agenda is no longer current — the worker published ``STALE``,
         *     the snapshot is past :data:`CALENDAR_MAX_AGE`, or every served event has
         *     passed its published ``stale_after`` at the relay clock —,
         *     ``state = "empty_window"`` that the REQUESTED window selects none of the
         *     published events, and ``state = "degraded"`` that the snapshot predates
         *     a field of the current contract and is therefore incomplete. Every
         *     non-ok state carries its ``reason``: an empty agenda never passes for a
         *     success, and a relayed ``fresh`` flag is recomputed against the server
         *     clock — never a frozen boolean.
         */
        CalendarResponse: {
            /** Agenda */
            agenda: {
                [key: string]: unknown;
            }[];
            /** As Of */
            as_of: string | null;
            /** Categories */
            categories: {
                [key: string]: unknown;
            } | null;
            /** Coverage */
            coverage: {
                [key: string]: unknown;
            } | null;
            /** Importance Rule */
            importance_rule: {
                [key: string]: unknown;
            } | null;
            /** Population */
            population: string | null;
            /** Reason */
            reason: string | null;
            /** Snapshot Version */
            snapshot_version: number | null;
            /**
             * State
             * @enum {string}
             */
            state: "ok" | "empty" | "not_entitled" | "rejected" | "stale" | "empty_window" | "degraded";
            /** Statuses */
            statuses: {
                [key: string]: unknown;
            } | null;
            window: components["schemas"]["CalendarWindow"];
        };
        /**
         * CalendarWindow
         * @description Echo of the applied (or absent) display window.
         *
         *     ``categories`` and ``statuses`` count the events REALLY displayed, so the
         *     counters never contradict the served list; the snapshot-wide totals stay
         *     published beside them in ``categories``/``statuses``/``coverage``.
         */
        CalendarWindow: {
            /** Applied */
            applied: boolean;
            /** Categories */
            categories: {
                [key: string]: unknown;
            };
            /** Events In Window */
            events_in_window: number;
            /** Events Total */
            events_total: number;
            /** From Utc */
            from_utc: string | null;
            /** Max Days */
            max_days: number;
            /** Statuses */
            statuses: {
                [key: string]: unknown;
            };
            /** To Utc */
            to_utc: string | null;
        };
        /**
         * CapabilityStatusEntry
         * @description One declared capability crossed with the latest persisted probe.
         *
         *     A capability never probed is ``tested_status = ERROR`` with
         *     ``reason = "NEVER_TESTED"`` and ``tested_at = None`` — absence of a probe
         *     is never presented as availability.
         */
        CapabilityStatusEntry: {
            /** Capability Id */
            capability_id: string;
            /** Declared Mode */
            declared_mode: string;
            /** Description */
            description: string | null;
            /** Family */
            family: string;
            /** Reason */
            reason: string | null;
            /** Tested At */
            tested_at: string | null;
            tested_status: components["schemas"]["SourceCapabilityStatus"];
        };
        /**
         * CeremonyOptionsResponse
         * @description A pending ceremony: opaque flow id + the WebAuthn options JSON.
         */
        CeremonyOptionsResponse: {
            /** Flow Id */
            flow_id: string;
            /** Options */
            options: {
                [key: string]: unknown;
            };
        };
        /**
         * CompensateTransactionRequest
         * @description Correction by compensation: the mandatory reason of the new row.
         */
        CompensateTransactionRequest: {
            /** Note */
            note: string;
        };
        /**
         * CompensateTransactionResponse
         * @description Receipt of one compensating row (the original stays untouched).
         */
        CompensateTransactionResponse: {
            /** Compensates */
            compensates: number;
            /** Compensation Id */
            compensation_id: number;
            /** Refresh Enqueued */
            refresh_enqueued: boolean;
        };
        /**
         * ConstraintsInput
         * @description Facts for gate 10 (``user_constraints_versioned``).
         */
        ConstraintsInput: {
            /**
             * Constraints Current
             * @default null
             */
            constraints_current: boolean | null;
            /**
             * Constraints Version
             * @default null
             */
            constraints_version: string | null;
        };
        /**
         * ContradictionsInput
         * @description Facts for gate 9 (``critical_contradictions_resolved``).
         */
        ContradictionsInput: {
            /**
             * Explicit Contradiction Count
             * @default null
             */
            explicit_contradiction_count: number | null;
            /**
             * Unresolved Critical Count
             * @default null
             */
            unresolved_critical_count: number | null;
        };
        /**
         * CreateThesisRequest
         * @description One user-written thesis to append (statement + mandatory falsifier).
         *
         *     ``invalidation`` is REQUIRED and non-blank: what would prove the thesis
         *     wrong is part of the statement, never optional. ``idempotency_key`` is
         *     the CLIENT's replay token: the same key always answers with the same
         *     thesis, and writes at most once.
         */
        CreateThesisRequest: {
            /**
             * Horizon
             * @default null
             */
            horizon: string | null;
            /** Hypotheses */
            hypotheses: string;
            /** Idempotency Key */
            idempotency_key: string;
            /** @default null */
            instrument: components["schemas"]["ThesisInstrumentInput"] | null;
            /** Invalidation */
            invalidation: string;
            /**
             * Note
             * @default null
             */
            note: string | null;
            /**
             * Portfolio Id
             * @default null
             */
            portfolio_id: number | null;
            /**
             * Review Due At
             * @default null
             */
            review_due_at: string | null;
            /** Title */
            title: string;
        };
        /**
         * CreateThesisResponse
         * @description Receipt: ``created=false`` marks an idempotent replay (nothing written).
         */
        CreateThesisResponse: {
            /** Created */
            created: boolean;
            /** Refresh Enqueued */
            refresh_enqueued: boolean;
            /** Revision Id */
            revision_id: number;
            /** Thesis Id */
            thesis_id: number;
        };
        /**
         * CsvImportPreviewRequest
         * @description Raw CSV text to preview. Nothing is written by the preview.
         */
        CsvImportPreviewRequest: {
            /** Csv */
            csv: string;
        };
        /**
         * DbHealth
         * @description Result of the ``SELECT 1`` probe: ``ok`` or ``error``, nothing more.
         */
        DbHealth: {
            /**
             * Status
             * @enum {string}
             */
            status: "ok" | "error";
        };
        /**
         * Direction
         * @description Analytical directional reading attached to a verdict (ADR-014).
         * @enum {string}
         */
        Direction: "BULLISH" | "BEARISH" | "NEUTRAL" | "MIXED" | "UNKNOWN";
        /**
         * EngineInfoResponse
         * @description Engine and contract versions backing every verdict. Carries no secret.
         *
         *     ``contracts_version`` equals the ``ENGINE_VERSION`` stamp because the
         *     canonical contracts are versioned by the same identifier that is recorded
         *     in every calculation and advice contract (``vertex_core.version``).
         */
        EngineInfoResponse: {
            /** Contracts Version */
            contracts_version: string;
            /** Engine Version */
            engine_version: string;
            /** Gate Versions */
            gate_versions: {
                [key: string]: unknown;
            };
        };
        /**
         * EntitlementsInput
         * @description Facts for gate 2 (``entitlements_sufficient``).
         */
        EntitlementsInput: {
            /** @default null */
            capability_status: components["schemas"]["SourceCapabilityStatus"] | null;
        };
        /**
         * FollowUpQueueResponse
         * @description The last published review queue snapshot — or an honest empty state.
         *
         *     ``state = "ok"`` relays the persisted content VERBATIM (projected states,
         *     documented ordering, urgency flags, populations kept separate); the API
         *     recomputes nothing. ``state = "empty"`` means the worker never published
         *     the queue: nothing is invented, ``reason`` says why.
         */
        FollowUpQueueResponse: {
            /** As Of */
            as_of: string | null;
            /** Content */
            content: {
                [key: string]: unknown;
            } | null;
            /** Reason */
            reason: string | null;
            /** Snapshot Version */
            snapshot_version: number | null;
            /**
             * State
             * @enum {string}
             */
            state: "ok" | "empty";
        };
        /**
         * GateResult
         * @description Outcome of one versioned decision gate.
         *
         *     ``observed_values`` and ``thresholds`` carry the real evidence the gate
         *     saw; both are frozen at validation time. A gate that cannot be evaluated
         *     is ``BLOCK`` with ``reason_code = "UNEVALUABLE"`` (fail-closed).
         */
        GateResult: {
            /**
             * Evidence Ids
             * @default []
             */
            evidence_ids: string[];
            /** Gate Id */
            gate_id: string;
            /** Message */
            message: string;
            /** Observed Values */
            observed_values?: {
                [key: string]: unknown;
            };
            /** Reason Code */
            reason_code: string;
            status: components["schemas"]["GateStatus"];
            /** Thresholds */
            thresholds?: {
                [key: string]: unknown;
            };
            /** Version */
            version: string;
        };
        /**
         * GateStatus
         * @description Result of one decision gate: ``PASS``, ``DEGRADE`` or ``BLOCK``.
         *
         *     A gate that cannot be evaluated is ``BLOCK`` with
         *     ``reason_code = "UNEVALUABLE"`` (fail-closed); there is no ``UNKNOWN``
         *     gate state (ADR-014).
         * @enum {string}
         */
        GateStatus: "PASS" | "DEGRADE" | "BLOCK";
        /** HTTPValidationError */
        HTTPValidationError: {
            /** Detail */
            detail?: components["schemas"]["ValidationError"][];
        };
        /**
         * HealthResponse
         * @description Liveness payload: static status and engine version, nothing sensitive.
         */
        HealthResponse: {
            /** Engine Version */
            engine_version: string;
            /**
             * Status
             * @constant
             */
            status: "alive";
        };
        /**
         * IdentityStatus
         * @description Resolution state of an instrument identity. Collisions stay ``UNRESOLVED``.
         * @enum {string}
         */
        IdentityStatus: "RESOLVED" | "AMBIGUOUS" | "UNRESOLVED";
        /**
         * ImportConfirmRequest
         * @description The rows to record: the preview echo, unmodified, hash included.
         */
        ImportConfirmRequest: {
            /** Rows */
            rows: components["schemas"]["ImportRowEcho"][];
        };
        /**
         * ImportConfirmResponse
         * @description Receipt of one confirmed import (source ``IMPORT_CONFIRMED``).
         */
        ImportConfirmResponse: {
            /** Recorded Transaction Ids */
            recorded_transaction_ids: number[];
            /** Refresh Enqueued */
            refresh_enqueued: boolean;
            /**
             * Source
             * @constant
             */
            source: "IMPORT_CONFIRMED";
        };
        /**
         * ImportPreviewResponse
         * @description Typed preview of one CSV import — NO write happened.
         */
        ImportPreviewResponse: {
            /** Max Bytes */
            max_bytes: number;
            /** Max Rows */
            max_rows: number;
            /** Potential Duplicates */
            potential_duplicates: components["schemas"]["ImportRowDuplicate"][];
            /** Rows Invalid */
            rows_invalid: components["schemas"]["ImportRowError"][];
            /** Rows Total */
            rows_total: number;
            /** Rows Valid */
            rows_valid: components["schemas"]["ImportRowEcho"][];
        };
        /**
         * ImportRowDuplicate
         * @description One valid row that matches already-recorded ledger transactions.
         */
        ImportRowDuplicate: {
            /** Matching Transaction Ids */
            matching_transaction_ids: number[];
            /** Row Number */
            row_number: number;
        };
        /**
         * ImportRowEcho
         * @description One VALIDATED import row echoed with its integrity hash.
         *
         *     The confirm endpoint replays the validation on these fields and
         *     recomputes ``row_hash``; any divergence rejects the whole request.
         *     Optional fields are empty strings in the canonical hashed form.
         */
        ImportRowEcho: {
            /** Amount */
            amount: string;
            /** Currency */
            currency: string;
            /** Effective At */
            effective_at: string;
            /** Fees */
            fees: string;
            /** Kind */
            kind: string;
            /** Note */
            note: string;
            /** Price */
            price: string;
            /** Quantity */
            quantity: string;
            /** Row Hash */
            row_hash: string;
            /** Row Number */
            row_number: number;
            /** Ticker */
            ticker: string;
        };
        /**
         * ImportRowError
         * @description One rejected import row with its machine-readable error codes.
         */
        ImportRowError: {
            /** Errors */
            errors: string[];
            /** Row Number */
            row_number: number;
        };
        /**
         * InstrumentRefInput
         * @description Canonical instrument reference of a recorded position fact.
         *
         *     ``ticker`` only for now: the synthetic universe identifies instruments by
         *     plain ticker. Extending the identity (options, con_id, trading class) is a
         *     contract change, never an implicit field.
         */
        InstrumentRefInput: {
            /** Ticker */
            ticker: string;
        };
        /**
         * InstrumentResolutionInput
         * @description Facts for gate 1 (``instrument_resolved``).
         */
        InstrumentResolutionInput: {
            /** @default null */
            identity_status: components["schemas"]["IdentityStatus"] | null;
            /**
             * Resolved With Conid
             * @default null
             */
            resolved_with_conid: boolean | null;
        };
        /**
         * LedgerEventKind
         * @description Kind of one manually recorded ledger fact.
         *
         *     Every kind names a **past fact typed in by the user** after it happened
         *     outside Vertex (``docs/03-domain/PORTFOLIO_MANUAL.md``). None of these is
         *     an instruction, an order or a transmissible ticket.
         * @enum {string}
         */
        LedgerEventKind: "BUY_RECORDED" | "SELL_RECORDED" | "OPTION_OPEN" | "OPTION_CLOSE" | "DIVIDEND" | "INTEREST" | "FEE" | "TAX" | "DEPOSIT" | "WITHDRAWAL" | "FX_CONVERSION" | "CORPORATE_ACTION" | "ADJUSTMENT";
        /**
         * LedgerTransactionEntry
         * @description One journal row, verbatim (decimal strings, UTC instants).
         */
        LedgerTransactionEntry: {
            /** Amount */
            amount: string;
            /** Compensated By */
            compensated_by: number | null;
            /** Compensates */
            compensates: number | null;
            /** Currency */
            currency: string;
            /**
             * Effective At
             * Format: date-time
             */
            effective_at: string;
            /** Fees */
            fees: string;
            /** Id */
            id: number;
            /** Instrument */
            instrument: {
                [key: string]: unknown;
            } | null;
            /** Kind */
            kind: string;
            /** Note */
            note: string | null;
            /** Price */
            price: string | null;
            /** Quantity */
            quantity: string | null;
            /**
             * Recorded At
             * Format: date-time
             */
            recorded_at: string;
            /** Source */
            source: string;
        };
        /**
         * LiquidityInput
         * @description Facts for gate 5 (``minimum_liquidity``); the threshold is per asset class.
         */
        LiquidityInput: {
            /** @default null */
            asset_class: components["schemas"]["AssetClass"] | null;
            /**
             * Observation Delayed
             * @default null
             */
            observation_delayed: boolean | null;
            /**
             * Observed Liquidity
             * @default null
             */
            observed_liquidity: number | string | null;
            /**
             * Required Minimum
             * @default null
             */
            required_minimum: number | string | null;
        };
        /**
         * LoginVerifyRequest
         * @description Client answer to an authentication ceremony.
         */
        LoginVerifyRequest: {
            /** Credential */
            credential: {
                [key: string]: unknown;
            };
            /** Flow Id */
            flow_id: string;
        };
        /**
         * LoginVerifyResponse
         * @description Session established (tokens travel ONLY in cookies, never in the body).
         */
        LoginVerifyResponse: {
            /**
             * Authenticated
             * @constant
             */
            authenticated: true;
            /** Expires At */
            expires_at: string;
        };
        /**
         * LogoutResponse
         * @description Session revoked and cookies cleared.
         */
        LogoutResponse: {
            /**
             * Logged Out
             * @constant
             */
            logged_out: true;
        };
        /**
         * MarketsBreadth
         * @description Global breadth block — ``market.breadth`` result or an honest INVALID.
         *
         *     ``status = "INVALID"`` (coverage below the threshold gate) carries the
         *     typed reason and NO value — a breadth computed on a sliver of the
         *     universe is never presented. All percentages are server-rendered strings.
         */
        MarketsBreadth: {
            /** Above Count */
            above_count: number;
            /** Calculation */
            calculation: {
                [key: string]: unknown;
            } | null;
            /** Coverage Pct */
            coverage_pct: string;
            /** Coverage Threshold */
            coverage_threshold: string;
            /** Coverage Threshold Pct */
            coverage_threshold_pct: string;
            /** Covered Count */
            covered_count: number;
            /** Reason */
            reason: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "OK" | "INVALID";
            /** Universe Size */
            universe_size: number;
            /** Value */
            value: string | null;
            /** Value Pct */
            value_pct: string | null;
        };
        /**
         * MarketsCoverage
         * @description Expected / received / covered / discarded account of the universe.
         */
        MarketsCoverage: {
            /** Covered */
            covered: number;
            /** Discarded */
            discarded: number;
            /** Discarded Tickers */
            discarded_tickers: components["schemas"]["MarketsDiscardedTicker"][];
            /** Expected */
            expected: number;
            /** Lookback Seconds */
            lookback_seconds: number;
            /** Observations Considered */
            observations_considered: number;
            /** Received */
            received: number;
            /** Rejected Records */
            rejected_records: components["schemas"]["MarketsRejectedRecord"][];
        };
        /**
         * MarketsDiscardedTicker
         * @description One universe ticker excluded from the overview, with its reason.
         *
         *     ``missing_close``: fewer than the two required closes in the window —
         *     the ticker is counted here, never interpolated.
         */
        MarketsDiscardedTicker: {
            /** Reason */
            reason: string;
            /** Ticker */
            ticker: string;
        };
        /**
         * MarketsOverviewResponse
         * @description The last ``markets_overview/global`` snapshot — or an honest empty state.
         *
         *     ``state = "empty"`` means NO snapshot was ever published: every
         *     snapshot-derived field is ``None`` (never zero, never invented) and
         *     ``reason`` says why. ``state = "ok"`` relays the persisted content
         *     verbatim: population (``SYNTHETIC`` shown as-is), the worker's own
         *     ``data_state`` (``ok``/``partial``/``stale``), the deterministic French
         *     conclusion sentence, sectors/tickers, breadth and the coverage account.
         */
        MarketsOverviewResponse: {
            /** As Of */
            as_of: string | null;
            breadth: components["schemas"]["MarketsBreadth"] | null;
            /** Conclusion */
            conclusion: string | null;
            coverage: components["schemas"]["MarketsCoverage"] | null;
            /** Data State */
            data_state: ("ok" | "partial" | "stale") | null;
            /** Display Unit */
            display_unit: string | null;
            /** Engine Version */
            engine_version: string | null;
            /** Population */
            population: string | null;
            /** Reason */
            reason: string | null;
            /** Sectors */
            sectors: components["schemas"]["MarketsSector"][];
            /** Snapshot Version */
            snapshot_version: number | null;
            /**
             * State
             * @enum {string}
             */
            state: "ok" | "empty";
            /** Unit */
            unit: string | null;
        };
        /**
         * MarketsRejectedRecord
         * @description One observation refused by the deny-by-default gates, with its reason.
         */
        MarketsRejectedRecord: {
            /** Event Id */
            event_id: string;
            /** Reason */
            reason: string;
        };
        /**
         * MarketsSector
         * @description One declared sector with its covered tickers (possibly none).
         */
        MarketsSector: {
            /** Covered Count */
            covered_count: number;
            /** Declared Count */
            declared_count: number;
            /** Label */
            label: string;
            /** Sector */
            sector: string;
            /** Tickers */
            tickers: components["schemas"]["MarketsTicker"][];
        };
        /**
         * MarketsTicker
         * @description One covered ticker, relayed from the worker snapshot verbatim.
         *
         *     Every price and ratio is a DECIMAL STRING computed server-side (the last
         *     close verbatim from the observation payload, the 1-day return from
         *     ``market.simple_return``, weights and display percentages rendered by the
         *     worker). The API and the client format — they never recompute.
         *     ``calculation`` is the preserved ``CalculationRecord`` lineage subset
         *     (engine_version, input_hash, result_hash, method, status).
         */
        MarketsTicker: {
            /** Calculation */
            calculation: {
                [key: string]: unknown;
            };
            /** Currency */
            currency: string | null;
            /** Last Close */
            last_close: string;
            /** Previous Close */
            previous_close: string;
            /** Previous Trading Day */
            previous_trading_day: string;
            /** Quality */
            quality: string;
            /** Return 1D */
            return_1d: string;
            /** Return 1D Pct */
            return_1d_pct: string;
            /** Sector */
            sector: string;
            /** Synthetic */
            synthetic: boolean;
            /** Ticker */
            ticker: string;
            /** Trading Day */
            trading_day: string;
            /** Weight Global */
            weight_global: string;
            /** Weight Global Pct */
            weight_global_pct: string;
            /** Weight In Sector */
            weight_in_sector: string;
            /** Weight In Sector Pct */
            weight_in_sector_pct: string;
        };
        /**
         * OpportunitiesResponse
         * @description The last published opportunities snapshot — or an honest empty state.
         *
         *     ``state = "ok"`` relays the persisted content VERBATIM: profile
         *     reference (id + version + what is really applied), calendar provenance,
         *     documented lexicographic ordering, qualified and excluded candidates with
         *     their gates, honest evidence checks and published exclusion reasons (the
         *     page's honest empty state on synthetic data). ``state = "stale"`` relays
         *     the SAME content, but says it is past its freshness budget and publishes
         *     why — an old verdict is never presented as current. ``state = "empty"``
         *     means the worker never published. ``state = "clock_inconsistent"`` means
         *     the snapshot is dated further ahead of the relay clock than the declared
         *     drift tolerance: the verdict cannot be dated, so the content is WITHHELD
         *     (``content = None``) and ``reason`` names the clock — the fault is
         *     server-side, not in the persisted payload.
         *
         *     ``age_seconds`` is published in every DATABLE state (server timestamps
         *     only), so the interface can always show how old the verdict is; it stays
         *     ``None`` exactly when no honest age exists (``empty``,
         *     ``clock_inconsistent``).
         */
        OpportunitiesResponse: {
            /** Age Seconds */
            age_seconds: number | null;
            /** As Of */
            as_of: string | null;
            /** Content */
            content: {
                [key: string]: unknown;
            } | null;
            /** Reason */
            reason: string | null;
            /** Snapshot Version */
            snapshot_version: number | null;
            /**
             * State
             * @enum {string}
             */
            state: "ok" | "stale" | "empty" | "clock_inconsistent";
        };
        /**
         * OptionChainContract
         * @description One option contract row, relayed from the worker snapshot verbatim.
         *
         *     The COMPLETE contract identity (synthetic ``con_id``, trading class,
         *     strike, right, multiplier, currency, exchange, style, settlement,
         *     expiration) travels with every row. ``quote`` is the verbatim observed
         *     quote plus its quality status (``OK``/``CROSSED``/``STALE``/``MISSING``);
         *     ``iv`` and ``greeks`` are the worker's Vertex results — present ONLY when
         *     the quote was sane, labeled ``value_nature = "THEORETICAL"`` with their
         *     preserved ``CalculationRecord`` lineage, otherwise honestly ``ABSENT``
         *     with the typed refusal reason. The API recomputes nothing.
         */
        OptionChainContract: {
            /** Con Id */
            con_id: number | null;
            /** Currency */
            currency: string;
            /** Exchange */
            exchange: string;
            /** Expiration */
            expiration: string;
            /** Greeks */
            greeks: {
                [key: string]: unknown;
            };
            /** Iv */
            iv: {
                [key: string]: unknown;
            };
            /** Multiplier */
            multiplier: number;
            /** Open Interest */
            open_interest: number | null;
            /** Open Interest Status */
            open_interest_status: string | null;
            /** Quote */
            quote: {
                [key: string]: unknown;
            };
            /** Right */
            right: ("CALL" | "PUT") | null;
            /** Settlement */
            settlement: string;
            /** Strike */
            strike: string | null;
            /** Style */
            style: string;
            /** Synthetic */
            synthetic: boolean;
            /** Trading Class */
            trading_class: string;
            /** Volume */
            volume: number | null;
        };
        /**
         * OptionChainExpiration
         * @description One ``(expiration, trading_class)`` group — never merged by date.
         *
         *     Two trading classes at the same expiration date are two distinct groups
         *     (distinct identities). ``coverage`` is the worker's honest account:
         *     expected/received/valid/resolved contracts and the per-contract discard
         *     reasons.
         */
        OptionChainExpiration: {
            /** Contracts */
            contracts: components["schemas"]["OptionChainContract"][];
            /** Coverage */
            coverage: {
                [key: string]: unknown;
            };
            /** Currency */
            currency: string;
            /** Exchange */
            exchange: string;
            /** Expiration */
            expiration: string;
            /** Maturity Years */
            maturity_years: string;
            /** Multiplier */
            multiplier: number;
            /** Quality */
            quality: string;
            /** Settlement */
            settlement: string;
            /** Source Event Id */
            source_event_id: string;
            /** Style */
            style: string;
            /** Trading Class */
            trading_class: string;
        };
        /**
         * OptionChainResponse
         * @description The last ``option_chain/{underlying}`` snapshot — or an honest empty.
         *
         *     ``state = "empty"`` means NO snapshot was ever published for this
         *     underlying: every snapshot-derived field is ``None`` (never invented) and
         *     ``reason`` says why. ``state = "ok"`` relays the persisted content
         *     verbatim: population (``SYNTHETIC`` shown as-is), the synthetic spot,
         *     the pricing assumptions, the per-(expiration, trading_class) groups and
         *     the displayed row budget.
         */
        OptionChainResponse: {
            /** As Of */
            as_of: string | null;
            /** Assumptions */
            assumptions: {
                [key: string]: unknown;
            } | null;
            /** Coverage */
            coverage: {
                [key: string]: unknown;
            } | null;
            /** Engine Version */
            engine_version: string | null;
            /** Expirations */
            expirations: components["schemas"]["OptionChainExpiration"][];
            /** Population */
            population: string | null;
            /** Reason */
            reason: string | null;
            /** Row Budget */
            row_budget: {
                [key: string]: unknown;
            } | null;
            /** Snapshot Version */
            snapshot_version: number | null;
            /** Spot */
            spot: {
                [key: string]: unknown;
            } | null;
            /**
             * State
             * @enum {string}
             */
            state: "ok" | "empty";
            /** Underlying */
            underlying: string;
            /** Value Nature */
            value_nature: "THEORETICAL" | null;
        };
        /**
         * OptionLeg
         * @description One declared leg of a manually stated structure (strict, frozen).
         *
         *     Fields:
         *
         *     - ``quantity``: signed integer number of contracts/shares; positive =
         *       long, negative = short; zero is rejected (a leg must exist);
         *     - ``right``: ``"CALL"``, ``"PUT"`` or ``"STOCK"`` (the linear underlying
         *       leg, intrinsic ``h(S) = S``);
         *     - ``strike``: strictly positive ``Decimal``; REQUIRED for CALL/PUT and
         *       FORBIDDEN for STOCK (fail-closed both ways);
         *     - ``premium``: non-negative ``Decimal`` unit premium actually declared
         *       for the leg (for STOCK, the declared unit reference price);
         *     - ``multiplier``: strictly positive int contract multiplier.
         *
         *     Legs describe a manually declared analytic structure only: same
         *     underlying, currency and expiry by construction of the caller. No field
         *     of this model is, or ever becomes, a transmissible ticket of any kind.
         */
        OptionLeg: {
            /** Multiplier */
            multiplier: number;
            /** Premium */
            premium: number | string;
            /** Quantity */
            quantity: number;
            /**
             * Right
             * @enum {string}
             */
            right: "CALL" | "PUT" | "STOCK";
            /**
             * Strike
             * @default null
             */
            strike: number | string | null;
        };
        /**
         * PerformanceExportResponse
         * @description Reproducible export: CSV of the daily points + JSON manifest.
         *
         *     A pure function of one snapshot version — identical calls return
         *     identical bytes; ``as_of`` is the SNAPSHOT's instant, never the request
         *     clock (documented). The manifest carries method, engine version and
         *     input/result hashes for each kept calculation, plus the conventions and
         *     coverage, so the figures can be re-derived and audited independently.
         */
        PerformanceExportResponse: {
            /**
             * As Of
             * Format: date-time
             */
            as_of: string;
            /** Csv */
            csv: string;
            /** Manifest */
            manifest: {
                [key: string]: unknown;
            };
            /** Portfolio Id */
            portfolio_id: number;
            /**
             * Schema Version
             * @constant
             */
            schema_version: "vertex.performance-export/1.0";
            /** Snapshot Version */
            snapshot_version: number;
        };
        /**
         * PerformanceSnapshotResponse
         * @description The last published performance snapshot — or an honest empty state.
         *
         *     ``state = "ok"`` relays the persisted content VERBATIM (series, gates,
         *     gross/net metrics with their lineage, heatmap, coverage, population
         *     ``SYNTHETIC_MARKS_REAL_LEDGER`` shown as-is); the API computes no return,
         *     drawdown or ratio. ``state = "empty"`` means the worker never published
         *     for this portfolio: nothing is invented, ``reason`` says why.
         */
        PerformanceSnapshotResponse: {
            /** As Of */
            as_of: string | null;
            /** Content */
            content: {
                [key: string]: unknown;
            } | null;
            /** Portfolio Id */
            portfolio_id: number;
            /** Reason */
            reason: string | null;
            /** Snapshot Version */
            snapshot_version: number | null;
            /**
             * State
             * @enum {string}
             */
            state: "ok" | "empty";
        };
        /**
         * PortfolioInfo
         * @description The user-declared portfolio identity (never a broker account).
         */
        PortfolioInfo: {
            /** Base Currency */
            base_currency: string;
            /** Id */
            id: number;
            /** Name */
            name: string;
        };
        /**
         * PortfolioLotEntry
         * @description One user-declared position lot, verbatim from the repository.
         */
        PortfolioLotEntry: {
            /** Currency */
            currency: string;
            /** Id */
            id: number;
            /** Instrument */
            instrument: {
                [key: string]: unknown;
            };
            /** Note */
            note: string | null;
            /**
             * Opened At
             * Format: date-time
             */
            opened_at: string;
            /** Quantity */
            quantity: string;
            /** Source */
            source: string;
            /** Unit Cost */
            unit_cost: string;
        };
        /**
         * PortfolioResponse
         * @description The manual portfolio: journal, declared lots, last valuation.
         */
        PortfolioResponse: {
            /** Lots */
            lots: components["schemas"]["PortfolioLotEntry"][];
            portfolio: components["schemas"]["PortfolioInfo"];
            /** Transactions */
            transactions: components["schemas"]["LedgerTransactionEntry"][];
            valuation: components["schemas"]["PortfolioValuationView"];
        };
        /**
         * PortfolioRiskInput
         * @description Facts for gate 7 (``manual_portfolio_risk_available``); declarations are user-made only.
         */
        PortfolioRiskInput: {
            /**
             * Declarations Current
             * @default null
             */
            declarations_current: boolean | null;
            /**
             * Portfolio Risk Available
             * @default null
             */
            portfolio_risk_available: boolean | null;
            /**
             * Risk Required
             * @default null
             */
            risk_required: boolean | null;
        };
        /**
         * PortfolioValuationView
         * @description The last published valuation snapshot — or an honest empty state.
         *
         *     ``state = "empty"`` means the worker never published a valuation for this
         *     portfolio: nothing is invented, ``reason`` says why. ``state = "ok"``
         *     relays the persisted snapshot content VERBATIM (``mark_population``
         *     ``SYNTHETIC`` shown as-is); the API computes no P&L, weight or total.
         */
        PortfolioValuationView: {
            /** As Of */
            as_of: string | null;
            /** Content */
            content: {
                [key: string]: unknown;
            } | null;
            /** Reason */
            reason: string | null;
            /** Snapshot Version */
            snapshot_version: number | null;
            /**
             * State
             * @enum {string}
             */
            state: "ok" | "empty";
        };
        /**
         * ProbabilityInput
         * @description Facts for gate 8 (``probability_calibrated_if_used``).
         */
        ProbabilityInput: {
            /**
             * Calibration Current
             * @default null
             */
            calibration_current: boolean | null;
            /**
             * Calibration Valid
             * @default null
             */
            calibration_valid: boolean | null;
            /**
             * Out Of Sample Validated
             * @default null
             */
            out_of_sample_validated: boolean | null;
            /**
             * Probability Used
             * @default null
             */
            probability_used: boolean | null;
        };
        /**
         * RecordTransactionRequest
         * @description One past fact to append to the accounting journal.
         *
         *     This RECORDS a transaction the user already executed outside Vertex; it
         *     is never an instruction. ``amount`` is the signed cash impact declared by
         *     the user (exact decimal string on the wire); ``effective_at`` must not be
         *     in the future (a fact that has not happened yet cannot be recorded).
         */
        RecordTransactionRequest: {
            /** Amount */
            amount: number | string;
            /** Currency */
            currency: string;
            /**
             * Effective At
             * Format: date-time
             */
            effective_at: string;
            /**
             * Fees
             * @default 0
             */
            fees: number | string;
            /** @default null */
            instrument: components["schemas"]["InstrumentRefInput"] | null;
            kind: components["schemas"]["LedgerEventKind"];
            /**
             * Note
             * @default null
             */
            note: string | null;
            /**
             * Price
             * @default null
             */
            price: number | string | null;
            /**
             * Quantity
             * @default null
             */
            quantity: number | string | null;
        };
        /**
         * RecordTransactionResponse
         * @description Receipt of one recorded journal fact.
         */
        RecordTransactionResponse: {
            /** Refresh Enqueued */
            refresh_enqueued: boolean;
            /** Transaction Id */
            transaction_id: number;
        };
        /**
         * RegisterVerifyRequest
         * @description Client answer to a registration ceremony.
         */
        RegisterVerifyRequest: {
            /** Credential */
            credential: {
                [key: string]: unknown;
            };
            /** Flow Id */
            flow_id: string;
            /** Label */
            label: string;
        };
        /**
         * RegisterVerifyResponse
         * @description Registration acknowledged. Carries no secret and no credential material.
         */
        RegisterVerifyResponse: {
            /** Label */
            label: string;
            /**
             * Registered
             * @constant
             */
            registered: true;
        };
        /**
         * SessionEventInput
         * @description Facts for gate 4 (``session_and_event_known``).
         */
        SessionEventInput: {
            /**
             * Event Calendar Known
             * @default null
             */
            event_calendar_known: boolean | null;
            /**
             * Session Known
             * @default null
             */
            session_known: boolean | null;
        };
        /**
         * SimulationAssumptions
         * @description Declared assumptions of one preview (decimal strings on the wire).
         *
         *     ``spot`` is the declared underlying reference of the snapshot the user
         *     composed against (echoed back); ``volatility`` is the single annualized
         *     decimal volatility applied to every option leg of the scenario grid
         *     (``0.25`` = 25%/yr); ``rate`` / ``dividend_yield`` are continuously
         *     compounded annualized decimals; ``fees`` groups the positive declared
         *     costs of the expiry payoff. The grids are BOUNDED by the wire contract.
         */
        SimulationAssumptions: {
            /** Dividend Yield */
            dividend_yield: number | string;
            /**
             * Fees
             * @default 0
             */
            fees: number | string;
            /** Rate */
            rate: number | string;
            /** Spot */
            spot: number | string;
            /** Spot Grid */
            spot_grid: (number | string)[];
            /** Time Grid Years */
            time_grid_years: (number | string)[];
            /** Volatility */
            volatility: number | string;
        };
        /**
         * SimulationBreakeven
         * @description One certified expiry breakeven.
         *
         *     ``payoff_at_spot`` is the authority's own re-evaluation of
         *     ``options.payoff`` at the reported spot (exact ``Decimal``; non-zero only
         *     through decimal quantization of the crossing point). ``bracket_low`` /
         *     ``bracket_high`` are the two authoritative evaluation points whose sign
         *     change pinned the crossing.
         */
        SimulationBreakeven: {
            /** Bracket High */
            bracket_high: string;
            /** Bracket Low */
            bracket_low: string;
            /** Payoff At Spot */
            payoff_at_spot: string;
            /** Spot */
            spot: string;
        };
        /**
         * SimulationExtreme
         * @description Best/worst expiry P&L over the evaluation grid, with its spot.
         */
        SimulationExtreme: {
            /** At Spot */
            at_spot: string;
            /** Pnl */
            pnl: string;
        };
        /**
         * SimulationPayoffPoint
         * @description Exact expiry P&L at one evaluated terminal spot (decimal strings).
         */
        SimulationPayoffPoint: {
            /** Pnl */
            pnl: string;
            /** Spot */
            spot: string;
        };
        /**
         * SimulationPreviewRequest
         * @description One declared structure plus its assumptions.
         *
         *     Legs ARE the engine's own :class:`OptionLeg` contract (strict: signed
         *     non-zero quantity, strike required on CALL/PUT and forbidden on STOCK,
         *     non-negative decimal premium, positive integer multiplier) — the wire
         *     never redefines the calculation contract.
         */
        SimulationPreviewRequest: {
            assumptions: components["schemas"]["SimulationAssumptions"];
            /** Legs */
            legs: components["schemas"]["OptionLeg"][];
        };
        /**
         * SimulationPreviewResponse
         * @description The full preview result (nothing persisted, nothing transactional).
         */
        SimulationPreviewResponse: {
            /** Assumptions */
            assumptions: {
                [key: string]: unknown;
            };
            /** Breakevens */
            breakevens: components["schemas"]["SimulationBreakeven"][];
            /** Calculations */
            calculations: {
                [key: string]: unknown;
            };
            /** Defined Risk */
            defined_risk: {
                [key: string]: unknown;
            };
            max_gain_on_grid: components["schemas"]["SimulationExtreme"];
            max_loss_on_grid: components["schemas"]["SimulationExtreme"];
            /** Payoff Points */
            payoff_points: components["schemas"]["SimulationPayoffPoint"][];
            /** Scenario Grid */
            scenario_grid: string[][][];
            /** Scenario Spot Grid */
            scenario_spot_grid: string[];
            /** Scenario Time Grid Years */
            scenario_time_grid_years: string[];
            /**
             * Value Nature
             * @constant
             */
            value_nature: "THEORETICAL";
            /** Warnings */
            warnings: string[];
        };
        /**
         * SnapshotHealth
         * @description Presence and age of one published snapshot head (no content).
         */
        SnapshotHealth: {
            /** Age Seconds */
            age_seconds: number | null;
            /** As Of */
            as_of: string | null;
            /** Present */
            present: boolean;
            /** Version */
            version: number | null;
        };
        /**
         * SnapshotInput
         * @description Facts for gate 3 (``snapshot_fresh_and_coherent``).
         */
        SnapshotInput: {
            /**
             * Fresh
             * @default null
             */
            fresh: boolean | null;
            /** @default null */
            quality: components["schemas"]["SnapshotQuality"] | null;
        };
        /**
         * SnapshotQuality
         * @description Quality of an evidence snapshot (namespace distinct from ``EnvelopeQuality``).
         *
         *     Neither quality namespace converts implicitly into the other (ADR-014).
         * @enum {string}
         */
        SnapshotQuality: "GOOD" | "PARTIAL" | "DEGRADED" | "MISSING" | "CONTRADICTORY";
        /**
         * SourceCapabilityStatus
         * @description Effective availability of one data-source capability (market data only).
         * @enum {string}
         */
        SourceCapabilityStatus: "AVAILABLE" | "DELAYED" | "NOT_ENTITLED" | "UNSUPPORTED" | "ERROR" | "MANUAL_EXPORT";
        /**
         * SystemCapabilitiesResponse
         * @description Every declared capability with its really-tested status, plus health.
         *
         *     ``total`` equals the exact number of manifest entries; ``as_of`` and
         *     ``snapshot_version`` describe the persisted capabilities snapshot
         *     (``None`` when never published). ``unknown_probed_capability_ids`` lists
         *     probed ids absent from the manifest — never silently dropped, never
         *     merged into the declared set. ``checked_at`` is the response instant.
         */
        SystemCapabilitiesResponse: {
            /** As Of */
            as_of: string | null;
            /** Capabilities */
            capabilities: components["schemas"]["CapabilityStatusEntry"][];
            /**
             * Checked At
             * Format: date-time
             */
            checked_at: string;
            health: components["schemas"]["SystemHealth"];
            /** Snapshot Version */
            snapshot_version: number | null;
            /** Total */
            total: number;
            /** Unknown Probed Capability Ids */
            unknown_probed_capability_ids: string[];
        };
        /**
         * SystemHealth
         * @description Health blocks: database, both snapshot heads, worker proxy.
         */
        SystemHealth: {
            attention_snapshot: components["schemas"]["SnapshotHealth"];
            capabilities_snapshot: components["schemas"]["SnapshotHealth"];
            db: components["schemas"]["DbHealth"];
            worker: components["schemas"]["WorkerHealth"];
        };
        /**
         * ThesisInstrumentInput
         * @description Canonical instrument reference of a thesis (plain ticker for now).
         */
        ThesisInstrumentInput: {
            /** Ticker */
            ticker: string;
        };
        /**
         * ThesisRevisionRequest
         * @description One append-only review-lifecycle revision of an existing thesis.
         *
         *     ``snooze_until`` is required exactly when ``action`` is SNOOZED and
         *     forbidden otherwise (also enforced by the repository and by CHECK).
         */
        ThesisRevisionRequest: {
            /**
             * Action
             * @enum {string}
             */
            action: "REVIEWED" | "SNOOZED" | "NOTE_UPDATED" | "ARCHIVED" | "REACTIVATED";
            /** Idempotency Key */
            idempotency_key: string;
            /**
             * Note
             * @default null
             */
            note: string | null;
            /**
             * Snapshot Ref
             * @default null
             */
            snapshot_ref: string | null;
            /**
             * Snooze Until
             * @default null
             */
            snooze_until: string | null;
        };
        /**
         * ThesisRevisionResponse
         * @description Receipt: ``created=false`` marks an idempotent replay (nothing written).
         */
        ThesisRevisionResponse: {
            /** Created */
            created: boolean;
            /** Refresh Enqueued */
            refresh_enqueued: boolean;
            /** Revision Id */
            revision_id: number;
            /** Thesis Id */
            thesis_id: number;
        };
        /** ValidationError */
        ValidationError: {
            /** Context */
            ctx?: Record<string, never>;
            /** Input */
            input?: unknown;
            /** Location */
            loc: (string | number)[];
            /** Message */
            msg: string;
            /** Error Type */
            type: string;
        };
        /**
         * WorkerHealth
         * @description Honest worker liveness proxy: the age of the freshest snapshot.
         *
         *     The worker exposes no direct heartbeat; the method label
         *     ``heartbeat_proxy`` names that limitation explicitly instead of
         *     pretending to observe the process.
         */
        WorkerHealth: {
            /** Age Seconds */
            age_seconds: number | null;
            /** Last Snapshot As Of */
            last_snapshot_as_of: string | null;
            /**
             * Method
             * @constant
             */
            method: "heartbeat_proxy";
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    post_advice_preview: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AdvicePreviewRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AdviceResult"];
                };
            };
            /** @description Authentication required: no valid WebAuthn session cookie (or missing/invalid CSRF header on a mutation). Always the same generic body with detail code AUTH_REQUIRED. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    post_ai_explain: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AiExplainRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AiAnswer"];
                };
            };
            /** @description Authentication required: no valid WebAuthn session cookie (or missing/invalid CSRF header on a mutation). Always the same generic body with detail code AUTH_REQUIRED. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description No snapshot was ever published for this subject (code NO_SNAPSHOT_FOR_SUBJECT) — there is nothing honest to explain. */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    get_ai_status: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AiStatusResponse"];
                };
            };
            /** @description Authentication required: no valid WebAuthn session cookie (or missing/invalid CSRF header on a mutation). Always the same generic body with detail code AUTH_REQUIRED. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    get_analysis: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                instrument: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AnalysisResponse"];
                };
            };
            /** @description Authentication required: no valid WebAuthn session cookie (or missing/invalid CSRF header on a mutation). Always the same generic body with detail code AUTH_REQUIRED. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    post_auth_login_options: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CeremonyOptionsResponse"];
                };
            };
            /** @description Authentication failed. Always the same generic body (code AUTH_REQUIRED) whatever the cause. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    post_auth_login_verify: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["LoginVerifyRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LoginVerifyResponse"];
                };
            };
            /** @description Authentication failed. Always the same generic body (code AUTH_REQUIRED) whatever the cause. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    post_auth_logout: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LogoutResponse"];
                };
            };
            /** @description Authentication failed. Always the same generic body (code AUTH_REQUIRED) whatever the cause. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    post_auth_register_options: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CeremonyOptionsResponse"];
                };
            };
            /** @description Authentication failed. Always the same generic body (code AUTH_REQUIRED) whatever the cause. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    post_auth_register_verify: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RegisterVerifyRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RegisterVerifyResponse"];
                };
            };
            /** @description Authentication failed. Always the same generic body (code AUTH_REQUIRED) whatever the cause. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_calendar: {
        parameters: {
            query?: {
                from?: string | null;
                to?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CalendarResponse"];
                };
            };
            /** @description Authentication required: no valid WebAuthn session cookie (or missing/invalid CSRF header on a mutation). Always the same generic body with detail code AUTH_REQUIRED. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Rejected fail-closed window: WINDOW_INCOMPLETE (one bound without the other), WINDOW_NAIVE_DATETIME, WINDOW_INVERTED or WINDOW_TOO_LARGE (bounded to 90 days). */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    get_events_stream: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description text/event-stream of `snapshot` events (`{"resource": "<kind>/<key>", "version": <int>}`) and keepalive `ping` events. Signal only — no business data; clients refetch through the REST endpoints. */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "text/event-stream": string;
                };
            };
            /** @description Authentication required: no valid WebAuthn session cookie (or missing/invalid CSRF header on a mutation). Always the same generic body with detail code AUTH_REQUIRED. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    get_follow_up_queue: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FollowUpQueueResponse"];
                };
            };
            /** @description Authentication required: no valid WebAuthn session cookie (or missing/invalid CSRF header on a mutation). Always the same generic body with detail code AUTH_REQUIRED. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    get_health: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HealthResponse"];
                };
            };
        };
    };
    get_markets_overview: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MarketsOverviewResponse"];
                };
            };
            /** @description Authentication required: no valid WebAuthn session cookie (or missing/invalid CSRF header on a mutation). Always the same generic body with detail code AUTH_REQUIRED. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    get_opportunities: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OpportunitiesResponse"];
                };
            };
            /** @description Authentication required: no valid WebAuthn session cookie (or missing/invalid CSRF header on a mutation). Always the same generic body with detail code AUTH_REQUIRED. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    get_option_chain: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                underlying: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OptionChainResponse"];
                };
            };
            /** @description Authentication required: no valid WebAuthn session cookie (or missing/invalid CSRF header on a mutation). Always the same generic body with detail code AUTH_REQUIRED. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_performance: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                portfolio_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PerformanceSnapshotResponse"];
                };
            };
            /** @description Authentication required: no valid WebAuthn session cookie (or missing/invalid CSRF header on a mutation). Always the same generic body with detail code AUTH_REQUIRED. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    export_performance: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                portfolio_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PerformanceExportResponse"];
                };
            };
            /** @description Authentication required: no valid WebAuthn session cookie (or missing/invalid CSRF header on a mutation). Always the same generic body with detail code AUTH_REQUIRED. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description No performance snapshot was ever published for this portfolio — code NO_PERFORMANCE_SNAPSHOT — there is nothing honest to export. */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_portfolio: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PortfolioResponse"];
                };
            };
            /** @description Authentication required: no valid WebAuthn session cookie (or missing/invalid CSRF header on a mutation). Always the same generic body with detail code AUTH_REQUIRED. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    export_portfolio: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description text/csv: one version-stamp comment line, the header row and the ledger rows — no other data. Cells starting with '=', '+', '-' or '@' are neutralized with a leading apostrophe against spreadsheet formula injection. */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "text/csv": string;
                };
            };
            /** @description Authentication required: no valid WebAuthn session cookie (or missing/invalid CSRF header on a mutation). Always the same generic body with detail code AUTH_REQUIRED. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    confirm_portfolio_import: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ImportConfirmRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ImportConfirmResponse"];
                };
            };
            /** @description Authentication required: no valid WebAuthn session cookie (or missing/invalid CSRF header on a mutation). Always the same generic body with detail code AUTH_REQUIRED. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Rejected fail-closed: IMPORT_ROW_INVALID (a row no longer passes the replayed validation) or ECHO_HASH_MISMATCH (an echoed row was altered after the preview). Nothing is written on rejection. */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    preview_portfolio_import: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CsvImportPreviewRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ImportPreviewResponse"];
                };
            };
            /** @description Authentication required: no valid WebAuthn session cookie (or missing/invalid CSRF header on a mutation). Always the same generic body with detail code AUTH_REQUIRED. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Whole-input rejection: CSV_TOO_LARGE (256 KiB), CSV_TOO_MANY_ROWS (500 data rows) or CSV_HEADER_INVALID. */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    record_transaction: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RecordTransactionRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RecordTransactionResponse"];
                };
            };
            /** @description Authentication required: no valid WebAuthn session cookie (or missing/invalid CSRF header on a mutation). Always the same generic body with detail code AUTH_REQUIRED. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Rejected fail-closed: wire-contract violation or EFFECTIVE_AT_IN_FUTURE (a fact that has not happened yet cannot be recorded). */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    compensate_transaction: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                transaction_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CompensateTransactionRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CompensateTransactionResponse"];
                };
            };
            /** @description Authentication required: no valid WebAuthn session cookie (or missing/invalid CSRF header on a mutation). Always the same generic body with detail code AUTH_REQUIRED. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Unknown transaction (code UNKNOWN_TRANSACTION). */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description The transaction already has a compensating row (code ALREADY_COMPENSATED) — history is append-only, a fact is corrected at most once. */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    post_simulations_preview: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SimulationPreviewRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SimulationPreviewResponse"];
                };
            };
            /** @description Authentication required: no valid WebAuthn session cookie (or missing/invalid CSRF header on a mutation). Always the same generic body with detail code AUTH_REQUIRED. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Rejected fail-closed with the exact machine-readable reason: either a wire-contract violation, or the defined-risk verifier's code (e.g. OUTSIDE_CLOSED_CATALOG, UNCOVERED_SHORT_UPSIDE_TAIL, VERTICAL_DEBIT_NOT_BELOW_WIDTH), or a typed calculation-domain violation from vertex_core. */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    get_system_capabilities: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SystemCapabilitiesResponse"];
                };
            };
            /** @description Authentication required: no valid WebAuthn session cookie (or missing/invalid CSRF header on a mutation). Always the same generic body with detail code AUTH_REQUIRED. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    get_system_engine: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EngineInfoResponse"];
                };
            };
            /** @description Authentication required: no valid WebAuthn session cookie (or missing/invalid CSRF header on a mutation). Always the same generic body with detail code AUTH_REQUIRED. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    create_thesis: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateThesisRequest"];
            };
        };
        responses: {
            /** @description Idempotent replay: the client's idempotency_key already names this thesis — nothing was written, created=false, the original ids are returned. */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CreateThesisResponse"];
                };
            };
            /** @description Authentication required: no valid WebAuthn session cookie (or missing/invalid CSRF header on a mutation). Always the same generic body with detail code AUTH_REQUIRED. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Unknown portfolio — code UNKNOWN_PORTFOLIO. */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description The idempotency_key already names a DIFFERENT operation (code IDEMPOTENCY_KEY_REUSED) — keys are never recycled. */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Rejected fail-closed: blank invalidation, missing idempotency_key or any other wire-contract violation. */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    record_thesis_revision: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                thesis_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ThesisRevisionRequest"];
            };
        };
        responses: {
            /** @description Idempotent replay: the client's idempotency_key already names this exact revision — nothing was written, created=false, the original revision id is returned. Ten replays leave exactly one row. */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ThesisRevisionResponse"];
                };
            };
            /** @description Authentication required: no valid WebAuthn session cookie (or missing/invalid CSRF header on a mutation). Always the same generic body with detail code AUTH_REQUIRED. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Unknown thesis (code UNKNOWN_THESIS). */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description The idempotency_key already names a DIFFERENT operation (code IDEMPOTENCY_KEY_REUSED) — keys are never recycled. */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Rejected fail-closed: action outside the allowlist (CREATED included), snooze_until missing on SNOOZED or present elsewhere, or any wire-contract violation. */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    get_today_attention: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AttentionSnapshotResponse"];
                };
            };
            /** @description Authentication required: no valid WebAuthn session cookie (or missing/invalid CSRF header on a mutation). Always the same generic body with detail code AUTH_REQUIRED. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
}
