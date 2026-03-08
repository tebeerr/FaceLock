# Secure key storage
# Handles AES encryption key generation and secure storage
from cryptography.fernet import Fernet
import os

KEY_PATH = "profiles/secret.key"

def generate_key():
    """Generate a new encryption key and save it."""
    os.makedirs("profiles", exist_ok=True)
    key = Fernet.generate_key()
    with open(KEY_PATH, "wb") as f:
        f.write(key)
    print("[KEY MANAGER] New encryption key generated and saved.")
    return key

def load_key():
    """Load existing key, or generate one if it doesn't exist."""
    if not os.path.exists(KEY_PATH):
        print("[KEY MANAGER] No key found, generating a new one...")
        return generate_key()
    with open(KEY_PATH, "rb") as f:
        return f.read()

def get_cipher():
    """Return a ready-to-use Fernet cipher."""
    return Fernet(load_key())