"""Sanity checks for the hypothesis-testing helpers (src/analysis/stats_tests.py)."""

import numpy as np
import pandas as pd

from src.analysis import stats_tests as st

rng = np.random.default_rng(0)


def test_bootstrap_ci_contains_estimate():
    a = rng.exponential(100, 500)
    est, low, high = st.bootstrap_ci(a, n_boot=2000)
    assert low < est < high


def test_bootstrap_difference_detects_shift():
    a, b = rng.normal(10, 1, 300), rng.normal(9, 1, 300)
    est, low, high = st.bootstrap_ci(a, b, n_boot=2000)
    assert low > 0 and abs(est - 1) < 0.3


def test_mann_whitney_effect_size_bounds_and_direction():
    a, b = rng.normal(1, 1, 200), rng.normal(0, 1, 200)
    res = st.mann_whitney(a, b, alternative="greater")
    assert res["p_value"] < 0.05 and 0 < res["effect_size"] <= 1


def test_kruskal_no_difference_for_identical_groups():
    data = rng.normal(0, 1, 900)
    res = st.kruskal_wallis({"a": data[:300], "b": data[300:600], "c": data[600:]})
    assert res["p_value"] > 0.01


def test_chi_square_cramers_v_perfect_association():
    table = pd.DataFrame([[50, 0], [0, 50]])
    res = st.chi_square(table)
    assert res["p_value"] < 0.001 and res["effect_size"] > 0.9


def test_holm_never_reduces_p_values():
    p = np.array([0.01, 0.02, 0.03, 0.5])
    assert (st.holm(p) >= p).all()
