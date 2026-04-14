"""
modules/database.py
====================
SQLite database manager for FaceLock.
Stores encrypted face embeddings using AES-256 (Fernet).
Compliant with GDPR Art. 5(1)(f) -- Integrity & confidentiality.
"""

import sqlite3
import pickle
import os
import numpy as np
from datetime import datetime
from cryptography.fernet import Fernet

from config import DB_PATH, KEY_PATH


# -- Key Management ------------------------------------------------------------

def _load_or_create_key() -> bytes:
    """Load the AES key from disk, or generate and save a new one."""
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(KEY_PATH):
        key = Fernet.generate_key()
        with open(KEY_PATH, "wb") as f:
            f.write(key)
        print("[DB] New AES-256 key generated.")
    with open(KEY_PATH, "rb") as f:
        return f.read()

def _get_cipher() -> Fernet:
    return Fernet(_load_or_create_key())


# -- DatabaseManager Class -----------------------------------------------------

class DatabaseManager:
    """
    Handles all SQLite operations for FaceLock.
    All embeddings are encrypted before storage (Privacy by Design).
    """

    def __init__(self):
        os.makedirs("data", exist_ok=True)
        self.db_path = DB_PATH
        self.cipher  = _get_cipher()
        self.create_tables()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    # -- Schema ----------------------------------------------------------------

    def create_tables(self):
        """Initialize the database schema."""
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id     TEXT PRIMARY KEY,
                    created_at  TEXT NOT NULL,
                    updated_at  TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     TEXT NOT NULL,
                    embedding   BLOB NOT NULL,
                    created_at  TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS auth_logs (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     TEXT NOT NULL,
                    event       TEXT NOT NULL,
                    success     INTEGER,
                    timestamp   TEXT NOT NULL
                )
            """)
            conn.commit()
        print("[DB] Tables initialized.")

    # -- Enrollment ------------------------------------------------------------

    def enroll_user(self, user_id: str, embedding: np.ndarray) -> bool:
        """
        Add or update a user with their face embedding.
        Raw embedding is encrypted before storage -- no plaintext biometric data.
        Returns True on success.
        """
        now = datetime.now().isoformat()
        encrypted_blob = self.cipher.encrypt(pickle.dumps(embedding))

        with self._connect() as conn:
            conn.execute("""
                INSERT INTO users (user_id, created_at, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET updated_at=excluded.updated_at
            """, (user_id, now, now))
            conn.execute("DELETE FROM embeddings WHERE user_id = ?", (user_id,))
            conn.execute("""
                INSERT INTO embeddings (user_id, embedding, created_at)
                VALUES (?, ?, ?)
            """, (user_id, encrypted_blob, now))
            conn.commit()

        self.log_event(user_id, "ENROLLMENT", success=True)
        print(f"[DB] User '{user_id}' enrolled and embedding encrypted.")
        return True

    # -- Retrieval -------------------------------------------------------------

    def store_embedding(self, username: str, embedding: np.ndarray) -> bool:
        """Alias for enroll_user — stores encrypted embedding."""
        return self.enroll_user(username, embedding)

    def get_embedding(self, user_id: str) -> np.ndarray:
        """
        Retrieve and decrypt the stored embedding for a user.
        Raises FileNotFoundError if user not found.
        """
        with self._connect() as conn:
            row = conn.execute("""
                SELECT embedding FROM embeddings WHERE user_id = ?
            """, (user_id,)).fetchone()

        if row is None:
            raise FileNotFoundError(f"No embedding found for user '{user_id}'")

        decrypted = self.cipher.decrypt(row[0])
        return pickle.loads(decrypted)

    def get_all_users(self) -> list[str]:
        """Return a list of all enrolled user IDs."""
        with self._connect() as conn:
            rows = conn.execute("SELECT user_id FROM users").fetchall()
        return [r[0] for r in rows]

    def is_enrolled(self, user_id: str) -> bool:
        """Check if a user has an embedding stored."""
        with self._connect() as conn:
            row = conn.execute("""
                SELECT 1 FROM embeddings WHERE user_id = ?
            """, (user_id,)).fetchone()
        return row is not None

    # -- Deletion (GDPR Art. 17 -- Right to Erasure) ---------------------------

    def delete_user(self, user_id: str) -> bool:
        """
        Permanently delete all data for a user.
        Satisfies GDPR Article 17 -- Right to Erasure.
        """
        with self._connect() as conn:
            conn.execute("DELETE FROM embeddings WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM auth_logs WHERE user_id = ?", (user_id,))
            conn.commit()

        print(f"[DB] All data for '{user_id}' permanently deleted.")
        return True

    # -- Logging ---------------------------------------------------------------

    def log_event(self, user_id: str, event: str, success: bool = None):
        """Record an authentication event to the database."""
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO auth_logs (user_id, event, success, timestamp)
                VALUES (?, ?, ?, ?)
            """, (user_id, event, int(success) if success is not None else None,
                  datetime.now().isoformat()))
            conn.commit()

    def get_logs(self, user_id: str = None, limit: int = 50) -> list[dict]:
        """Retrieve authentication logs, optionally filtered by user."""
        with self._connect() as conn:
            if user_id:
                rows = conn.execute("""
                    SELECT user_id, event, success, timestamp
                    FROM auth_logs WHERE user_id = ?
                    ORDER BY timestamp DESC LIMIT ?
                """, (user_id, limit)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT user_id, event, success, timestamp
                    FROM auth_logs
                    ORDER BY timestamp DESC LIMIT ?
                """, (limit,)).fetchall()

        return [
            {"user_id": r[0], "event": r[1],
             "success": bool(r[2]) if r[2] is not None else None,
             "timestamp": r[3]}
            for r in rows
        ]

    # -- Threshold -------------------------------------------------------------

    def set_threshold(self, threshold: float):
        """Store authentication threshold in DB config table."""
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    key   TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            conn.execute("""
                INSERT INTO config (key, value) VALUES ('threshold', ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """, (str(threshold),))
            conn.commit()

    def get_threshold(self, default: float = 0.45) -> float:
        """Retrieve the stored threshold value."""
        with self._connect() as conn:
            try:
                row = conn.execute(
                    "SELECT value FROM config WHERE key='threshold'"
                ).fetchone()
                return float(row[0]) if row else default
            except Exception:
                return default

    # -- Stats -----------------------------------------------------------------

    def get_stats(self) -> dict:
        """Return database statistics for the UI dashboard."""
        with self._connect() as conn:
            total_users   = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            total_auths   = conn.execute("SELECT COUNT(*) FROM auth_logs").fetchone()[0]
            success_auths = conn.execute(
                "SELECT COUNT(*) FROM auth_logs WHERE success=1"
            ).fetchone()[0]
            failed_auths  = conn.execute(
                "SELECT COUNT(*) FROM auth_logs WHERE success=0"
            ).fetchone()[0]

        return {
            "total_users"  : total_users,
            "total_auths"  : total_auths,
            "success_auths": success_auths,
            "failed_auths" : failed_auths,
        }
