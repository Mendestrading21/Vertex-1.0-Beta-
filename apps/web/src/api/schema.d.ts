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
