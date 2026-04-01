"""
config.py
==========
Centralized configuration for FaceLock.
Edit this file to change system-wide settings.
"""

# -- Paths ---------------------------------------------------------------------
DB_PATH       = "data/facelock.db"
KEY_PATH      = "data/facelock.key"
LOG_PATH      = "logs/activity.log"

# -- Face Recognition ----------------------------------------------------------
DEFAULT_THRESHOLD     = 0.45
MIN_THRESHOLD         = 0.30
MAX_THRESHOLD         = 0.65
ENROLLMENT_FRAMES     = 5

# -- Background Service --------------------------------------------------------
INACTIVITY_TIMEOUT    = 60
SERVICE_POLL_INTERVAL = 1

# -- UI ------------------------------------------------------------------------
APP_TITLE     = "FaceLock -- Biometric Authentication"
APP_ICON      = "\U0001f510"
DEFAULT_USER  = "student_user"

# -- Privacy -------------------------------------------------------------------
STORE_RAW_IMAGES = False
CLOUD_UPLOAD     = False
