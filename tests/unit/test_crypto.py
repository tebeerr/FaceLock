import pytest
from infrastructure.crypto import encrypt, decrypt, load_or_create_key


@pytest.fixture
def key(tmp_path):
    return load_or_create_key(tmp_path / "test.key")


def test_key_is_32_bytes(key):
    assert len(key) == 32


def test_encrypt_decrypt_roundtrip(key):
    plaintext = b"biometric embedding payload"
    assert decrypt(key, encrypt(key, plaintext)) == plaintext


def test_nonce_is_random_per_encryption(key):
    ct1 = encrypt(key, b"same")
    ct2 = encrypt(key, b"same")
    assert ct1 != ct2


def test_tampered_ciphertext_raises(key):
    ct = bytearray(encrypt(key, b"data"))
    ct[-1] ^= 0xFF
    with pytest.raises(Exception):
        decrypt(key, bytes(ct))


def test_load_creates_key_file(tmp_path):
    p = tmp_path / "sub" / "k.bin"
    assert not p.exists()
    load_or_create_key(p)
    assert p.exists()


def test_load_is_idempotent(tmp_path):
    p  = tmp_path / "k.bin"
    k1 = load_or_create_key(p)
    k2 = load_or_create_key(p)
    assert k1 == k2


def test_wrong_key_size_raises(tmp_path):
    p = tmp_path / "bad.bin"
    p.write_bytes(b"\x00" * 16)  # 128-bit — not AES-256
    with pytest.raises(ValueError, match="AES-256"):
        load_or_create_key(p)
