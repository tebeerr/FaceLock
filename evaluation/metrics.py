"""
evaluation/metrics.py
======================
Biometric performance metrics: FAR, FRR, EER.

Definitions:
  FAR (False Acceptance Rate) = FP / (FP + TN)
      Fraction of imposter attempts incorrectly accepted.
  FRR (False Rejection Rate)  = FN / (FN + TP)
      Fraction of genuine attempts incorrectly rejected.
  EER (Equal Error Rate)      = threshold where FAR ≈ FRR.
      Lower EER → better system discrimination.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class BiometricMetrics:
    far:              float
    frr:              float
    eer:              float
    threshold_at_eer: float
    n_genuine:        int
    n_imposter:       int

    def report(self) -> str:
        lines = [
            "Biometric Evaluation Report",
            "=" * 40,
            f"  Genuine samples   : {self.n_genuine}",
            f"  Imposter samples  : {self.n_imposter}",
            f"  FAR @ EER thr.    : {self.far:.4f}  ({self.far * 100:.2f}%)",
            f"  FRR @ EER thr.    : {self.frr:.4f}  ({self.frr * 100:.2f}%)",
            f"  EER               : {self.eer:.4f}  ({self.eer * 100:.2f}%)",
            f"  Threshold @ EER   : {self.threshold_at_eer:.4f}",
            "=" * 40,
        ]
        return "\n".join(lines)


def compute_far_frr(
    genuine_distances:  list[float],
    imposter_distances: list[float],
    thresholds:         list[float],
) -> tuple[list[float], list[float]]:
    """Return (far_list, frr_list) at each threshold value."""
    n_g = len(genuine_distances)
    n_i = len(imposter_distances)
    far_list, frr_list = [], []

    for t in thresholds:
        # Imposters with distance < threshold are falsely accepted
        fa = sum(1 for d in imposter_distances if d < t)
        # Genuine users with distance >= threshold are falsely rejected
        fr = sum(1 for d in genuine_distances if d >= t)
        far_list.append(fa / n_i if n_i else 0.0)
        frr_list.append(fr / n_g if n_g else 0.0)

    return far_list, frr_list


def compute_eer(
    genuine_distances:  list[float],
    imposter_distances: list[float],
    n_thresholds:       int = 500,
) -> BiometricMetrics:
    """
    Find EER by sweeping thresholds between min and max observed distance.
    EER is the point where |FAR - FRR| is minimised.
    """
    all_d      = genuine_distances + imposter_distances
    thresholds = np.linspace(min(all_d), max(all_d), n_thresholds).tolist()

    far_list, frr_list = compute_far_frr(genuine_distances, imposter_distances, thresholds)

    diffs = [abs(f - r) for f, r in zip(far_list, frr_list)]
    idx   = int(np.argmin(diffs))
    eer   = (far_list[idx] + frr_list[idx]) / 2.0

    return BiometricMetrics(
        far=far_list[idx],
        frr=frr_list[idx],
        eer=eer,
        threshold_at_eer=thresholds[idx],
        n_genuine=len(genuine_distances),
        n_imposter=len(imposter_distances),
    )
