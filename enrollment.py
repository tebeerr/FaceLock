"""
enrollment.py (updated)
========================
Face enrollment using SQLite database instead of .enc files.
"""

import cv2
import numpy as np
import face_recognition
from modules.database import DatabaseManager


def enroll_from_frame(username: str, frame_bgr, db: DatabaseManager = None) -> dict:
    """
    Enroll a user from a single captured frame.
    Stores encrypted embedding in SQLite database.
    """
    if db is None:
        db = DatabaseManager()

    rgb       = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    locations = face_recognition.face_locations(rgb)
    encodings = face_recognition.face_encodings(rgb, locations)

    if not encodings:
        db.log_event(username, "ENROLLMENT_FAILED_NO_FACE", success=False)
        return {"success": False, "message": "No face detected. Please try again."}

    embedding = np.array(encodings[0])
    db.enroll_user(username, embedding)

    return {
        "success": True,
        "message": f"'{username}' enrolled and encrypted in database."
    }


def enroll_user_multisample(username: str, frames: list, db: DatabaseManager = None) -> dict:
    """
    Enroll from multiple frames and store the averaged embedding.
    """
    if db is None:
        db = DatabaseManager()

    embeddings = []
    for frame_bgr in frames:
        rgb       = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        locations = face_recognition.face_locations(rgb)
        encodings = face_recognition.face_encodings(rgb, locations)
        if encodings:
            embeddings.append(encodings[0])

    if len(embeddings) == 0:
        db.log_event(username, "ENROLLMENT_FAILED_NO_FACE", success=False)
        return {"success": False, "message": "No face detected in any frame.", "samples": 0}

    avg_embedding = np.mean(embeddings, axis=0)
    db.enroll_user(username, avg_embedding)

    return {
        "success": True,
        "message": f"Enrolled from {len(embeddings)} frames.",
        "samples": len(embeddings)
    }
