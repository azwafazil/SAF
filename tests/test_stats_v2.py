"""Tests for bug fixes and new features added in the 2026-06-03 improve-stats PR.

Covers:
  - chi-square GOF (FIX 1)
  - friedman with subject_col (FIX 2)
  - eta_squared effect size (FIX 3)
  - rank_biserial effect size (NEW)
  - power.f with FTestAnovaPower (FIX 4)
  - power.z with NormalIndPower (FIX 5)
  - power with both power and nobs (ERROR)
  - outliers mahalanobis 1 col (FIX 6)
  - cohens_d + hedges_g for Welch t-test (FIX 7)
  - correlate Spearman bootstrap CI (FIX 8)
  - correlate Spearman bootstrap reproducibility with seed (FIX 8)
  - nonparametric friedman errors (shape, group_col, etc.)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from saf_mcp.stats import (
    stat_chi_square,
    stat_compare_groups,
    stat_correlate,
    stat_effect_size,
    stat_nonparametric,
    stat_outliers,
    stat_power,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def saf_root(tmp_path, monkeypatch):
    """SAF sandbox with a study.csv: 60 rows, 3 groups, 2 sex, numeric v1/v2."""
    monkeypatch.setenv("SAF_DATA_ROOT", str(tmp_path))
    df = pd.DataFrame(
        {
            "id": range(1, 61),
            "v1": list(range(60)),
            "v2": [1.0] * 30 + [2.0] * 30,
            "group": (["A"] * 20) + (["B"] * 20) + (["C"] * 20),
            "sex": (["M"] * 30) + (["F"] * 30),
        }
    )
    df.to_csv(tmp_path / "study.csv", index=False)
    return tmp_path / "study.csv"


@pytest.fixture
def two_group_csv(tmp_path, monkeypatch):
    """SAF sandbox with two_group.csv: 2 groups, 50 obs each."""
    monkeypatch.setenv("SAF_DATA_ROOT", str(tmp_path))
    rng = np.random.default_rng(42)
    df = pd.DataFrame(
        {
            "g": (["A"] * 50) + (["B"] * 50),
            "v": np.concatenate([rng.normal(50, 10, 50), rng.normal(55, 10, 50)]),
        }
    )
    df.to_csv(tmp_path / "two_group.csv", index=False)
    return tmp_path / "two_group.csv"


@pytest.fixture
def friedman_csv(tmp_path, monkeypatch):
    """SAF sandbox with friedman.csv: 4 subjects, 3 conditions (long format)."""
    monkeypatch.setenv("SAF_DATA_ROOT", str(tmp_path))
    df = pd.DataFrame(
        {
            "subject": [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4],
            "cond": ["A", "B", "C"] * 4,
            "score": [10, 12, 15, 11, 13, 14, 9, 11, 16, 8, 10, 12],
        }
    )
    df.to_csv(tmp_path / "friedman.csv", index=False)
    return tmp_path / "friedman.csv"


# ---------------------------------------------------------------------------
# FIX 1: chi-square GOF
# ---------------------------------------------------------------------------


def test_chi_square_gof_zero_when_expected_matches_observed(tmp_path, monkeypatch):
    """When expected == observed, chi2 should be 0 and p should be 1.

    Use a balanced 2x2 fixture (no zero cells) so scipy's chisquare can compute.
    """
    monkeypatch.setenv("SAF_DATA_ROOT", str(tmp_path))
    df = pd.DataFrame(
        {
            "a": (["x"] * 30) + (["y"] * 30),
            "b": (["p"] * 15) + (["q"] * 15) + (["p"] * 15) + (["q"] * 15),
        }
    )
    df.to_csv(tmp_path / "balanced.csv", index=False)
    r = stat_chi_square(
        "balanced.csv",
        "a",
        "b",
        test="gof",
        expected=[[15, 15], [15, 15]],
    )
    assert r["ok"] is True
    assert r["result"]["chi2"] == pytest.approx(0.0, abs=1e-9)
    assert r["result"]["p_value"] == pytest.approx(1.0)


def test_chi_square_gof_shape_mismatch(saf_root):
    """Mismatched shape should error, not silently return nan."""
    r = stat_chi_square(
        "study.csv",
        "sex",
        "group",
        test="gof",
        expected=[[30, 30, 30]],  # 1x3, but observed is 2x3
    )
    assert r["ok"] is False
    assert "shape mismatch" in r["error"]["message"]


# ---------------------------------------------------------------------------
# FIX 2: friedman with subject_col
# ---------------------------------------------------------------------------


def test_nonparametric_friedman_long_format_with_subject(friedman_csv):
    """Long format with subject_col should pivot correctly and yield Q, p, n_subjects."""
    r = stat_nonparametric(
        "friedman.csv",
        "score",
        group_col="cond",
        subject_col="subject",
        test="friedman",
    )
    assert r["ok"] is True
    res = r["result"]
    assert res["method"] == "Friedman"
    assert res["k_groups"] == 3
    assert res["n_subjects"] == 4
    assert not np.isnan(res["Q"])
    assert not np.isnan(res["p_value"])


def test_nonparametric_friedman_requires_group_col(saf_root):
    """Friedman without group_col should error cleanly (after data load)."""
    r = stat_nonparametric("study.csv", "v1", test="friedman")
    assert r["ok"] is False
    assert "group_col" in r["error"]["message"]


def test_nonparametric_friedman_requires_3_groups(saf_root, tmp_path, monkeypatch):
    """Friedman with <3 groups should error."""
    monkeypatch.setenv("SAF_DATA_ROOT", str(tmp_path))
    df = pd.DataFrame(
        {
            "subject": [1, 1, 2, 2, 3, 3],
            "cond": ["A", "B"] * 3,
            "score": [10, 12, 11, 13, 9, 11],
        }
    )
    df.to_csv(tmp_path / "small.csv", index=False)
    r = stat_nonparametric(
        "small.csv", "score", group_col="cond", subject_col="subject", test="friedman"
    )
    assert r["ok"] is False
    assert ">= 3 conditions" in r["error"]["message"]


# ---------------------------------------------------------------------------
# FIX 3: eta_squared effect size
# ---------------------------------------------------------------------------


def test_effect_size_eta_squared(saf_root):
    """eta_squared for value_col/group_col should return a value in [0, 1]."""
    r = stat_effect_size(
        kind="eta_squared", file_path="study.csv", var_a="v1", var_b="group"
    )
    assert r["ok"] is True
    assert 0.0 <= r["result"]["value"] <= 1.0
    assert r["result"]["n_groups"] == 3
    assert r["result"]["value_col"] == "v1"
    assert r["result"]["group_col"] == "group"


def test_effect_size_eta_squared_requires_group_col(saf_root):
    """eta_squared without var_b should error."""
    r = stat_effect_size(kind="eta_squared", file_path="study.csv", var_a="v1")
    assert r["ok"] is False
    assert "var_b" in r["error"]["message"]


def test_effect_size_eta_squared_invalid_column(saf_root):
    """eta_squared with non-existent column should error."""
    r = stat_effect_size(
        kind="eta_squared",
        file_path="study.csv",
        var_a="nonexistent",
        var_b="group",
    )
    assert r["ok"] is False
    assert "not in dataset" in r["error"]["message"]


# ---------------------------------------------------------------------------
# NEW: rank_biserial effect size
# ---------------------------------------------------------------------------


def test_effect_size_rank_biserial(two_group_csv):
    """rank_biserial correlation from two samples."""
    import pandas as pd

    df = pd.read_csv(two_group_csv)
    x = df[df.g == "A"]["v"].tolist()
    y = df[df.g == "B"]["v"].tolist()
    r = stat_effect_size(kind="rank_biserial", x=x, y=y)
    assert r["ok"] is True
    assert -1.0 <= r["result"]["value"] <= 1.0
    assert r["result"]["n1"] == 50
    assert r["result"]["n2"] == 50


# ---------------------------------------------------------------------------
# FIX 4 + 5: power f + z tests
# ---------------------------------------------------------------------------


def test_stat_power_f_solve_power():
    """F-test power for one-way ANOVA: f=0.25, n=60, k=3 → ~0.37 power."""
    r = stat_power(test="f", effect_size=0.25, alpha=0.05, nobs=60, df_num=2)
    assert r["ok"] is True
    assert 0.3 < r["result"]["solved_power"] < 0.5
    assert r["result"]["k_groups"] == 3


def test_stat_power_f_solve_nobs():
    """F-test solve_nobs: f=0.25, power=0.8, k=3 → ~158 (matches G*Power)."""
    r = stat_power(test="f", effect_size=0.25, alpha=0.05, power=0.8, df_num=2)
    assert r["ok"] is True
    # G*Power 3.1: f=0.25, k=3, power=0.8, alpha=0.05 → N=159
    assert 150 <= r["result"]["solved_nobs"] <= 170


def test_stat_power_f_df_num_optional_defaults_to_2_groups():
    """F-test power without df_num defaults to k_groups=2 (one-way ANOVA with 2 groups)."""
    r = stat_power(test="f", effect_size=0.5, alpha=0.05, nobs=30)
    assert r["ok"] is True
    # k_groups=2 (one-way ANOVA with 2 groups)
    assert r["result"]["k_groups"] == 2


def test_stat_power_f_df_num_3_groups():
    """F-test power with df_num=2 → k_groups=3."""
    r = stat_power(test="f", effect_size=0.25, alpha=0.05, nobs=60, df_num=2)
    assert r["ok"] is True
    assert r["result"]["k_groups"] == 3


def test_stat_power_z_solve_power():
    """z-test power for two proportions."""
    r = stat_power(test="z", effect_size=0.3, alpha=0.05, nobs=100)
    assert r["ok"] is True
    assert 0.5 < r["result"]["solved_power"] < 0.7


def test_stat_power_z_solve_nobs():
    """z-test solve_nobs: h=0.3, power=0.8 → reasonable sample size."""
    r = stat_power(test="z", effect_size=0.3, alpha=0.05, power=0.8)
    assert r["ok"] is True
    assert 150 <= r["result"]["solved_nobs"] <= 200


def test_stat_power_both_power_and_nobs_errors():
    """Supplying both power and nobs should error."""
    r = stat_power(test="t", effect_size=0.5, power=0.8, nobs=64)
    assert r["ok"] is False
    assert "exactly one" in r["error"]["message"]


# ---------------------------------------------------------------------------
# FIX 6: outliers mahalanobis 1 col
# ---------------------------------------------------------------------------


def test_outliers_mahalanobis_single_column_errors(saf_root):
    """Mahalanobis requires >=2 columns; with 1 should error cleanly."""
    r = stat_outliers("study.csv", ["v1"], method="mahalanobis")
    assert r["ok"] is False
    assert "mahalanobis requires >= 2 columns" in r["error"]["message"]


# ---------------------------------------------------------------------------
# FIX 7: cohens_d + hedges_g for Welch t-test
# ---------------------------------------------------------------------------


def test_compare_groups_welch_includes_cohens_d_and_hedges(two_group_csv):
    """Welch t-test should now also report Cohen's d + Hedges' g."""
    r = stat_compare_groups("two_group.csv", "v", "g", parametric=True, equal_var=False)
    assert r["ok"] is True
    assert r["result"]["method"] == "Welch t-test"
    assert r["result"]["cohens_d"] is not None
    assert r["result"]["hedges_g"] is not None
    # Hedges' g is the small-sample-corrected version, magnitude slightly smaller
    assert abs(r["result"]["hedges_g"]) < abs(r["result"]["cohens_d"])


def test_compare_groups_student_includes_cohens_d(two_group_csv):
    """Student t (equal_var=True) should also include both effect sizes."""
    r = stat_compare_groups("two_group.csv", "v", "g", parametric=True, equal_var=True)
    assert r["ok"] is True
    assert r["result"]["method"] == "Student t"
    assert r["result"]["cohens_d"] is not None
    assert r["result"]["hedges_g"] is not None


# ---------------------------------------------------------------------------
# FIX 8: correlate Spearman bootstrap CI
# ---------------------------------------------------------------------------


def test_correlate_spearman_with_bootstrap(saf_root):
    """Spearman with bootstrap should return a real CI."""
    r = stat_correlate(
        "study.csv", "v1", "v2", method="spearman", bootstrap=200, seed=42
    )
    assert r["ok"] is True
    assert r["result"]["ci95"][0] is not None
    assert r["result"]["ci95"][1] is not None
    assert r["result"]["ci95"][0] < r["result"]["ci95"][1]


def test_correlate_spearman_without_bootstrap_returns_null_ci(saf_root):
    """Spearman without bootstrap (default) returns [None, None]."""
    r = stat_correlate("study.csv", "v1", "v2", method="spearman")
    assert r["ok"] is True
    assert r["result"]["ci95"] == [None, None]


def test_correlate_spearman_bootstrap_reproducible_with_seed(saf_root):
    """Same seed should give same CI."""
    r1 = stat_correlate(
        "study.csv", "v1", "v2", method="spearman", bootstrap=200, seed=1
    )
    r2 = stat_correlate(
        "study.csv", "v1", "v2", method="spearman", bootstrap=200, seed=1
    )
    assert r1["result"]["ci95"] == r2["result"]["ci95"]


def test_correlate_kendall_with_bootstrap(saf_root):
    """Kendall tau can also use bootstrap CI."""
    r = stat_correlate("study.csv", "v1", "v2", method="kendall", bootstrap=200, seed=7)
    assert r["ok"] is True
    assert r["result"]["ci95"][0] is not None


def test_correlate_custom_alpha(saf_root):
    """alpha=0.10 should give a narrower 90% CI than the default 95% CI."""
    r95 = stat_correlate("study.csv", "v1", "v2", method="pearson")
    r90 = stat_correlate("study.csv", "v1", "v2", method="pearson", alpha=0.10)
    assert r95["ok"] is True
    assert r90["ok"] is True
    w95 = r95["result"]["ci95"][1] - r95["result"]["ci95"][0]
    w90 = r90["result"]["ci95"][1] - r90["result"]["ci95"][0]
    assert w90 < w95
