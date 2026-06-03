from __future__ import annotations

from typing import Any

import pandas as pd
import statsmodels.api as sm


def ols_regression(df: pd.DataFrame, dv: str, predictors: list[str]) -> dict[str, Any]:
    data = df[[dv] + predictors].apply(pd.to_numeric, errors="coerce").dropna()
    if len(data) < len(predictors) + 2:
        return {"ok": False, "error": "Not enough complete observations for OLS regression."}
    y = data[dv]
    x = sm.add_constant(data[predictors])
    model = sm.OLS(y, x).fit()
    rows = []
    for name in model.params.index:
        rows.append(
            {
                "term": name,
                "b": float(model.params[name]),
                "se": float(model.bse[name]),
                "t": float(model.tvalues[name]),
                "p": float(model.pvalues[name]),
                "ci95_low": float(model.conf_int().loc[name, 0]),
                "ci95_high": float(model.conf_int().loc[name, 1]),
            }
        )
    return {
        "ok": True,
        "method": "Ordinary least squares regression",
        "dv": dv,
        "predictors": predictors,
        "n_used": int(model.nobs),
        "r_squared": float(model.rsquared),
        "adj_r_squared": float(model.rsquared_adj),
        "f": float(model.fvalue) if model.fvalue is not None else None,
        "f_p": float(model.f_pvalue) if model.f_pvalue is not None else None,
        "coefficients": rows,
    }
