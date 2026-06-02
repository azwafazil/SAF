"""Tests for the 12 donated stat_* tools.

Donated by Muhammad Arif bin Fazil <ariffazil@arif-fazil.com> 2026-06-02.
Originally forged as part of the arifOS sovereign organ (decommissioned).
Ported to upstream-style for inclusive reuse.
"""

from __future__ import annotations

import math
import os
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from saf_mcp.stats import (
    stat_anova,
    stat_assumptions,
    stat_chi_square,
    stat_compare_groups,
    stat_correlate,
    stat_descriptives,
    stat_effect_size,
    stat_missing,
    stat_nonparametric,
    stat_outliers,
    stat_power,
    stat_regress,
)


@pytest.fixture
def saf_root(tmp_path, monkeypatch):
    """Set SAF_DATA_ROOT to a tmp dir and write a small CSV."""
    monkeypatch.setenv("SAF_DATA_ROOT", str(tmp_path))
    csv = tmp_path / "toy.csv"
    df = pd.DataFrame(
        {
            "g": (["A"] * 30) + (["B"] * 30) + (["C"] * 30),
            "v1": list(range(30)) + list(range(20, 50)) + list(range(10, 40)),
            "v2": ([1.0] * 15 + [2.0] * 15)
            + ([3.0] * 15 + [4.0] * 15)
            + ([5.0] * 15 + [6.0] * 15),
            "v_skew": [1] * 89 + [1000],  # one big outlier
        }
    )
    df.to_csv(csv, index=False)
    return csv


# 1. stat_descriptives


def test_stat_descriptives_normal(saf_root):
    r = stat_descriptives("toy.csv", ["v1"])
    assert r["ok"] is True
    assert len(r["results"]) == 1
    row = r["results"][0]
    assert row["n"] == 90
    assert 20 < row["mean"] < 30
    assert row["sd"] > 0
    assert "spss_syntax" in r


def test_stat_descriptives_skewed(saf_root):
    r = stat_descriptives("toy.csv", ["v_skew"])
    assert r["ok"] is True
    assert r["results"][0]["skew"] > 0.5  # right-skewed


def test_stat_descriptives_unknown_column(saf_root):
    r = stat_descriptives("toy.csv", ["nonexistent"])
    assert r["ok"] is False
    assert r["error"]["type"] == "ValueError"


# 2. stat_assumptions


def test_stat_assumptions_normality(saf_root):
    r = stat_assumptions("toy.csv", ["v1"])
    assert r["ok"] is True
    assert r["n_columns"] == 1
    assert "normality_p" in r["results"][0]


def test_stat_assumptions_with_group_levene(saf_root):
    r = stat_assumptions("toy.csv", ["v1"], group_col="g")
    assert r["ok"] is True
    assert r["levene"] is not None
    assert "homoscedastic" in r["levene"]


# 3. stat_compare_groups


def test_compare_groups_ttest(saf_root, tmp_path):
    # Build a 2-group dataset (toy.csv has 3 groups → compare_groups requires 2)
    df = pd.DataFrame(
        {
            "g": (["A"] * 30) + (["B"] * 30),
            "v1": list(range(30)) + list(range(20, 50)),
        }
    )
    p2 = tmp_path / "two_group.csv"
    df.to_csv(p2, index=False)
    r = stat_compare_groups("two_group.csv", "v1", "g", parametric=True)
    assert r["ok"] is True
    assert r["result"]["method"] == "Welch t-test"  # equal_var default is False
    assert "t_stat" in r["result"]
    assert "p_value" in r["result"]


def test_compare_groups_mannwhitney(saf_root, tmp_path):
    df = pd.DataFrame(
        {
            "g": (["A"] * 30) + (["B"] * 30),
            "v1": list(range(30)) + list(range(20, 50)),
        }
    )
    p2 = tmp_path / "two_group2.csv"
    df.to_csv(p2, index=False)
    r = stat_compare_groups("two_group2.csv", "v1", "g", parametric=False)
    assert r["ok"] is True
    assert r["result"]["method"] == "Mann-Whitney U"


def test_compare_groups_wrong_groups(saf_root):
    r = stat_compare_groups("toy.csv", "v1", "g", parametric=True)
    # 3 groups → should fail (compare_groups requires 2)
    assert r["ok"] is False


# 4. stat_anova


def test_anova_classic(saf_root):
    r = stat_anova("toy.csv", "v1", "g", post_hoc=False)
    assert r["ok"] is True
    assert r["result"]["method"] == "One-way ANOVA (Type II)"
    assert "F" in r["result"]
    assert "p_value" in r["result"]
    assert "eta_squared" in r["result"]


def test_anova_welch(saf_root):
    r = stat_anova("toy.csv", "v1", "g", welch=True, post_hoc=False)
    assert r["ok"] is True
    assert r["result"]["method"] == "Welch ANOVA"


# 5. stat_correlate


def test_correlate_pearson(saf_root):
    r = stat_correlate("toy.csv", "v1", "v2", method="pearson")
    assert r["ok"] is True
    assert r["result"]["method"] == "pearson"
    assert "r" in r["result"]


def test_correlate_spearman(saf_root):
    r = stat_correlate("toy.csv", "v1", "v2", method="spearman")
    assert r["ok"] is True
    assert r["result"]["method"] == "spearman"


# 6. stat_regress


def test_regress_ols(saf_root):
    r = stat_regress("toy.csv", "v1", ["v2"], family="ols")
    assert r["ok"] is True
    assert "r_squared" in r["result"]
    assert "coefficients" in r["result"]
    assert "v2" in r["result"]["coefficients"]


def test_regress_vif(saf_root):
    # 2+ independents → VIF should be computed
    df = pd.DataFrame(
        {
            "y": np.random.randn(50),
            "x1": np.random.randn(50),
            "x2": np.random.randn(50),
        }
    )
    df.to_csv(saf_root.parent / "regress.csv", index=False)
    r = stat_regress("regress.csv", "y", ["x1", "x2"])
    assert r["ok"] is True
    assert "vif" in r["result"]


# 7. stat_chi_square


def test_chi_square_independence(saf_root):
    # Build a 2x2 table
    df = pd.DataFrame(
        {
            "a": (["x"] * 30) + (["y"] * 30),
            "b": (["p"] * 20) + (["q"] * 10) + (["p"] * 10) + (["q"] * 20),
            "v1": range(60),
        }
    )
    df.to_csv(saf_root.parent / "chi.csv", index=False)
    r = stat_chi_square("chi.csv", "a", "b", test="independence")
    assert r["ok"] is True
    assert "chi2" in r["result"]
    assert "cramers_v" in r["result"]
    assert "fisher_exact" in r["result"]  # 2x2 → Fisher included


# 8. stat_nonparametric


def test_nonparametric_wilcoxon(saf_root):
    r = stat_nonparametric("toy.csv", "v1", test="wilcoxon", mu=25.0)
    assert r["ok"] is True
    assert "W" in r["result"]


def test_nonparametric_mannwhitney_via_group(saf_root):
    r = stat_nonparametric("toy.csv", "v1", group_col="g", test="wilcoxon")
    # 3 groups → falls back to Kruskal
    assert r["ok"] is True
    assert r["result"]["method"] in (
        "Kruskal-Wallis H",
        "Mann-Whitney U (via group_col)",
    )


# 9. stat_effect_size


def test_effect_size_cohens_d():
    x = [1, 2, 3, 4, 5]
    y = [3, 4, 5, 6, 7]
    r = stat_effect_size(kind="cohens_d", x=x, y=y)
    assert r["ok"] is True
    assert abs(r["result"]["value"]) > 0  # nonzero effect


def test_effect_size_unknown_kind():
    r = stat_effect_size(kind="unknown_kind")
    assert r["ok"] is False


# 10. stat_power


def test_stat_power_solve_power():
    r = stat_power(test="t", effect_size=0.5, alpha=0.05, nobs=64)
    assert r["ok"] is True
    assert "solved_power" in r["result"]
    assert 0.5 < r["result"]["solved_power"] < 1.0


def test_stat_power_solve_nobs():
    r = stat_power(test="t", effect_size=0.5, alpha=0.05, power=0.8)
    assert r["ok"] is True
    assert r["result"]["solved_nobs"] > 0


def test_stat_power_unknown_test():
    r = stat_power(test="unknown", effect_size=0.5, alpha=0.05, nobs=10)
    assert r["ok"] is False


# 11. stat_outliers


def test_outliers_iqr(saf_root):
    r = stat_outliers("toy.csv", ["v_skew"], method="iqr", threshold=1.5)
    assert r["ok"] is True
    assert r["per_column"]["v_skew"]["n_outliers"] >= 1


def test_outliers_z(saf_root):
    r = stat_outliers("toy.csv", ["v_skew"], method="z", threshold=2.0)
    assert r["ok"] is True
    assert r["per_column"]["v_skew"]["n_outliers"] >= 1


def test_outliers_modified_z(saf_root):
    r = stat_outliers("toy.csv", ["v_skew"], method="modified_z", threshold=3.5)
    assert r["ok"] is True


def test_outliers_mahalanobis(saf_root):
    r = stat_outliers("toy.csv", ["v1", "v2"], method="mahalanobis")
    assert r["ok"] is True


# 12. stat_missing


def test_stat_missing(saf_root):
    # Inject some NaN
    df = pd.read_csv(saf_root)
    df.loc[0:4, "v1"] = np.nan
    df.to_csv(saf_root, index=False)
    r = stat_missing("toy.csv")
    assert r["ok"] is True
    assert r["n_rows"] == 90
    assert r["complete_rows"] < 90
    assert any(c["n_missing"] > 0 for c in r["per_column"] if c["column"] == "v1")
