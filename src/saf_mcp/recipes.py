"""SAF Analysis Recipe Runner — batch multiple analyses in one call.

A recipe is a JSON list of steps:

.. code-block:: json

  [
    {"kind": "descriptives", "variables": ["age", "score"]},
    {"kind": "reliability", "items": ["q1", "q2", "q3", "q4"]},
    {"kind": "correlation", "x": "screen_time", "y": "exam_score"},
    {"kind": "regression", "dependent": "exam_score", "independents": ["screen_time", "motivation"]}
  ]

Each step runs sequentially. Results include JSON, APA text, warnings,
and optional SPSS syntax per step.
"""

from __future__ import annotations

import time
from typing import Any

from .stats import (
    stat_anova,
    stat_assumptions,
    stat_chi_square,
    stat_compare_groups,
    stat_correlate,
    stat_describe_all,
    stat_descriptives,
    stat_frequencies,
    stat_missing,
    stat_outliers,
    stat_regress,
    stat_reliability,
)
from .reporting import apa_interpretation
from .syntax import syntax_for_recipe

RECIPE_KINDS: dict[str, str] = {
    "descriptives": "Descriptive statistics (n, mean, sd, min, max, skew, kurtosis)",
    "frequencies": "Frequency tables for categorical variables",
    "describe_all": "Describe all numeric columns",
    "assumptions": "Normality (Shapiro-Wilk) + Levene's test",
    "compare_groups": "t-test (independent/paired/Welch) + Mann-Whitney",
    "anova": "One-way ANOVA / Welch / Kruskal-Wallis",
    "correlation": "Pearson / Spearman / Kendall correlation",
    "regression": "OLS / logistic regression",
    "chi_square": "Chi-square test of independence",
    "reliability": "Cronbach's alpha for scale reliability",
    "missing": "Missing data profile",
    "outliers": "Outlier detection",
}


def _run_step(path: str, step: dict[str, Any]) -> dict[str, Any]:
    """Execute a single recipe step and return the result."""
    kind = step.get("kind", "")
    start = time.time()

    try:
        if kind == "descriptives":
            result = stat_descriptives(path, step.get("variables", []))
        elif kind == "frequencies":
            result = stat_frequencies(path, step.get("variables", []))
        elif kind == "describe_all":
            result = stat_describe_all(path)
        elif kind == "assumptions":
            result = stat_assumptions(
                path,
                step.get("variables", []),
                step.get("group_col"),
            )
        elif kind == "compare_groups":
            result = stat_compare_groups(
                path,
                step.get("value_col", ""),
                step.get("group_col", ""),
                paired=step.get("paired", False),
                parametric=step.get("parametric", True),
                equal_var=step.get("equal_var", False),
            )
        elif kind == "anova":
            result = stat_anova(
                path,
                step.get("value_col", ""),
                step.get("group_col", ""),
                welch=step.get("welch", False),
                post_hoc=step.get("post_hoc", True),
            )
        elif kind == "correlation":
            result = stat_correlate(
                path,
                step.get("x", ""),
                step.get("y", ""),
                method=step.get("method", "pearson"),
                bootstrap=step.get("bootstrap", 0),
                seed=step.get("seed"),
            )
        elif kind == "regression":
            result = stat_regress(
                path,
                step.get("dependent", ""),
                step.get("independents", []),
                family=step.get("family", "ols"),
                robust=step.get("robust", False),
            )
        elif kind == "chi_square":
            result = stat_chi_square(
                path,
                step.get("var_a", ""),
                step.get("var_b", ""),
                test=step.get("test", "independence"),
            )
        elif kind == "reliability":
            result = stat_reliability(path, step.get("items", []))
        elif kind == "missing":
            result = stat_missing(path)
        elif kind == "outliers":
            result = stat_outliers(
                path,
                step.get("variables", []),
                method=step.get("method", "iqr"),
                threshold=step.get("threshold", 1.5),
            )
        else:
            return {"ok": False, "error": {"message": f"Unknown recipe kind: {kind}"}}

        elapsed = round(time.time() - start, 3)
        output = dict(result) if isinstance(result, dict) else {"ok": False, "error": {"message": "Invalid result"}}

        # Add APA interpretation
        try:
            output["apa"] = apa_interpretation(kind, output)
        except Exception:
            output["apa"] = ""

        # Add SPSS syntax
        try:
            output["spss_syntax"] = syntax_for_recipe(path, step)
        except Exception:
            output["spss_syntax"] = ""

        output["_elapsed"] = elapsed
        return output

    except Exception as exc:
        return {
            "ok": False,
            "error": {"type": exc.__class__.__name__, "message": str(exc)},
            "_elapsed": round(time.time() - start, 3),
        }


def run_recipe(
    path: str,
    steps: list[dict[str, Any]],
    generate_syntax: bool = True,
    include_apa: bool = True,
) -> dict[str, Any]:
    """Execute a full analysis recipe.

    Parameters
    ----------
    path : str  Dataset path relative to SAF_DATA_ROOT.
    steps : list[dict]  List of recipe steps.
    generate_syntax : bool  Include SPSS syntax per step.
    include_apa : bool  Include APA-style interpretation per step.

    Returns
    -------
    dict with keys: ok, path, n_steps, results (list), warnings, total_elapsed.
    """
    total_start = time.time()
    results: list[dict[str, Any]] = []
    warnings: list[str] = []

    for i, step in enumerate(steps):
        kind = step.get("kind", "?")
        label = step.get("label", f"Step {i + 1}: {kind}")

        result = _run_step(path, step)
        entry = {
            "step": i + 1,
            "kind": kind,
            "label": label,
            "ok": result.get("ok", False),
            "elapsed": result.get("_elapsed", 0),
        }

        if include_apa:
            apa = result.get("apa", "")
            if apa:
                entry["apa"] = apa

        # Include the actual analysis data
        if "result" in result:
            entry["result"] = result["result"]
        elif "results" in result:
            entry["results"] = result["results"]
        elif "per_column" in result:
            entry["per_column"] = result["per_column"]

        if "spss_syntax" in result and generate_syntax:
            entry["spss_syntax"] = result["spss_syntax"]

        if not result.get("ok", False):
            err = result.get("error", {}).get("message", "Unknown error")
            entry["error"] = err
            warnings.append(f"Step {i + 1} ({kind}): {err}")

        results.append(entry)

    total_elapsed = round(time.time() - total_start, 3)

    recipe_key = {
        "path": path,
        "n_steps": len(steps),
        "n_ok": sum(1 for r in results if r["ok"]),
        "n_failed": sum(1 for r in results if not r["ok"]),
        "total_elapsed": total_elapsed,
        "results": results,
        "warnings": warnings,
    }

    return {"ok": True, "recipe": recipe_key}
