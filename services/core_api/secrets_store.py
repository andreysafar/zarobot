"""
Encryption for secrets kept at rest, currently TON wallet private keys.

The `ton_wallets.encrypted_private_key` column has always been named as though
its contents were encrypted, while raw private keys were written into it: any
read access to the SQLite file handed over every user's wallet.

Key material comes from WALLET_ENCRYPTION_KEY (a Fernet key). Without it the
service refuses to store or read private keys rather than silently falling back
to plaintext.
"""

from __future__ import annotations

import os

from cryptography.fernet import Fernet, InvalidToken
from loguru import logger


class EncryptionUnavailable(RuntimeError):
    """Raised when WALLET_ENCRYPTION_KEY is missing or unusable."""


def _fernet() -> Fernet:
    key = os.getenv("WALLET_ENCRYPTION_KEY", "")
    if not key:
        raise EncryptionUnavailable(
            "WALLET_ENCRYPTION_KEY is not set; refusing to handle private keys. "
            "Generate one with: python -c "
            "\"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except (ValueError, TypeError) as e:
        raise EncryptionUnavailable(f"WALLET_ENCRYPTION_KEY is not a valid Fernet key: {e}")


def encrypt_secret(plaintext: str | bytes) -> str:
    """Encrypt a secret for storage. Returns a token safe to put in a text column."""
    if isinstance(plaintext, str):
        plaintext = plaintext.encode()
    return _fernet().encrypt(plaintext).decode()


def decrypt_secret(token: str) -> bytes:
    """Decrypt a stored secret."""
    try:
        return _fernet().decrypt(token.encode())
    except InvalidToken:
        # A row written before encryption existed, or a rotated key.
        logger.error("Stored secret could not be decrypted with the current key.")
        raise EncryptionUnavailable("stored secret is not readable with the current key")


def is_configured() -> bool:
    """True when a usable encryption key is present."""
    try:
        _fernet()
        return True
    except EncryptionUnavailable:
        return False
