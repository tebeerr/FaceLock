"""
enroll.py
==========
FaceLock enrollment script.
Run once to register your face. No Streamlit needed.

Usage:
    python enroll.py
    python enroll.py --user my_name
"""

import cv2
import face_recognition
import numpy as np
import argparse
import sys
from modules.database import DatabaseManager
from config import ENROLLMENT_FRAMES, DEFAULT_USER, SHOW_WINDOW


def enroll_user(username: str) -> bool:
    """
    Capture ENROLLMENT_FRAMES face embeddings from webcam,
    average them, and store the result encrypted in SQLite.

    Returns True on success, False on failure.
    """
    db = DatabaseManager()

    if db.is_enrolled(username):
        print(f"[ENROLL] ⚠️  User '{username}' is already enrolled.")
        overwrite = input("  Overwrite? (y/N): ").strip().lower()
        if overwrite != 'y':
            print("[ENROLL] Cancelled.")
            return False
        db.delete_user(username)
        print(f"[ENROLL] Old profile deleted. Re-enrolling...")

    print(f"\n[ENROLL] Starting enrollment for '{username}'")
    print(f"[ENROLL] Will capture {ENROLLMENT_FRAMES} frames. Look at the camera.")
    print(f"[ENROLL] Press Q to cancel.\n")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ENROLL] ❌ Cannot open webcam.")
        return False

    embeddings_collected = []
    frame_count = 0
    attempts = 0
    MAX_ATTEMPTS = 300  # safety exit after 30 seconds at 10fps

    while len(embeddings_collected) < ENROLLMENT_FRAMES and attempts < MAX_ATTEMPTS:
        ret, frame = cap.read()
        if not ret:
            attempts += 1
            continue

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        locations = face_recognition.face_locations(rgb)
        encodings = face_recognition.face_encodings(rgb, locations)

        if encodings:
            embeddings_collected.append(encodings[0])
            frame_count += 1
            progress = f"  Captured frame {frame_count}/{ENROLLMENT_FRAMES}"
            print(progress)

            if SHOW_WINDOW:
                for (top, right, bottom, left) in locations:
                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                label = f"Capturing {frame_count}/{ENROLLMENT_FRAMES}"
                cv2.putText(frame, label, (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        else:
            if SHOW_WINDOW:
                cv2.putText(frame, "No face detected — adjust position", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        if SHOW_WINDOW:
            cv2.imshow(f"FaceLock — Enrollment ({username})", frame)
            key = cv2.waitKey(100) & 0xFF
            if key == ord('q') or key == 27:
                print("\n[ENROLL] Cancelled by user.")
                cap.release()
                cv2.destroyAllWindows()
                return False

        attempts += 1

    cap.release()
    cv2.destroyAllWindows()

    if len(embeddings_collected) < ENROLLMENT_FRAMES:
        print(f"\n[ENROLL] ❌ Only captured {len(embeddings_collected)} frames. Try again.")
        return False

    # Average all captured embeddings for a stable representation
    avg_embedding = np.mean(embeddings_collected, axis=0)

    success = db.store_embedding(username, avg_embedding)
    db.log_event(username, "ENROLLED", success=success)

    if success:
        print(f"\n[ENROLL] ✅ '{username}' enrolled successfully.")
        print(f"[ENROLL] Embedding stored encrypted in data/facelock.db")
        return True
    else:
        print(f"\n[ENROLL] ❌ Failed to store embedding.")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FaceLock — Enroll a user face")
    parser.add_argument("--user", default=DEFAULT_USER,
                        help=f"Username to enroll (default: {DEFAULT_USER})")
    args = parser.parse_args()

    ok = enroll_user(args.user)
    sys.exit(0 if ok else 1)
