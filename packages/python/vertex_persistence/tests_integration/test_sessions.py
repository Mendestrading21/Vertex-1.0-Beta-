"""Passkey credential and session storage: full cycle, fail-closed paths.

All inputs are SYNTHETIC and deterministic (fixed aware-UTC instants, fixed
byte strings). Covers: register/get/list, the bootstrap counter, the full
session cycle (create -> validate -> revoke), expiry, CSRF hashing, the
sign-count regression clone response (credential + sessions revoked) and the
proof that no opaque token is ever stored in clear in the database.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from vertex_persistence.errors import (
    CredentialRevokedError,
    DuplicateCredentialError,
    SignCountRegressionError,
    UnknownCredentialError,
    ValidationFailedError,
)
from vertex_persistence.repository.sessions import (
    DEFAULT_SESSION_TTL,
    MAX_SESSION_TTL,
    count_credentials,
    create_session,
    get_credential,
    hash_token,
    list_active_credentials,
    purge_expired,
    register_credential,
    revoke_session,
    update_sign_count,
    validate_csrf,
    validate_session,
)

T0 = datetime(2026, 8, 1, 12, 0, 0, tzinfo=UTC)

CRED_ID = b"synthetic-credential-id-1"
PUB_KEY = b"synthetic-cose-public-key-bytes"


def _register(db_session: Session, *, cred_id: bytes = CRED_ID, sign_count: int = 0):
    return register_credential(
        db_session,
        credential_id=cred_id,
        public_key=PUB_KEY,
        sign_count=sign_count,
        transports="internal",
        label="synthetic passkey",
        now=T0,
    )


class TestCredentials:
    def test_register_get_and_list(self, db_session: Session) -> None:
        assert count_credentials(db_session) == 0
        record = _register(db_session)
        assert record.credential_id == CRED_ID
        assert record.public_key == PUB_KEY
        assert record.sign_count == 0
        assert record.revoked_at is None
        assert count_credentials(db_session) == 1
        fetched = get_credential(db_session, credential_id=CRED_ID)
        assert fetched == record
        assert list_active_credentials(db_session) == (record,)

    def test_unknown_credential_reads_as_none(self, db_session: Session) -> None:
        assert get_credential(db_session, credential_id=b"absent") is None

    def test_duplicate_credential_id_fails_closed(self, db_session: Session) -> None:
        _register(db_session)
        with pytest.raises(DuplicateCredentialError):
            _register(db_session)

    def test_naive_datetime_is_rejected(self, db_session: Session) -> None:
        from vertex_persistence.errors import ClockError

        with pytest.raises(ClockError):
            register_credential(
                db_session,
                credential_id=CRED_ID,
                public_key=PUB_KEY,
                sign_count=0,
                transports=None,
                label="x",
                # naïf délibéré : rejet vérifié
                now=datetime(2026, 8, 1, 12, 0, 0),  # naive: rejected  # noqa: DTZ001
            )

    def test_empty_bytes_and_negative_sign_count_rejected(
        self, db_session: Session
    ) -> None:
        with pytest.raises(ValidationFailedError):
            register_credential(
                db_session,
                credential_id=b"",
                public_key=PUB_KEY,
                sign_count=0,
                transports=None,
                label="x",
                now=T0,
            )
        with pytest.raises(ValidationFailedError):
            register_credential(
                db_session,
                credential_id=CRED_ID,
                public_key=PUB_KEY,
                sign_count=-1,
                transports=None,
                label="x",
                now=T0,
            )


class TestSessionCycle:
    def test_full_cycle_create_validate_revoke(self, db_session: Session) -> None:
        _register(db_session)
        issued = create_session(db_session, credential_id=CRED_ID, now=T0)
        assert issued.expires_at == T0 + DEFAULT_SESSION_TTL

        validated = validate_session(
            db_session, session_token=issued.session_token, now=T0 + timedelta(minutes=1)
        )
        assert validated is not None
        assert validated.credential_label == "synthetic passkey"
        assert validate_csrf(validated, issued.csrf_token) is True
        assert validate_csrf(validated, "forged-csrf-token") is False
        assert validate_csrf(validated, "") is False

        assert (
            revoke_session(db_session, session_token=issued.session_token, now=T0) is True
        )
        assert (
            validate_session(
                db_session, session_token=issued.session_token, now=T0 + timedelta(minutes=2)
            )
            is None
        )
        # Revoking twice is idempotent and reports nothing was live.
        assert (
            revoke_session(db_session, session_token=issued.session_token, now=T0) is False
        )

    def test_expired_session_validates_to_none(self, db_session: Session) -> None:
        _register(db_session)
        issued = create_session(
            db_session, credential_id=CRED_ID, now=T0, ttl=timedelta(minutes=30)
        )
        at_expiry = issued.expires_at
        assert (
            validate_session(db_session, session_token=issued.session_token, now=at_expiry) is None
        )
        just_before = at_expiry - timedelta(seconds=1)
        assert (
            validate_session(db_session, session_token=issued.session_token, now=just_before)
            is not None
        )

    def test_unknown_token_validates_to_none(self, db_session: Session) -> None:
        _register(db_session)
        assert validate_session(db_session, session_token="never-issued", now=T0) is None

    def test_ttl_ceiling_is_enforced(self, db_session: Session) -> None:
        _register(db_session)
        with pytest.raises(ValidationFailedError):
            create_session(
                db_session,
                credential_id=CRED_ID,
                now=T0,
                ttl=MAX_SESSION_TTL + timedelta(seconds=1),
            )
        with pytest.raises(ValidationFailedError):
            create_session(db_session, credential_id=CRED_ID, now=T0, ttl=timedelta(0))

    def test_session_for_unknown_or_revoked_credential_fails(
        self, db_session: Session
    ) -> None:
        with pytest.raises(UnknownCredentialError):
            create_session(db_session, credential_id=b"absent", now=T0)
        _register(db_session)
        # Force a revocation through the clone path (5 -> 5 regression).
        update_sign_count(db_session, credential_id=CRED_ID, new_sign_count=5, now=T0)
        with pytest.raises(SignCountRegressionError):
            update_sign_count(db_session, credential_id=CRED_ID, new_sign_count=5, now=T0)
        with pytest.raises(CredentialRevokedError):
            create_session(db_session, credential_id=CRED_ID, now=T0)

    def test_purge_expired_removes_only_dead_sessions(self, db_session: Session) -> None:
        _register(db_session)
        live = create_session(db_session, credential_id=CRED_ID, now=T0)
        expired = create_session(
            db_session, credential_id=CRED_ID, now=T0, ttl=timedelta(minutes=1)
        )
        revoked = create_session(db_session, credential_id=CRED_ID, now=T0)
        revoke_session(db_session, session_token=revoked.session_token, now=T0)

        removed = purge_expired(db_session, now=T0 + timedelta(minutes=5))
        assert removed == 2
        assert (
            validate_session(
                db_session, session_token=live.session_token, now=T0 + timedelta(minutes=5)
            )
            is not None
        )
        assert (
            validate_session(
                db_session, session_token=expired.session_token, now=T0 + timedelta(minutes=5)
            )
            is None
        )


class TestSignCount:
    def test_increasing_sign_count_is_stored(self, db_session: Session) -> None:
        _register(db_session)
        record = update_sign_count(db_session, credential_id=CRED_ID, new_sign_count=1, now=T0)
        assert record.sign_count == 1
        record = update_sign_count(db_session, credential_id=CRED_ID, new_sign_count=7, now=T0)
        assert record.sign_count == 7

    def test_counterless_authenticator_zero_zero_is_accepted(
        self, db_session: Session
    ) -> None:
        _register(db_session, sign_count=0)
        record = update_sign_count(db_session, credential_id=CRED_ID, new_sign_count=0, now=T0)
        assert record.sign_count == 0
        assert record.revoked_at is None

    @pytest.mark.parametrize("regressed", [0, 3, 7])
    def test_regression_revokes_credential_and_all_sessions(
        self, db_session: Session, regressed: int
    ) -> None:
        """Clone detected: the credential AND every session die, fail-closed."""
        _register(db_session, sign_count=7)
        first = create_session(db_session, credential_id=CRED_ID, now=T0)
        second = create_session(db_session, credential_id=CRED_ID, now=T0)

        with pytest.raises(SignCountRegressionError):
            update_sign_count(
                db_session, credential_id=CRED_ID, new_sign_count=regressed, now=T0
            )

        credential = get_credential(db_session, credential_id=CRED_ID)
        assert credential is not None and credential.revoked_at is not None
        assert list_active_credentials(db_session) == ()
        later = T0 + timedelta(minutes=1)
        assert validate_session(db_session, session_token=first.session_token, now=later) is None
        assert validate_session(db_session, session_token=second.session_token, now=later) is None

    def test_update_unknown_credential_fails(self, db_session: Session) -> None:
        with pytest.raises(UnknownCredentialError):
            update_sign_count(db_session, credential_id=b"absent", new_sign_count=1, now=T0)


class TestNoClearTokenInDatabase:
    def test_no_opaque_token_stored_in_clear(self, db_session: Session) -> None:
        """Scan every text column of the auth tables: the issued tokens never
        appear in storage — only their prefixed SHA-256 hashes do."""
        _register(db_session)
        issued = create_session(db_session, credential_id=CRED_ID, now=T0)
        db_session.commit()

        rows = db_session.execute(
            text(
                "SELECT session_id_hash, csrf_token_hash, "
                "CAST(created_at AS TEXT), CAST(expires_at AS TEXT) FROM auth_sessions"
            )
        ).all()
        assert len(rows) == 1
        stored_values = [value for row in rows for value in row if value is not None]
        for secret_value in (issued.session_token, issued.csrf_token):
            for stored in stored_values:
                assert secret_value not in stored
        assert rows[0][0] == hash_token(issued.session_token)
        assert rows[0][1] == hash_token(issued.csrf_token)
        assert rows[0][0].startswith("sha256:")

    def test_hash_token_is_deterministic_and_one_way_shaped(self) -> None:
        assert hash_token("abc") == hash_token("abc")
        assert hash_token("abc") != hash_token("abd")
        assert len(hash_token("abc")) == len("sha256:") + 64
