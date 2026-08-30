"""SYNTHETIC software passkey (ES256, attestation 'none') and ceremony helpers.

Explicitly SYNTHETIC test tooling: a deterministic software authenticator
that answers real WebAuthn ceremonies so the API integration tests exercise
py_webauthn verification without hardware. Never crosses a production
boundary.
"""

from __future__ import annotations

import hashlib
import json
import os
import struct
from typing import Any

import cbor2
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
from webauthn.helpers import bytes_to_base64url

_RP_ID = "localhost"
_ORIGIN = "http://localhost"

# Authenticator data flags.
_FLAG_UP = 0x01
_FLAG_UV = 0x04
_FLAG_AT = 0x40


class SoftPasskey:
    """SYNTHETIC software authenticator (ES256, attestation 'none').

    Deterministic apart from the key pair; the signature counter starts at 0
    and increments on every assertion unless pinned explicitly (clone tests).
    """

    def __init__(self, *, origin: str = _ORIGIN, rp_id: str = _RP_ID) -> None:
        self.origin = origin
        self.rp_id = rp_id
        self.credential_id = os.urandom(32)
        self.private_key = ec.generate_private_key(ec.SECP256R1())
        self.sign_count = 0

    # -- helpers -----------------------------------------------------------
    def _rp_id_hash(self) -> bytes:
        return hashlib.sha256(self.rp_id.encode("utf-8")).digest()

    def _cose_public_key(self) -> bytes:
        numbers = self.private_key.public_key().public_numbers()
        return cbor2.dumps(
            {
                1: 2,  # kty: EC2
                3: -7,  # alg: ES256
                -1: 1,  # crv: P-256
                -2: numbers.x.to_bytes(32, "big"),
                -3: numbers.y.to_bytes(32, "big"),
            }
        )

    def _client_data(self, ceremony_type: str, challenge_b64url: str) -> bytes:
        return json.dumps(
            {
                "type": ceremony_type,
                "challenge": challenge_b64url,
                "origin": self.origin,
                "crossOrigin": False,
            }
        ).encode("utf-8")

    # -- ceremonies --------------------------------------------------------
    def create(self, options: dict[str, Any]) -> dict[str, Any]:
        """Answer a registration ceremony (navigator.credentials.create)."""
        client_data = self._client_data("webauthn.create", options["challenge"])
        attested = (
            bytes(16)  # zero AAGUID
            + struct.pack(">H", len(self.credential_id))
            + self.credential_id
            + self._cose_public_key()
        )
        auth_data = (
            self._rp_id_hash()
            + bytes([_FLAG_UP | _FLAG_UV | _FLAG_AT])
            + struct.pack(">I", self.sign_count)
            + attested
        )
        attestation_object = cbor2.dumps({"fmt": "none", "attStmt": {}, "authData": auth_data})
        return {
            "id": bytes_to_base64url(self.credential_id),
            "rawId": bytes_to_base64url(self.credential_id),
            "response": {
                "clientDataJSON": bytes_to_base64url(client_data),
                "attestationObject": bytes_to_base64url(attestation_object),
                "transports": ["internal"],
            },
            "type": "public-key",
            "clientExtensionResults": {},
        }

    def get(
        self, options: dict[str, Any], *, sign_count: int | None = None
    ) -> dict[str, Any]:
        """Answer an authentication ceremony (navigator.credentials.get).

        ``sign_count`` pins the reported counter (clone simulation); by
        default the counter increments like a healthy authenticator.
        """
        if sign_count is None:
            self.sign_count += 1
            reported = self.sign_count
        else:
            reported = sign_count
        client_data = self._client_data("webauthn.get", options["challenge"])
        auth_data = (
            self._rp_id_hash() + bytes([_FLAG_UP | _FLAG_UV]) + struct.pack(">I", reported)
        )
        signed = auth_data + hashlib.sha256(client_data).digest()
        signature = self.private_key.sign(signed, ec.ECDSA(hashes.SHA256()))
        return {
            "id": bytes_to_base64url(self.credential_id),
            "rawId": bytes_to_base64url(self.credential_id),
            "response": {
                "clientDataJSON": bytes_to_base64url(client_data),
                "authenticatorData": bytes_to_base64url(auth_data),
                "signature": bytes_to_base64url(signature),
                "userHandle": None,
            },
            "type": "public-key",
            "clientExtensionResults": {},
        }


def register_passkey(
    client: TestClient, passkey: SoftPasskey, *, label: str = "synthetic passkey"
) -> None:
    """Run the full registration ceremony; asserts success."""
    options_response = client.post("/api/v1/auth/register/options")
    assert options_response.status_code == 200, options_response.text
    body = options_response.json()
    credential = passkey.create(body["options"])
    verify_response = client.post(
        "/api/v1/auth/register/verify",
        json={"flow_id": body["flow_id"], "label": label, "credential": credential},
    )
    assert verify_response.status_code == 200, verify_response.text
    assert verify_response.json() == {"registered": True, "label": label}


def login_passkey(
    client: TestClient, passkey: SoftPasskey, *, sign_count: int | None = None
) -> Any:
    """Run the full authentication ceremony; returns the verify response."""
    options_response = client.post("/api/v1/auth/login/options")
    assert options_response.status_code == 200, options_response.text
    body = options_response.json()
    credential = passkey.get(body["options"], sign_count=sign_count)
    return client.post(
        "/api/v1/auth/login/verify",
        json={"flow_id": body["flow_id"], "credential": credential},
    )


__all__ = ["SoftPasskey", "login_passkey", "register_passkey"]
