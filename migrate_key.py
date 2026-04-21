"""
migrate_key.py
==============
One-time migration: Fernet (AES-128-CBC) → AES-256-GCM.

Run once after pulling the new infrastructure layer.
Safe to re-run: exits immediately if key is already AES-256-GCM format.

Usage:
    python migrate_key.py
"""

import base64
import os
import pickle
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import DB_PATH, KEY_PATH

KEY = Path(KEY_PATH)
DB  = Path(DB_PATH)


def _is_fernet_key(raw: bytes) -> bool:
    try:
        decoded = base64.urlsafe_b64decode(raw)
        return len(raw) == 44 and len(decoded) == 32
    except Exception:
        return False


def main() -> None:
    if not KEY.exists():
        print("[MIGRATE] No key file found. Nothing to migrate.")
        sys.exit(0)

    raw = KEY.read_bytes()

    if len(raw) == 32:
        print("[MIGRATE] Key is already AES-256-GCM (32 raw bytes). No migration needed.")
        sys.exit(0)

    if not _is_fernet_key(raw):
        print(f"[MIGRATE] Unrecognised key format ({len(raw)} bytes). Aborting.")
        sys.exit(1)

    print("[MIGRATE] Fernet key detected — migrating to AES-256-GCM...")

    from cryptography.fernet import Fernet
    from infrastructure import crypto

    old_cipher = Fernet(raw)
    new_key    = os.urandom(32)

    if not DB.exists():
        print("[MIGRATE] No database found. Writing new key only.")
        KEY.write_bytes(new_key)
        print("[MIGRATE] Done.")
        sys.exit(0)

    with sqlite3.connect(DB) as conn:
        rows = conn.execute(
            "SELECT id, user_id, embedding FROM embeddings"
        ).fetchall()

    print(f"[MIGRATE] Re-encrypting {len(rows)} embedding(s)...")

    new_blobs: list[tuple[bytes, int]] = []
    for row_id, user_id, old_blob in rows:
        try:
            plaintext = old_cipher.decrypt(bytes(old_blob))
            new_blob  = crypto.encrypt(new_key, plaintext)
            new_blobs.append((new_blob, row_id))
            print(f"  [OK] {user_id}")
        except Exception as exc:
            print(f"  [FAIL] {user_id}: {exc}")
            print("[MIGRATE] Aborting — original key unchanged.")
            sys.exit(1)

    with sqlite3.connect(DB) as conn:
        for new_blob, row_id in new_blobs:
            conn.execute(
                "UPDATE embeddings SET embedding=? WHERE id=?", (new_blob, row_id)
            )
        conn.commit()

    backup = KEY.parent / f"facelock_fernet_{datetime.now().strftime('%Y%m%d_%H%M%S')}.key.bak"
    shutil.copy(KEY, backup)
    KEY.write_bytes(new_key)

    print(f"\n[MIGRATE] Migration complete.")
    print(f"  Embeddings re-encrypted : {len(new_blobs)}")
    print(f"  Old key backed up to    : {backup.name}")
    print(f"  New AES-256-GCM key     : {KEY}")


if __name__ == "__main__":
    main()
