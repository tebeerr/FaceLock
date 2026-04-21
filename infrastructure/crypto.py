"""
infrastructure/crypto.py
=========================
AES-256-GCM authenticated encryption.
Key: 32 raw bytes (256 bits). Nonce: 12 bytes random per message.
Ciphertext layout: nonce(12) || ciphertext || GCM-tag(16)
"""

import os
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_NONCE_SIZE = 12  # 96-bit nonce, NIST recommended for GCM
_KEY_SIZE   = 32  # 256-bit key


def load_or_create_key(path: Path) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        key = os.urandom(_KEY_SIZE)
        path.write_bytes(key)
        print("[CRYPTO] New AES-256-GCM key generated.")
    key = path.read_bytes()
    if len(key) != _KEY_SIZE:
        raise ValueError(
            f"Key at {path} is {len(key)} bytes — expected {_KEY_SIZE} (AES-256). "
            "Run migrate_key.py to upgrade from Fernet."
        )
    return key


def encrypt(key: bytes, plaintext: bytes) -> bytes:
    nonce = os.urandom(_NONCE_SIZE)
    ct    = AESGCM(key).encrypt(nonce, plaintext, None)
    return nonce + ct  # nonce || ciphertext+GCM-tag


def decrypt(key: bytes, data: bytes) -> bytes:
    nonce, ct = data[:_NONCE_SIZE], data[_NONCE_SIZE:]
    return AESGCM(key).decrypt(nonce, ct, None)
