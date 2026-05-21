"""VAPID-Keys für Web Push erzeugen (Anforderung K4).

Ausführen: python scripts/generate_vapid_keys.py

Gibt VAPID_PRIVATE_KEY und VAPID_PUBLIC_KEY in URL-safe Base64 aus
(beide Werte gehen 1:1 in backend/.env). Der gleiche Public-Key wird auch
vom Frontend per /api/v1/users/vapid-public-key abgeholt und an
PushManager.subscribe übergeben.
"""

from __future__ import annotations

import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def main() -> None:
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()

    priv_raw = private_key.private_numbers().private_value.to_bytes(32, "big")
    pub_raw = public_key.public_bytes(
        serialization.Encoding.X962,
        serialization.PublicFormat.UncompressedPoint,
    )

    print("# VAPID-Keys (in backend/.env eintragen)")
    print(f"VAPID_PRIVATE_KEY={_b64url(priv_raw)}")
    print(f"VAPID_PUBLIC_KEY={_b64url(pub_raw)}")
    print("VAPID_SUBJECT=mailto:admin@happin.fun")


if __name__ == "__main__":
    main()
