"""
authenticate.py
================
FaceLock unlock script.
Run after the session is unlocked (or to test authentication).
Attempts to verify your face against the stored encrypted embedding.

Usage:
    python authenticate.py
    python authenticate.py --user my_name
"""

import cv2
import face_recognition
import numpy as np
import sys
import argparse
from modules.database import DatabaseManager
from config import MATCH_THRESHOLD, AUTH_MAX_ATTEMPTS, AUTH_CORRECT_NEEDED, DEFAULT_USER


def authenticate_user(username: str) -> bool:
    """
    Open webcam, attempt to match the live face against the stored embedding.
    Requires AUTH_CORRECT_NEEDED consecutive matching frames to confirm identity.

    Returns True if authenticated, False otherwise.
    """
    db = DatabaseManager()

    try:
        known_embedding = db.get_embedding(username)
    except FileNotFoundError:
        print(f"[AUTH] ❌ User '{username}' is not enrolled.")
        print(f"[AUTH]    Run: python enroll.py --user {username}")
        return False

    print(f"\n[AUTH] Authenticating '{username}'... Look at the camera.")
    print(f"[AUTH] Press Q to cancel.\n")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[AUTH] ❌ Cannot open webcam.")
        return False

    correct_streak = 0
    attempts = 0
    authenticated = False

    while attempts < AUTH_MAX_ATTEMPTS:
        ret, frame = cap.read()
        if not ret:
            continue

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        locations = face_recognition.face_locations(rgb)
        encodings = face_recognition.face_encodings(rgb, locations)

        color = (0, 0, 255)  # Red by default

        for enc in encodings:
            distance = face_recognition.face_distance([known_embedding], enc)[0]

            if distance < MATCH_THRESHOLD:
                correct_streak += 1
                color = (0, 255, 0)
                label = f"Verifying... {correct_streak}/{AUTH_CORRECT_NEEDED}"
                print(f"  ✓ Match ({(1-distance)*100:.1f}%) — streak {correct_streak}/{AUTH_CORRECT_NEEDED}")
            else:
                correct_streak = 0
                label = f"Not recognized ({(1-distance)*100:.1f}%)"

            for (top, right, bottom, left) in locations:
                cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                cv2.putText(frame, label, (left, top - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        if correct_streak >= AUTH_CORRECT_NEEDED:
            authenticated = True
            break

        progress = f"Attempt {attempts+1}/{AUTH_MAX_ATTEMPTS} | Streak: {correct_streak}/{AUTH_CORRECT_NEEDED}"
        cv2.putText(frame, progress, (10, frame.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)
        cv2.imshow(f"FaceLock — Authenticate ({username})", frame)

        if cv2.waitKey(100) & 0xFF in (ord('q'), 27):
            print("\n[AUTH] Cancelled.")
            break

        attempts += 1

    cap.release()
    cv2.destroyAllWindows()

    db.log_event(username, "AUTH_SUCCESS" if authenticated else "AUTH_FAILED",
                 success=authenticated)

    if authenticated:
        print(f"\n[AUTH] ✅ Identity verified — Welcome back, {username}!")
    else:
        print(f"\n[AUTH] ❌ Authentication failed after {attempts} attempts.")

    return authenticated


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FaceLock — Authenticate")
    parser.add_argument("--user", default=DEFAULT_USER,
                        help=f"Username to authenticate (default: {DEFAULT_USER})")
    args = parser.parse_args()

    ok = authenticate_user(args.user)
    sys.exit(0 if ok else 1)
