import os
from pathlib import Path

import pandas as pd

from saf_mcp.stats.descriptive import descriptive, frequencies
from saf_mcp.stats.reliability import cronbach_alpha
from saf_mcp.stats.inferential import correlation_matrix, one_way_anova
from saf_mcp.stats.regression import ols_regression


def sample_df():
    return pd.DataFrame(
        {
            "gender": ["F", "M", "F", "M"],
            "group": ["A", "A", "B", "B"],
            "q1": [4, 3, 5, 2],
            "q2": [5, 4, 5, 3],
            "q3": [4, 3, 5, 2],
            "score": [80, 70, 90, 60],
            "screen_time": [5, 8, 4, 10],
        }
    )


def test_descriptive():
    out = descriptive(sample_df(), ["score"])
    assert out["ok"] is True
    assert out["tables"][0]["n"] == 4


def test_frequencies():
    out = frequencies(sample_df(), "gender")
    assert out["ok"] is True
    assert len(out["table"]) == 2


def test_alpha():
    out = cronbach_alpha(sample_df(), ["q1", "q2", "q3"])
    assert out["ok"] is True
    assert "alpha" in out


def test_correlation():
    out = correlation_matrix(sample_df(), ["score", "screen_time"])
    assert out["ok"] is True


def test_anova():
    out = one_way_anova(sample_df(), "score", "group")
    assert out["ok"] is True


def test_regression():
    out = ols_regression(sample_df(), "score", ["screen_time", "q1"])
    assert out["ok"] is True
