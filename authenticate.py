"""
authenticate.py — CLI adapter for AuthenticateUseCase.
Usage:
    python authenticate.py
    python authenticate.py --user my_name
"""

import argparse
import sys

import cv2
import face_recognition

sys.stdout.reconfigure(encoding="utf-8")

from application.authenticate_usecase import AuthenticateUseCase
from infrastructure.repositories import SQLiteAuditRepository, SQLiteEmbeddingRepository
from config import AUTH_CORRECT_NEEDED, AUTH_MAX_ATTEMPTS, DEFAULT_USER, MATCH_THRESHOLD


def authenticate_user(username: str) -> bool:
    embeddings = SQLiteEmbeddingRepository()
    audit      = SQLiteAuditRepository()
    uc         = AuthenticateUseCase(embeddings, audit, MATCH_THRESHOLD)

    if embeddings.find(username) is None:
        print(f"[AUTH] User '{username}' is not enrolled.")
        print(f"[AUTH]    Run: python enroll.py --user {username}")
        return False

    print(f"\n[AUTH] Authenticating '{username}'... Look at the camera.")
    print("[AUTH] Press Q to cancel.\n")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[AUTH] Cannot open webcam.")
        return False

    correct_streak = 0
    attempts       = 0
    authenticated  = False

    while attempts < AUTH_MAX_ATTEMPTS:
        ret, frame = cap.read()
        if not ret:
            continue

        rgb       = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        locations = face_recognition.face_locations(rgb)
        encodings = face_recognition.face_encodings(rgb, locations)
        color     = (0, 0, 255)

        for enc in encodings:
            result = uc.execute(username, enc, auth_type="genuine")

            if result.success:
                correct_streak += 1
                color = (0, 255, 0)
                label = f"Verifying... {correct_streak}/{AUTH_CORRECT_NEEDED}"
                print(f"  Match ({result.confidence:.1f}%) — streak {correct_streak}/{AUTH_CORRECT_NEEDED}")
            else:
                correct_streak = 0
                label = f"Not recognized ({result.confidence:.1f}%)"

            for (top, right, bottom, left) in locations:
                cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                cv2.putText(frame, label, (left, top - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        if correct_streak >= AUTH_CORRECT_NEEDED:
            authenticated = True
            break

        cv2.putText(
            frame,
            f"Attempt {attempts + 1}/{AUTH_MAX_ATTEMPTS} | Streak: {correct_streak}/{AUTH_CORRECT_NEEDED}",
            (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1,
        )
        cv2.imshow(f"FaceLock — Authenticate ({username})", frame)
        if cv2.waitKey(100) & 0xFF in (ord("q"), 27):
            print("\n[AUTH] Cancelled.")
            break

        attempts += 1

    cap.release()
    cv2.destroyAllWindows()

    if authenticated:
        print(f"\n[AUTH] Identity verified — Welcome back, {username}!")
    else:
        print(f"\n[AUTH] Authentication failed after {attempts} attempts.")

    return authenticated


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FaceLock — Authenticate")
    parser.add_argument("--user", default=DEFAULT_USER)
    args = parser.parse_args()
    sys.exit(0 if authenticate_user(args.user) else 1)
