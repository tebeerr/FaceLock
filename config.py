# config.py
"""
FaceLock — Centralized Configuration
=====================================
Edit this file to change all system-wide settings.
No other file should contain hardcoded paths or values.
"""

# ── Paths ─────────────────────────────────────────────────────────────────────
DB_PATH             = "data/facelock.db"
KEY_PATH            = "data/facelock.key"
LOG_PATH            = "logs/facelock.log"

# ── Face Recognition ──────────────────────────────────────────────────────────
MATCH_THRESHOLD     = 0.45     # Cosine distance — lower = stricter match
                                # 0.4 = tight (same lighting needed)
                                # 0.5 = relaxed (works across lighting conditions)
ENROLLMENT_FRAMES   = 5        # How many frames to average during enrollment
                                # More frames = more stable embedding

# ── Guardian Loop (facelock.py) ───────────────────────────────────────────────
NO_FACE_TIMEOUT     = 5        # Seconds without a face before locking
                                # Same concept as teja0508's 8-second timeout
WRONG_FACE_LIMIT    = 30       # Consecutive wrong-face frames before locking
                                # Prevents instant lock on single bad frame
POLL_INTERVAL_MS    = 100      # Milliseconds between webcam frames (10 fps)
SHOW_WINDOW         = True     # Show live webcam window during guardian loop
                                # Set False for silent background mode

# ── Authentication ────────────────────────────────────────────────────────────
AUTH_MAX_ATTEMPTS   = 60       # Max frames to try before giving up auth
AUTH_CORRECT_NEEDED = 10       # Consecutive correct frames to confirm identity
                                # Higher = more secure, slower to unlock

# ── Privacy (DO NOT CHANGE) ───────────────────────────────────────────────────
STORE_RAW_IMAGES    = False    # GDPR Art. 5(1)(c) — must always be False
CLOUD_UPLOAD        = False    # Privacy by Design — must always be False

# ── App ───────────────────────────────────────────────────────────────────────
DEFAULT_USER        = "student_user"
APP_NAME            = "FaceLock"
