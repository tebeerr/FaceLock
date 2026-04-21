"""
facelock.py — CLI adapter for GuardianUseCase.
Usage:
    python facelock.py
    python facelock.py --user my_name
    python facelock.py --user my_name --silent
"""

import argparse
import ctypes
import sys
import time
from datetime import datetime

import cv2
import face_recognition

sys.stdout.reconfigure(encoding="utf-8")

from application.guardian_usecase import GuardianUseCase
from domain.entities import AuditEvent
from infrastructure.repositories import SQLiteAuditRepository, SQLiteEmbeddingRepository
from config import (
    DEFAULT_USER, MATCH_THRESHOLD, NO_FACE_TIMEOUT,
    POLL_INTERVAL_MS, SHOW_WINDOW, WRONG_FACE_LIMIT,
)


def _lock(reason: str, uc: GuardianUseCase, username: str) -> None:
    print(f"\n[FACELOCK] LOCKING SESSION — {reason}")
    uc.log(AuditEvent(username, f"SESSION_LOCKED:{reason}",
                      True, datetime.now(), "system"))
    ctypes.windll.user32.LockWorkStation()
    sys.exit(0)


def run_guardian(username: str, show_window: bool = SHOW_WINDOW) -> None:
    uc = GuardianUseCase(
        embeddings=SQLiteEmbeddingRepository(),
        audit=SQLiteAuditRepository(),
        threshold=MATCH_THRESHOLD,
        wrong_face_limit=WRONG_FACE_LIMIT,
        no_face_timeout=NO_FACE_TIMEOUT,
    )

    try:
        known_vector = uc.load_embedding(username)
    except FileNotFoundError:
        print(f"[FACELOCK] User '{username}' is not enrolled.")
        print(f"[FACELOCK]    Run: python enroll.py --user {username}")
        sys.exit(1)

    print(f"\n[FACELOCK] Loaded profile for '{username}'")
    print("[FACELOCK] Guardian loop started. Press Q to exit.\n")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[FACELOCK] Cannot open webcam.")
        sys.exit(1)

    uc.log(AuditEvent(username, "GUARDIAN_STARTED", True, datetime.now(), "system"))

    last_face_time   = time.time()
    wrong_face_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        rgb       = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        locations = face_recognition.face_locations(rgb)
        encodings = face_recognition.face_encodings(rgb, locations)
        now       = time.time()

        if not encodings:
            elapsed   = now - last_face_time
            remaining = max(0.0, NO_FACE_TIMEOUT - elapsed)

            if show_window:
                cv2.putText(frame, f"No face — locking in {remaining:.1f}s",
                            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                cv2.imshow("FaceLock — Guardian", frame)
                if cv2.waitKey(POLL_INTERVAL_MS) & 0xFF in (ord("q"), 27):
                    break

            if elapsed >= NO_FACE_TIMEOUT:
                cap.release()
                cv2.destroyAllWindows()
                _lock("no_face_timeout", uc, username)
            continue

        last_face_time = now
        matched        = False

        for i, enc in enumerate(encodings):
            is_match, distance = uc.check_frame(known_vector, [enc])

            if is_match:
                matched          = True
                wrong_face_count = 0
                color            = (0, 255, 0)
                label            = f"{username} ({(1 - distance) * 100:.1f}%)"
            else:
                wrong_face_count += 1
                color             = (0, 0, 255)
                label             = f"Unknown ({(1 - distance) * 100:.1f}%)"

            if show_window and i < len(locations):
                top, right, bottom, left = locations[i]
                cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                cv2.rectangle(frame, (left, bottom - 30), (right, bottom), color, -1)
                cv2.putText(frame, label, (left + 4, bottom - 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        if wrong_face_count >= WRONG_FACE_LIMIT:
            cap.release()
            cv2.destroyAllWindows()
            _lock("wrong_face_detected", uc, username)

        if show_window:
            status = ("Authorized" if matched
                      else f"Wrong face ({wrong_face_count}/{WRONG_FACE_LIMIT})")
            cv2.putText(frame, status, (10, frame.shape[0] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                        (0, 255, 0) if matched else (0, 140, 255), 2)
            cv2.imshow("FaceLock — Guardian", frame)
            if cv2.waitKey(POLL_INTERVAL_MS) & 0xFF in (ord("q"), 27):
                break

    cap.release()
    cv2.destroyAllWindows()
    uc.log(AuditEvent(username, "GUARDIAN_STOPPED", True, datetime.now(), "system"))
    print("[FACELOCK] Guardian stopped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FaceLock — Guardian Loop")
    parser.add_argument("--user",   default=DEFAULT_USER)
    parser.add_argument("--silent", action="store_true")
    args = parser.parse_args()
    run_guardian(args.user, show_window=not args.silent)
