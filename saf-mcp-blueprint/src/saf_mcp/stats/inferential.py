from __future__ import annotations

from typing import Any

import pandas as pd
from scipy import stats


def t_test_independent(df: pd.DataFrame, dv: str, group: str, group_a: str | int | float, group_b: str | int | float) -> dict[str, Any]:
    data = df[[dv, group]].dropna()
    a = pd.to_numeric(data.loc[data[group] == group_a, dv], errors="coerce").dropna()
    b = pd.to_numeric(data.loc[data[group] == group_b, dv], errors="coerce").dropna()
    if len(a) < 2 or len(b) < 2:
        return {"ok": False, "error": "Each group needs at least two numeric observations."}
    t_stat, p_val = stats.ttest_ind(a, b, equal_var=False)
    dof_num = (a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b)) ** 2
    dof_den = ((a.var(ddof=1) / len(a)) ** 2 / (len(a) - 1)) + ((b.var(ddof=1) / len(b)) ** 2 / (len(b) - 1))
    dof = dof_num / dof_den if dof_den else None
    pooled_sd = (((len(a) - 1) * a.var(ddof=1) + (len(b) - 1) * b.var(ddof=1)) / (len(a) + len(b) - 2)) ** 0.5
    cohen_d = (a.mean() - b.mean()) / pooled_sd if pooled_sd else None
    return {
        "ok": True,
        "method": "Welch independent samples t-test",
        "dv": dv,
        "group": group,
        "groups": [group_a, group_b],
        "n_a": int(len(a)),
        "n_b": int(len(b)),
        "mean_a": float(a.mean()),
        "mean_b": float(b.mean()),
        "t": float(t_stat),
        "df": None if dof is None else float(dof),
        "p": float(p_val),
        "cohen_d": None if cohen_d is None else float(cohen_d),
    }


def one_way_anova(df: pd.DataFrame, dv: str, between: str) -> dict[str, Any]:
    data = df[[dv, between]].dropna()
    groups = []
    labels = []
    for label, sub in data.groupby(between):
        vals = pd.to_numeric(sub[dv], errors="coerce").dropna()
        if len(vals) >= 2:
            groups.append(vals)
            labels.append(label)
    if len(groups) < 2:
        return {"ok": False, "error": "ANOVA needs at least two groups with two observations each."}
    f_stat, p_val = stats.f_oneway(*groups)
    grand = pd.to_numeric(data[dv], errors="coerce").dropna()
    ss_between = sum(len(g) * (g.mean() - grand.mean()) ** 2 for g in groups)
    ss_total = sum((grand - grand.mean()) ** 2)
    eta_sq = ss_between / ss_total if ss_total else None
    return {
        "ok": True,
        "method": "One-way ANOVA",
        "dv": dv,
        "between": between,
        "groups": [str(x) for x in labels],
        "F": float(f_stat),
        "p": float(p_val),
        "eta_squared": None if eta_sq is None else float(eta_sq),
    }


def chi_square_test(df: pd.DataFrame, row: str, column: str) -> dict[str, Any]:
    table = pd.crosstab(df[row], df[column])
    chi2, p, dof, expected = stats.chi2_contingency(table)
    n = table.to_numpy().sum()
    r, c = table.shape
    cramer_v = (chi2 / (n * (min(r - 1, c - 1)))) ** 0.5 if min(r - 1, c - 1) > 0 else None
    return {
        "ok": True,
        "method": "Pearson chi-square test of independence",
        "row": row,
        "column": column,
        "observed": table.reset_index().astype(str).to_dict(orient="records"),
        "chi2": float(chi2),
        "df": int(dof),
        "p": float(p),
        "cramers_v": None if cramer_v is None else float(cramer_v),
        "expected_min": float(expected.min()),
    }


def correlation_matrix(df: pd.DataFrame, variables: list[str], method: str = "pearson") -> dict[str, Any]:
    data = df[variables].apply(pd.to_numeric, errors="coerce")
    corr = data.corr(method=method)
    pvals: dict[str, dict[str, float | None]] = {}
    for a in variables:
        pvals[a] = {}
        for b in variables:
            pair = data[[a, b]].dropna()
            if len(pair) < 3:
                pvals[a][b] = None
            elif method == "spearman":
                pvals[a][b] = float(stats.spearmanr(pair[a], pair[b]).pvalue)
            else:
                pvals[a][b] = float(stats.pearsonr(pair[a], pair[b]).pvalue)
    return {
        "ok": True,
        "method": f"{method.title()} correlation",
        "variables": variables,
        "correlation": corr.to_dict(),
        "p_values": pvals,
    }
