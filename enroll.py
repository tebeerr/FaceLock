"""
enroll.py — CLI adapter for EnrollUseCase.
Usage:
    python enroll.py
    python enroll.py --user my_name
    python enroll.py --user my_name --role admin
"""

import argparse
import sys

import cv2
import face_recognition

sys.stdout.reconfigure(encoding="utf-8")

from application.enroll_usecase import EnrollUseCase
from domain.entities import Role
from infrastructure.repositories import (
    SQLiteAuditRepository,
    SQLiteEmbeddingRepository,
    SQLiteUserRepository,
)
from config import DEFAULT_USER, ENROLLMENT_FRAMES, SHOW_WINDOW


def enroll_user(username: str, role: Role = Role.USER) -> bool:
    uc = EnrollUseCase(
        users=SQLiteUserRepository(),
        embeddings=SQLiteEmbeddingRepository(),
        audit=SQLiteAuditRepository(),
    )

    if uc.is_enrolled(username):
        print(f"[ENROLL] User '{username}' is already enrolled.")
        if input("  Overwrite? (y/N): ").strip().lower() != "y":
            print("[ENROLL] Cancelled.")
            return False
        uc.delete(username)
        print("[ENROLL] Old profile deleted. Re-enrolling...")

    print(f"\n[ENROLL] Starting enrollment for '{username}'")
    print(f"[ENROLL] Capturing {ENROLLMENT_FRAMES} frames — look at the camera.")
    print("[ENROLL] Press Q to cancel.\n")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ENROLL] Cannot open webcam.")
        return False

    collected: list = []
    attempts        = 0

    while len(collected) < ENROLLMENT_FRAMES and attempts < 300:
        ret, frame = cap.read()
        if not ret:
            attempts += 1
            continue

        rgb       = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        locations = face_recognition.face_locations(rgb)
        encodings = face_recognition.face_encodings(rgb, locations)

        if encodings:
            collected.append(encodings[0])
            print(f"  Captured frame {len(collected)}/{ENROLLMENT_FRAMES}")
            if SHOW_WINDOW:
                for (top, right, bottom, left) in locations:
                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                cv2.putText(frame, f"Capturing {len(collected)}/{ENROLLMENT_FRAMES}",
                            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        elif SHOW_WINDOW:
            cv2.putText(frame, "No face detected — adjust position",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        if SHOW_WINDOW:
            cv2.imshow(f"FaceLock — Enrollment ({username})", frame)
            if cv2.waitKey(100) & 0xFF in (ord("q"), 27):
                print("\n[ENROLL] Cancelled.")
                cap.release()
                cv2.destroyAllWindows()
                return False

        attempts += 1

    cap.release()
    cv2.destroyAllWindows()

    if len(collected) < ENROLLMENT_FRAMES:
        print(f"\n[ENROLL] Only captured {len(collected)} frames. Try again.")
        return False

    ok = uc.execute(username, collected, role=role)
    if ok:
        print(f"\n[ENROLL] '{username}' enrolled successfully (role={role.value}).")
        print("[ENROLL] Embedding stored with AES-256-GCM encryption.")
    return ok


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FaceLock — Enroll")
    parser.add_argument("--user", default=DEFAULT_USER)
    parser.add_argument("--role", default="user", choices=["admin", "user", "readonly"])
    args = parser.parse_args()
    sys.exit(0 if enroll_user(args.user, Role(args.role)) else 1)
