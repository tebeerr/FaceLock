"""
facelock.py
============
FaceLock Guardian Loop — the core of the system.
Watches webcam continuously. Locks Windows if:
  - No face detected for NO_FACE_TIMEOUT seconds
  - Wrong face detected for WRONG_FACE_LIMIT consecutive frames

Equivalent to teja0508's lock_unlock_face_recognition.py but:
  - Uses deep embeddings instead of LBPH
  - Reads from encrypted SQLite instead of trainer.yml
  - No hardcoded paths

Usage:
    python facelock.py
    python facelock.py --user my_name
    python facelock.py --user my_name --silent   (no webcam window)
"""

import cv2
import face_recognition
import ctypes
import sys
import time
import argparse
from modules.database import DatabaseManager
from config import (
    MATCH_THRESHOLD, NO_FACE_TIMEOUT, WRONG_FACE_LIMIT,
    POLL_INTERVAL_MS, SHOW_WINDOW, DEFAULT_USER
)


def lock_workstation(reason: str, db: DatabaseManager, username: str):
    """Lock the Windows session and log the event."""
    print(f"\n[FACELOCK] 🔒 LOCKING SESSION — Reason: {reason}")
    db.log_event(username, f"SESSION_LOCKED:{reason}", success=True)
    ctypes.windll.user32.LockWorkStation()
    sys.exit(0)


def run_guardian(username: str, show_window: bool = SHOW_WINDOW):
    """
    Main guardian loop.
    Mirrors teja0508's while-True loop with time-based lock,
    but uses cosine distance on deep embeddings.
    """
    db = DatabaseManager()

    # Load known embedding from encrypted DB
    try:
        known_embedding = db.get_embedding(username)
    except FileNotFoundError:
        print(f"[FACELOCK] ❌ User '{username}' is not enrolled.")
        print(f"[FACELOCK]    Run: python enroll.py --user {username}")
        sys.exit(1)

    print(f"\n[FACELOCK] ✅ Loaded profile for '{username}'")
    print(f"[FACELOCK] 🔍 Guardian loop started. Press Q to exit.\n")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[FACELOCK] ❌ Cannot open webcam.")
        sys.exit(1)

    db.log_event(username, "GUARDIAN_STARTED", success=True)

    last_face_time = time.time()   # Track when we last saw any face
    wrong_face_count = 0           # Count consecutive wrong-face frames
    correct_face_count = 0         # For display feedback only

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        locations = face_recognition.face_locations(rgb)
        encodings = face_recognition.face_encodings(rgb, locations)

        now = time.time()

        # ── No face detected ──────────────────────────────────────────────────
        if not encodings:
            elapsed = now - last_face_time
            remaining = max(0, NO_FACE_TIMEOUT - elapsed)

            if show_window:
                label = f"No face — locking in {remaining:.1f}s"
                cv2.putText(frame, label, (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                cv2.imshow("FaceLock — Guardian", frame)
                if cv2.waitKey(POLL_INTERVAL_MS) & 0xFF in (ord('q'), 27):
                    break

            if elapsed >= NO_FACE_TIMEOUT:
                cap.release()
                cv2.destroyAllWindows()
                lock_workstation("no_face_timeout", db, username)
            continue

        # ── Face(s) detected — check identity ─────────────────────────────────
        last_face_time = now  # Reset the no-face timer
        matched = False

        for i, enc in enumerate(encodings):
            distance = face_recognition.face_distance([known_embedding], enc)[0]
            is_match = distance < MATCH_THRESHOLD

            if is_match:
                matched = True
                correct_face_count += 1
                wrong_face_count = 0
                color = (0, 255, 0)
                label = f"{username} ({(1 - distance) * 100:.1f}%)"
            else:
                wrong_face_count += 1
                color = (0, 0, 255)
                label = f"Unknown ({(1 - distance) * 100:.1f}%)"

            if show_window and i < len(locations):
                top, right, bottom, left = locations[i]
                cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                cv2.rectangle(frame, (left, bottom - 30), (right, bottom), color, -1)
                cv2.putText(frame, label, (left + 4, bottom - 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        # ── Wrong face threshold reached ───────────────────────────────────────
        if wrong_face_count >= WRONG_FACE_LIMIT:
            cap.release()
            cv2.destroyAllWindows()
            lock_workstation("wrong_face_detected", db, username)

        # ── Status bar ────────────────────────────────────────────────────────
        if show_window:
            status = "✓ Authorized" if matched else f"⚠ Wrong face ({wrong_face_count}/{WRONG_FACE_LIMIT})"
            cv2.putText(frame, status, (10, frame.shape[0] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                        (0, 255, 0) if matched else (0, 140, 255), 2)
            cv2.imshow("FaceLock — Guardian", frame)
            if cv2.waitKey(POLL_INTERVAL_MS) & 0xFF in (ord('q'), 27):
                break

    cap.release()
    cv2.destroyAllWindows()
    db.log_event(username, "GUARDIAN_STOPPED", success=True)
    print("[FACELOCK] Guardian stopped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FaceLock — Guardian Loop")
    parser.add_argument("--user", default=DEFAULT_USER,
                        help=f"Username to authenticate (default: {DEFAULT_USER})")
    parser.add_argument("--silent", action="store_true",
                        help="Run without showing webcam window")
    args = parser.parse_args()

    run_guardian(args.user, show_window=not args.silent)
