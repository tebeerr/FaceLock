"""
evaluation/evaluate.py
========================
Real biometric evaluation using live webcam — Option A.

Procedure:
  1. Captures N genuine samples  (enrolled user at camera)
  2. Pauses and prompts for a different person
  3. Captures N imposter samples (different person at camera)
  4. Computes FAR / FRR / EER across threshold sweep
  5. Saves full results to report/evaluation_results.json

Usage:
    python evaluation/evaluate.py --user student_user
    python evaluation/evaluate.py --user student_user --genuine 30 --imposter 30
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import cv2
import face_recognition
import numpy as np

# Allow running from project root or from evaluation/
sys.path.insert(0, str(Path(__file__).parent.parent))

from evaluation.metrics import BiometricMetrics, compute_eer
from infrastructure.repositories import SQLiteEmbeddingRepository
from config import MATCH_THRESHOLD

_REPORT_DIR = Path(__file__).parent.parent / "report"


def _capture_distances(
    known_vector: np.ndarray,
    n_samples:    int,
    label:        str,
) -> list[float]:
    cap       = cv2.VideoCapture(0)
    distances: list[float] = []
    attempts  = 0
    max_att   = n_samples * 15

    print(f"\n[EVAL] Capturing {n_samples} {label} samples — look at the camera.")
    print("[EVAL] Press Q to stop early.\n")

    while len(distances) < n_samples and attempts < max_att:
        ret, frame = cap.read()
        if not ret:
            attempts += 1
            continue

        rgb       = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        locations = face_recognition.face_locations(rgb)
        encodings = face_recognition.face_encodings(rgb, locations)

        if encodings:
            dist = float(
                face_recognition.face_distance([known_vector], encodings[0])[0]
            )
            distances.append(dist)
            accepted = dist < MATCH_THRESHOLD
            color    = (0, 255, 0) if accepted else (0, 0, 255)
            print(f"  [{label}] {len(distances):>3}/{n_samples}  "
                  f"dist={dist:.4f}  {'ACCEPT' if accepted else 'REJECT'}")

            for (top, right, bottom, left) in locations:
                cv2.rectangle(frame, (left, top), (right, bottom), color, 2)

        tag = f"{label}  {len(distances)}/{n_samples}"
        cv2.putText(frame, tag, (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                    0.8, (255, 255, 0), 2)
        cv2.imshow(f"FaceLock Evaluation — {label}", frame)

        if cv2.waitKey(200) & 0xFF in (ord("q"), 27):
            break
        attempts += 1

    cap.release()
    cv2.destroyAllWindows()
    return distances


def run_evaluation(user_id: str, n_genuine: int, n_imposter: int) -> None:
    repo   = SQLiteEmbeddingRepository()
    stored = repo.find(user_id)
    if stored is None:
        print(f"[EVAL] User '{user_id}' is not enrolled. Aborting.")
        sys.exit(1)

    known_vector = stored.vector

    # ── Genuine capture ────────────────────────────────────────────────
    genuine_distances = _capture_distances(known_vector, n_genuine, "GENUINE")

    if not genuine_distances:
        print("[EVAL] No genuine samples captured. Aborting.")
        sys.exit(1)

    # ── Imposter capture ───────────────────────────────────────────────
    input(
        f"\n[EVAL] Genuine capture complete ({len(genuine_distances)} samples).\n"
        "       Now have a DIFFERENT person sit at the camera, then press Enter..."
    )

    imposter_distances = _capture_distances(known_vector, n_imposter, "IMPOSTER")

    if not imposter_distances:
        print("[EVAL] No imposter samples captured. Aborting.")
        sys.exit(1)

    # ── Compute metrics ────────────────────────────────────────────────
    metrics: BiometricMetrics = compute_eer(genuine_distances, imposter_distances)

    print(f"\n{metrics.report()}")

    # ── Save results ───────────────────────────────────────────────────
    _REPORT_DIR.mkdir(exist_ok=True)
    result = {
        "user_id":               user_id,
        "timestamp":             datetime.now().isoformat(),
        "configured_threshold":  MATCH_THRESHOLD,
        "n_genuine":             len(genuine_distances),
        "n_imposter":            len(imposter_distances),
        "genuine_distances":     genuine_distances,
        "imposter_distances":    imposter_distances,
        "far":                   metrics.far,
        "frr":                   metrics.frr,
        "eer":                   metrics.eer,
        "threshold_at_eer":      metrics.threshold_at_eer,
    }
    out = _REPORT_DIR / "evaluation_results.json"
    out.write_text(json.dumps(result, indent=2))
    print(f"\n[EVAL] Results saved → {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FaceLock — Biometric Evaluation")
    parser.add_argument("--user",     required=True, help="Enrolled username to evaluate")
    parser.add_argument("--genuine",  type=int, default=20, help="Genuine sample count")
    parser.add_argument("--imposter", type=int, default=20, help="Imposter sample count")
    args = parser.parse_args()
    run_evaluation(args.user, args.genuine, args.imposter)
