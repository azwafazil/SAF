from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy import stats


def descriptive(df: pd.DataFrame, variables: list[str]) -> dict[str, Any]:
    rows = []
    for var in variables:
        s = pd.to_numeric(df[var], errors="coerce").dropna()
        n = int(s.size)
        if n == 0:
            rows.append({"variable": var, "error": "No numeric data"})
            continue
        ci = stats.t.interval(0.95, n - 1, loc=float(s.mean()), scale=float(stats.sem(s))) if n > 1 else (np.nan, np.nan)
        rows.append(
            {
                "variable": var,
                "n": n,
                "mean": float(s.mean()),
                "sd": float(s.std(ddof=1)) if n > 1 else 0.0,
                "median": float(s.median()),
                "min": float(s.min()),
                "max": float(s.max()),
                "iqr": float(s.quantile(0.75) - s.quantile(0.25)),
                "skew": float(stats.skew(s, bias=False)) if n > 2 else None,
                "kurtosis": float(stats.kurtosis(s, bias=False)) if n > 3 else None,
                "ci95_low": None if np.isnan(ci[0]) else float(ci[0]),
                "ci95_high": None if np.isnan(ci[1]) else float(ci[1]),
            }
        )
    return {"ok": True, "method": "Descriptive statistics", "tables": rows}


def frequencies(df: pd.DataFrame, variable: str, *, include_percent: bool = True) -> dict[str, Any]:
    s = df[variable]
    counts = s.value_counts(dropna=False).rename_axis("value").reset_index(name="count")
    if include_percent:
        counts["percent"] = counts["count"] / len(s) * 100
    table = counts.astype({"value": "string"}).to_dict(orient="records")
    return {"ok": True, "method": "Frequencies", "variable": variable, "n": len(s), "table": table}


def missing_profile(df: pd.DataFrame) -> dict[str, Any]:
    rows = []
    for col in df.columns:
        n_missing = int(df[col].isna().sum())
        rows.append(
            {
                "variable": col,
                "missing": n_missing,
                "missing_percent": float(n_missing / len(df) * 100) if len(df) else 0.0,
            }
        )
    return {"ok": True, "method": "Missing-data profile", "table": rows}
