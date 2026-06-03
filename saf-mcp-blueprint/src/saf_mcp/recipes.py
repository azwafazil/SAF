from __future__ import annotations

from typing import Any

from .io import read_dataset
from .stats.descriptive import descriptive, frequencies
from .stats.inferential import chi_square_test, correlation_matrix, one_way_anova, t_test_independent
from .stats.regression import ols_regression
from .stats.reliability import cronbach_alpha


def run_recipe(file: str, steps: list[dict[str, Any]]) -> dict[str, Any]:
    df, _ = read_dataset(file)
    results: list[dict[str, Any]] = []

    for step in steps:
        kind = step.get("kind")
        if kind == "descriptives":
            results.append(descriptive(df, step["variables"]))
        elif kind == "frequencies":
            for variable in step["variables"]:
                results.append(frequencies(df, variable))
        elif kind == "reliability":
            results.append(cronbach_alpha(df, step["items"]))
        elif kind == "ttest_independent":
            results.append(t_test_independent(df, step["dv"], step["group"], step["group_a"], step["group_b"]))
        elif kind == "anova":
            results.append(one_way_anova(df, step["dv"], step["between"]))
        elif kind == "chi_square":
            results.append(chi_square_test(df, step["row"], step["column"]))
        elif kind == "correlation":
            results.append(correlation_matrix(df, step["variables"], step.get("method", "pearson")))
        elif kind == "regression":
            results.append(ols_regression(df, step["dv"], step["predictors"]))
        else:
            results.append({"ok": False, "error": f"Unsupported recipe step: {kind}", "step": step})

    return {"ok": True, "file": file, "n_steps": len(steps), "results": results}
