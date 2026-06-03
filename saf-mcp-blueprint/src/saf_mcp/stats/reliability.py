from __future__ import annotations

from typing import Any

import pandas as pd


def cronbach_alpha(df: pd.DataFrame, items: list[str]) -> dict[str, Any]:
    """Calculate Cronbach's alpha using listwise deletion."""
    data = df[items].apply(pd.to_numeric, errors="coerce")
    before = len(data)
    data = data.dropna()
    n = len(data)
    k = len(items)
    if k < 2:
        return {"ok": False, "error": "Cronbach alpha requires at least two items."}
    if n < 2:
        return {"ok": False, "error": "Not enough complete rows after missing-data removal."}

    item_variances = data.var(axis=0, ddof=1)
    total_score = data.sum(axis=1)
    total_variance = total_score.var(ddof=1)
    alpha = (k / (k - 1)) * (1 - item_variances.sum() / total_variance) if total_variance else float("nan")

    alpha_if_deleted = []
    for item in items:
        remaining = [x for x in items if x != item]
        if len(remaining) < 2:
            continue
        alpha_if_deleted.append({"deleted_item": item, "alpha": cronbach_alpha(data, remaining)["alpha"]})

    interpretation = (
        "Excellent internal consistency" if alpha >= 0.9 else
        "Good internal consistency" if alpha >= 0.8 else
        "Acceptable internal consistency" if alpha >= 0.7 else
        "Questionable internal consistency" if alpha >= 0.6 else
        "Poor internal consistency"
    )

    return {
        "ok": True,
        "method": "Cronbach's alpha",
        "items": items,
        "n_items": k,
        "n_used": n,
        "n_dropped_missing": before - n,
        "alpha": float(alpha),
        "alpha_if_item_deleted": alpha_if_deleted,
        "interpretation": interpretation,
    }
