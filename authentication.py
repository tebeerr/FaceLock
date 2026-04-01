"""
authentication.py (updated)
============================
Face authentication using SQLite database.
"""

import cv2
import numpy as np
import face_recognition
from modules.database import DatabaseManager


def authenticate_from_frame(username: str, frame_bgr, db: DatabaseManager = None) -> dict:
    """
    Authenticate a user from a captured frame.
    Loads embedding from SQLite, decrypts it, compares with live face.
    """
    if db is None:
        db = DatabaseManager()

    threshold = db.get_threshold(default=0.45)

    known = db.get_embedding(username)
    if known is None:
        return {
            "success"   : False,
            "message"   : f"No profile found for '{username}'. Enroll first.",
            "distance"  : None,
            "confidence": None,
        }

    db.log_event(username, "AUTH_ATTEMPT")

    rgb       = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    locations = face_recognition.face_locations(rgb)
    encodings = face_recognition.face_encodings(rgb, locations)

    if not encodings:
        db.log_event(username, "AUTH_FAILED_NO_FACE", success=False)
        return {
            "success"   : False,
            "message"   : "No face detected. Please try again.",
            "distance"  : None,
            "confidence": None,
        }

    distance = face_recognition.face_distance([known], encodings[0])[0]
    success  = bool(distance < threshold)

    db.log_event(username, "AUTH_RESULT", success=success)

    return {
        "success"   : success,
        "message"   : "Access Granted" if success else "Access Denied",
        "distance"  : round(float(distance), 4),
        "confidence": f"{round((1 - distance) * 100, 1)}%",
    }


def is_enrolled(username: str, db: DatabaseManager = None) -> bool:
    """Quick check if a user has an embedding in the database."""
    if db is None:
        db = DatabaseManager()
    return db.is_enrolled(username)
