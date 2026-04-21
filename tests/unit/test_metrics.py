import pytest
from evaluation.metrics import compute_eer, compute_far_frr


def test_perfect_separation_gives_low_eer():
    genuine  = [0.10, 0.15, 0.20, 0.12, 0.18]
    imposter = [0.60, 0.65, 0.70, 0.75, 0.80]
    m = compute_eer(genuine, imposter)
    assert m.eer < 0.05


def test_identical_populations_give_high_eer():
    same = [0.4, 0.45, 0.5, 0.4, 0.42]
    m    = compute_eer(same, same)
    assert abs(m.eer - 0.5) < 0.15


def test_far_zero_when_no_imposter_below_threshold():
    genuine  = [0.2, 0.3]
    imposter = [0.7, 0.8]
    far, frr = compute_far_frr(genuine, imposter, [0.5])
    assert far[0] == pytest.approx(0.0)


def test_frr_zero_when_all_genuine_below_threshold():
    genuine  = [0.1, 0.2]
    imposter = [0.8, 0.9]
    far, frr = compute_far_frr(genuine, imposter, [0.5])
    assert frr[0] == pytest.approx(0.0)


def test_threshold_at_eer_within_distance_range():
    genuine  = [0.2, 0.3, 0.25, 0.28]
    imposter = [0.5, 0.55, 0.6, 0.52]
    m        = compute_eer(genuine, imposter)
    all_d    = genuine + imposter
    assert min(all_d) <= m.threshold_at_eer <= max(all_d)


def test_metrics_report_contains_key_fields():
    genuine  = [0.2, 0.3]
    imposter = [0.7, 0.8]
    m        = compute_eer(genuine, imposter)
    report   = m.report()
    for keyword in ("FAR", "FRR", "EER", "Threshold"):
        assert keyword in report


def test_sample_counts_recorded():
    genuine  = [0.1] * 10
    imposter = [0.9] * 5
    m        = compute_eer(genuine, imposter)
    assert m.n_genuine  == 10
    assert m.n_imposter == 5
