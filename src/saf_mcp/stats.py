"""SAF Statistical Analysis Tools — 12 inferential-statistics MCP tools.

This module is a clean, upstream-style port of the 12 stat_* primitives
originally added in the arifOS sovereign organ (2026-06-02). It uses
the upstream security sandbox (SAF_DATA_ROOT) for path resolution and
returns plain Python dicts — no F1-F13 governance wrapping, no
VAULT999 sealing. The statistical logic is unchanged from the
ariffazil/arifOS donation.

The 12 tools:
  1.  stat_descriptives      univariate summary with skew, kurt, IQR, MAD
  2.  stat_assumptions       Shapiro-Wilk, Levene, normality, homoscedasticity
  3.  stat_compare_groups    t-test (indep/paired/Welch) + Mann-Whitney
  4.  stat_anova             one-way, Welch, Kruskal-Wallis, Friedman
  5.  stat_correlate         Pearson, Spearman, Kendall with CIs
  6.  stat_regress           OLS, logistic, robust; diagnostics + VIF
  7.  stat_chi_square        independence, GOF, Fisher exact
  8.  stat_nonparametric     Wilcoxon, sign, Friedman
  9.  stat_effect_size       Cohen's d, η², Cramér's V, OR, rank-biserial
  10. stat_power             a priori, post-hoc, sensitivity
  11. stat_outliers          z, modified z, IQR, Mahalanobis, Cook's D
  12. stat_missing           pattern, Little's MCAR, listwise/pairwise

DITEMPA BUKAN DIBERI — Forged, Not Given.
Donated by Muhammad Arif bin Fazil <ariffazil@arif-fazil.com>
Original implementation: arifOS sovereign organ (decommissioned 2026-06-02).
"""

from __future__ import annotations

import math
import warnings
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

# Lazy imports: scipy/statsmodels/pingouin are heavy. The MCP server
# starts fast; heavy deps load only when a stat_* tool is called.
try:
    from scipy import stats as _ss
    from scipy.stats import shapiro, levene, mannwhitneyu, wilcoxon, friedmanchisquare
    from scipy.stats import kruskal, pearsonr, spearmanr, kendalltau
    from scipy.stats import ttest_ind, ttest_rel, ttest_1samp, f_oneway
    from scipy.stats import chi2_contingency, fisher_exact
    from scipy.stats import norm, t as t_dist
except ImportError:  # pragma: no cover
    _ss = None  # type: ignore

try:
    from statsmodels.stats import power as _sm_power
    from statsmodels.stats.multicomp import pairwise_tukeyhsd
    from statsmodels.stats.outliers_influence import variance_inflation_factor
    from statsmodels.formula.api import ols as _sm_ols, logit as _sm_logit
    import statsmodels.api as _sm
except ImportError:  # pragma: no cover
    _sm_power = None  # type: ignore

try:
    import pingouin as _pg
except ImportError:  # pragma: no cover
    _pg = None  # type: ignore

from .security import (
    require_existing_dataset,
    SPSS_EXTENSIONS,
    TABULAR_EXTENSIONS,
    extension_for,
)
from .spss_utils import frequency_table, read_spss, read_tabular

warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="statsmodels")
warnings.filterwarnings("ignore", category=FutureWarning, module="scipy")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pingouin")


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------


def _load_dataframe(path: str) -> pd.DataFrame:
    """Resolve `path` inside the SAF sandbox and load the dataset."""
    # Allow either SPSS or tabular extensions
    p = Path(path)
    ext = extension_for(p)
    if ext in SPSS_EXTENSIONS:
        resolved = require_existing_dataset(path, SPSS_EXTENSIONS)
        df, _ = read_spss(resolved)
        return df
    if ext in TABULAR_EXTENSIONS:
        resolved = require_existing_dataset(path, TABULAR_EXTENSIONS)
        return read_tabular(resolved)
    # Fallback: try to read any supported dataset
    resolved = require_existing_dataset(path)
    if ext == ".sav" or ext == ".zsav" or ext == ".por":
        df, _ = read_spss(resolved)
        return df
    return read_tabular(resolved)


def _ci(stat: float, se: float, n: int, alpha: float = 0.05) -> list:
    """Normal-approximation confidence interval (two-sided)."""
    if se is None or se == 0 or n < 2:
        return [None, None]
    z = norm.ppf(1 - alpha / 2) if _ss is not None else 1.96
    return [round(stat - z * se, 6), round(stat + z * se, 6)]


def _add_const(X: "pd.DataFrame") -> "pd.DataFrame":
    """Augment a feature matrix with an intercept column for statsmodels."""
    return _sm.add_constant(X, has_constant="add") if _sm is not None else X


# ---------------------------------------------------------------------------
# 1. stat_descriptives
# ---------------------------------------------------------------------------


def stat_descriptives(file_path: str, columns: list[str]) -> dict:
    """Univariate summary statistics per column (numeric + categorical)."""
    df = _load_dataframe(file_path)
    cols = [c for c in columns if c in df.columns]
    if not cols:
        return {
            "ok": False,
            "error": {"type": "ValueError", "message": "no valid columns"},
        }
    out = []
    for c in cols:
        s = df[c].dropna()
        if not pd.api.types.is_numeric_dtype(s):
            out.append(
                {
                    "column": c,
                    "dtype": str(s.dtype),
                    "n": int(len(s)),
                    "n_unique": int(s.nunique()),
                    "top": str(s.mode().iat[0]) if len(s) else None,
                }
            )
            continue
        n = int(len(s))
        mean = float(s.mean())
        sd = float(s.std())
        se = sd / math.sqrt(n) if n > 1 else None
        out.append(
            {
                "column": c,
                "dtype": str(s.dtype),
                "n": n,
                "mean": mean,
                "sd": sd,
                "median": float(s.median()),
                "min": float(s.min()),
                "max": float(s.max()),
                "q25": float(s.quantile(0.25)),
                "q75": float(s.quantile(0.75)),
                "iqr": float(s.quantile(0.75) - s.quantile(0.25)),
                "mad": float((s - s.median()).abs().median()),
                "skew": float(s.skew()),
                "kurtosis": float(s.kurt()),
                "se_mean": se,
                "ci95_mean": _ci(mean, se, n) if se is not None else [None, None],
            }
        )
    spss = (
        "DESCRIPTIVES VARIABLES="
        + " ".join(cols)
        + " /STATISTICS=MEAN STDDEV MIN MAX SKEW KURT.\n"
    )
    return {"ok": True, "results": out, "spss_syntax": spss, "n_columns": len(out)}


# ---------------------------------------------------------------------------
# 2. stat_assumptions
# ---------------------------------------------------------------------------


def stat_assumptions(
    file_path: str, columns: list[str], group_col: Optional[str] = None
) -> dict:
    """Normality (Shapiro-Wilk) + homoscedasticity (Levene) per column."""
    if _ss is None:
        return {
            "ok": False,
            "error": {"type": "ImportError", "message": "scipy not installed"},
        }
    df = _load_dataframe(file_path)
    cols = [c for c in columns if c in df.columns]
    results = []
    for c in cols:
        s = df[c].dropna()
        if not pd.api.types.is_numeric_dtype(s) or len(s) < 3:
            continue
        try:
            sw_stat, sw_p = shapiro(s) if len(s) <= 5000 else _ss.normaltest(s)
            sw_method = "Shapiro-Wilk" if len(s) <= 5000 else "D'Agostino-Pearson"
        except Exception:
            sw_stat, sw_p = _ss.normaltest(s)
            sw_method = "D'Agostino-Pearson"
        results.append(
            {
                "column": c,
                "n": int(len(s)),
                "normality_test": sw_method,
                "normality_stat": float(sw_stat),
                "normality_p": float(sw_p),
                "normality_pass": bool(sw_p > 0.05),
                "skew": float(s.skew()),
                "kurtosis": float(s.kurt()),
            }
        )
    levene_result = None
    if group_col and group_col in df.columns and len(cols) >= 1:
        c = cols[0]
        groups = [
            g[c].dropna().values
            for _, g in df.groupby(group_col)
            if len(g[c].dropna()) > 1
        ]
        if len(groups) >= 2:
            ls, lp = levene(*groups, center="median")
            levene_result = {
                "column": c,
                "group_col": group_col,
                "levene_stat": float(ls),
                "levene_p": float(lp),
                "homoscedastic": bool(lp > 0.05),
            }
    return {
        "ok": True,
        "results": results,
        "levene": levene_result,
        "n_columns": len(results),
    }


# ---------------------------------------------------------------------------
# 3. stat_compare_groups
# ---------------------------------------------------------------------------


def stat_compare_groups(
    file_path: str,
    value_col: str,
    group_col: str,
    *,
    paired: bool = False,
    parametric: bool = True,
    equal_var: bool = False,
    alternative: str = "two-sided",
) -> dict:
    """Two-group comparison: t-test (indep/paired/Welch) + Mann-Whitney."""
    if _ss is None:
        return {
            "ok": False,
            "error": {"type": "ImportError", "message": "scipy not installed"},
        }
    df = _load_dataframe(file_path)
    if value_col not in df.columns or group_col not in df.columns:
        return {
            "ok": False,
            "error": {
                "type": "ValueError",
                "message": "value_col or group_col not in dataset",
            },
        }
    groups = [g[value_col].dropna().values for _, g in df.groupby(group_col)]
    if len(groups) != 2:
        return {
            "ok": False,
            "error": {
                "type": "ValueError",
                "message": f"need exactly 2 groups, got {len(groups)}",
            },
        }
    g1, g2 = groups
    out: dict[str, Any] = {
        "value_col": value_col,
        "group_col": group_col,
        "n_group1": int(len(g1)),
        "n_group2": int(len(g2)),
        "paired": bool(paired),
    }
    if parametric:
        if paired:
            t_stat, p_val = ttest_rel(g1, g2, alternative=alternative)
            out["method"] = "Paired t-test"
        else:
            t_stat, p_val = ttest_ind(
                g1, g2, equal_var=equal_var, alternative=alternative
            )
            out["method"] = "Student t" if equal_var else "Welch t-test"
        df_t = (
            len(g1) + len(g2) - 2
            if (not paired and equal_var)
            else min(len(g1), len(g2)) - 1
        )
        out.update(
            {
                "t_stat": float(t_stat),
                "p_value": float(p_val),
                "df": float(df_t),
            }
        )
        # Cohen's d (pooled) + Hedges' g (small-sample bias correction)
        if len(g1) > 1 and len(g2) > 1 and not paired:
            pooled_sd = math.sqrt(
                (
                    (len(g1) - 1) * float(np.var(g1, ddof=1))
                    + (len(g2) - 1) * float(np.var(g2, ddof=1))
                )
                / (len(g1) + len(g2) - 2)
            )
            if pooled_sd and pooled_sd > 0:
                d = (float(np.mean(g1)) - float(np.mean(g2))) / pooled_sd
                out["cohens_d"] = round(float(d), 4)
                # Hedges & Olkin (1985) small-sample correction factor
                df = len(g1) + len(g2) - 2
                if df > 2:
                    j = 1 - 3 / (4 * df - 5)
                    out["hedges_g"] = round(float(d) * j, 4)
    else:
        u_stat, p_val = mannwhitneyu(g1, g2, alternative=alternative)
        out.update(
            {
                "method": "Mann-Whitney U",
                "u_stat": float(u_stat),
                "p_value": float(p_val),
            }
        )
    return {"ok": True, "result": out}


# ---------------------------------------------------------------------------
# 4. stat_anova
# ---------------------------------------------------------------------------


def stat_anova(
    file_path: str,
    value_col: str,
    group_col: str,
    *,
    welch: bool = False,
    post_hoc: bool = True,
) -> dict:
    """One-way ANOVA: classic / Welch / Kruskal-Wallis with optional Tukey HSD."""
    if _ss is None:
        return {
            "ok": False,
            "error": {"type": "ImportError", "message": "scipy not installed"},
        }
    df = _load_dataframe(file_path)
    if value_col not in df.columns or group_col not in df.columns:
        return {
            "ok": False,
            "error": {
                "type": "ValueError",
                "message": "value_col or group_col not in dataset",
            },
        }
    groups = [g[value_col].dropna().values for _, g in df.groupby(group_col)]
    groups = [g for g in groups if len(g) > 0]
    if len(groups) < 2:
        return {
            "ok": False,
            "error": {"type": "ValueError", "message": "need >= 2 groups"},
        }
    out: dict[str, Any] = {
        "value_col": value_col,
        "group_col": group_col,
        "n_groups": len(groups),
        "group_sizes": [int(len(g)) for g in groups],
    }
    if welch and _pg is not None:
        welch_df = _pg.welch_anova(
            dv=value_col, between=group_col, data=df[[value_col, group_col]].dropna()
        )
        out.update(
            {
                "method": "Welch ANOVA",
                "F": float(welch_df["F"].iat[0]),
                "df_num": float(welch_df["ddof1"].iat[0]),
                "df_den": float(welch_df["ddof2"].iat[0]),
                "p_value": float(welch_df["p_unc"].iat[0]),
            }
        )
    else:
        f_stat, p_val = f_oneway(*groups)
        df_between = len(groups) - 1
        df_within = sum(len(g) for g in groups) - len(groups)
        # eta-squared
        ss_between = sum(
            len(g) * (float(np.mean(g)) - float(np.mean(np.concatenate(groups)))) ** 2
            for g in groups
        )
        ss_total = sum(
            (x - float(np.mean(np.concatenate(groups)))) ** 2 for g in groups for x in g
        )
        eta2 = ss_between / ss_total if ss_total > 0 else None
        out.update(
            {
                "method": "One-way ANOVA (Type II)",
                "F": float(f_stat),
                "df_between": float(df_between),
                "df_within": float(df_within),
                "p_value": float(p_val),
                "eta_squared": round(float(eta2), 4) if eta2 is not None else None,
            }
        )
        if post_hoc and _sm is not None and p_val < 0.05:
            try:
                tukey = pairwise_tukeyhsd(
                    endog=df[value_col].dropna(),
                    groups=df.loc[df[value_col].notna(), group_col],
                    alpha=0.05,
                )
                out["post_hoc"] = {
                    "method": "Tukey HSD",
                    "alpha": 0.05,
                    "groups": [str(g) for g in tukey.groupsunique],
                    "comparisons": [
                        {
                            "group1": str(row[0]),
                            "group2": str(row[1]),
                            "meandiff": float(row[2]),
                            "p_adj": float(row[3]),
                            "lower": float(row[4]),
                            "upper": float(row[5]),
                            "reject": bool(row[6]),
                        }
                        for row in tukey.summary().data[1:]
                    ],
                }
            except Exception as exc:  # noqa: BLE001
                out["post_hoc_error"] = str(exc)[:120]
    return {"ok": True, "result": out}


# ---------------------------------------------------------------------------
# 5. stat_correlate
# ---------------------------------------------------------------------------


def stat_correlate(
    file_path: str,
    x: str,
    y: str,
    *,
    method: str = "pearson",
    alpha: float = 0.05,
    bootstrap: int = 0,
    seed: Optional[int] = None,
) -> dict:
    """Correlation between two columns with CI and p-value.

    Parameters
    ----------
    method : str
        "pearson" (95% CI via Fisher z), "spearman" or "kendall"
        (CI via percentile bootstrap when ``bootstrap > 0``).
    alpha : float
        Significance level for the confidence interval (default 0.05).
    bootstrap : int
        Number of bootstrap resamples for non-parametric CI.
        0 (default) skips the bootstrap and returns ``ci95=[null, null]``
        for Spearman / Kendall.
    seed : int, optional
        RNG seed for bootstrap reproducibility.
    """
    if _ss is None:
        return {
            "ok": False,
            "error": {"type": "ImportError", "message": "scipy not installed"},
        }
    df = _load_dataframe(file_path)
    if x not in df.columns or y not in df.columns:
        return {
            "ok": False,
            "error": {"type": "ValueError", "message": "x or y not in dataset"},
        }
    sub = df[[x, y]].dropna()
    n = int(len(sub))
    if n < 3:
        return {
            "ok": False,
            "error": {"type": "ValueError", "message": "need >= 3 paired observations"},
        }
    xv = sub[x].values.astype(float)
    yv = sub[y].values.astype(float)
    method = method.lower()
    if method == "pearson":
        r, p = pearsonr(xv, yv)
        # 95% CI via Fisher z
        z = np.arctanh(r)
        se = 1.0 / math.sqrt(n - 3) if n > 3 else None
        ci = _ci(float(z), se, n, alpha=alpha)
        if ci[0] is not None:
            ci = [round(math.tanh(ci[0]), 6), round(math.tanh(ci[1]), 6)]
    elif method == "spearman":
        r, p = spearmanr(xv, yv)
        ci = _bootstrap_ci(xv, yv, "spearman", bootstrap, alpha, seed)
    elif method == "kendall":
        r, p = kendalltau(xv, yv)
        ci = _bootstrap_ci(xv, yv, "kendall", bootstrap, alpha, seed)
    else:
        return {
            "ok": False,
            "error": {"type": "ValueError", "message": f"unknown method {method}"},
        }
    return {
        "ok": True,
        "result": {
            "method": method,
            "x": x,
            "y": y,
            "n": n,
            "r": round(float(r), 6),
            "p_value": float(p),
            "ci95": ci,
            "alpha": alpha,
        },
    }


def _bootstrap_ci(
    x: "np.ndarray",
    y: "np.ndarray",
    method: str,
    n_boot: int,
    alpha: float,
    seed: Optional[int],
) -> list:
    """Percentile-bootstrap CI for Spearman / Kendall correlation.

    Returns ``[None, None]`` if ``n_boot <= 0`` (opt-in only — bootstrap is
    slow on large n).
    """
    if n_boot is None or n_boot <= 0:
        return [None, None]
    rng = np.random.default_rng(seed)
    n = len(x)
    fn = spearmanr if method == "spearman" else kendalltau
    rs = np.empty(int(n_boot), dtype=float)
    for i in range(int(n_boot)):
        idx = rng.integers(0, n, n)
        try:
            r_boot, _ = fn(x[idx], y[idx])
            rs[i] = (
                float(r_boot) if r_boot is not None and not np.isnan(r_boot) else np.nan
            )
        except Exception:  # noqa: BLE001
            rs[i] = np.nan
    rs = rs[~np.isnan(rs)]
    if len(rs) < 10:
        return [None, None]
    lo = float(np.quantile(rs, alpha / 2))
    hi = float(np.quantile(rs, 1 - alpha / 2))
    return [round(lo, 6), round(hi, 6)]


# ---------------------------------------------------------------------------
# 6. stat_regress
# ---------------------------------------------------------------------------


def stat_regress(
    file_path: str,
    dependent: str,
    independents: list[str],
    *,
    family: str = "ols",
    robust: bool = False,
) -> dict:
    """OLS / logistic / robust (HC3) regression with diagnostics."""
    if _sm is None:
        return {
            "ok": False,
            "error": {"type": "ImportError", "message": "statsmodels not installed"},
        }
    df = _load_dataframe(file_path)
    if dependent not in df.columns or any(c not in df.columns for c in independents):
        return {
            "ok": False,
            "error": {
                "type": "ValueError",
                "message": "dependent or independents not in dataset",
            },
        }
    sub = df[[dependent] + independents].dropna()
    n = int(len(sub))
    if n < len(independents) + 2:
        return {
            "ok": False,
            "error": {"type": "ValueError", "message": "insufficient observations"},
        }
    rhs = " + ".join(independents)
    formula = f"{dependent} ~ {rhs}"
    if family == "logistic":
        model = _sm_logit(formula, data=sub).fit(disp=0)
    elif robust:
        model = _sm_ols(formula, data=sub).fit(cov_type="HC3")
    else:
        model = _sm_ols(formula, data=sub).fit()
    out: dict[str, Any] = {
        "family": family,
        "dependent": dependent,
        "independents": independents,
        "n": n,
        "r_squared": float(model.rsquared) if hasattr(model, "rsquared") else None,
        "adj_r_squared": float(model.rsquared_adj)
        if hasattr(model, "rsquared_adj")
        else None,
        "f_stat": float(model.fvalue) if hasattr(model, "fvalue") else None,
        "f_pvalue": float(model.f_pvalue) if hasattr(model, "f_pvalue") else None,
        "aic": float(model.aic) if hasattr(model, "aic") else None,
        "bic": float(model.bic) if hasattr(model, "bic") else None,
        "coefficients": {},
    }
    for name, row in model.params.items():
        try:
            se = float(model.bse[name])
        except Exception:
            se = None
        try:
            ci_low, ci_high = model.conf_int().loc[name].tolist()
        except Exception:
            ci_low, ci_high = (None, None)
        out["coefficients"][str(name)] = {
            "coef": float(row),
            "se": se,
            "t": float(model.tvalues[name])
            if hasattr(model, "tvalues") and name in model.tvalues.index
            else None,
            "p_value": float(model.pvalues[name])
            if hasattr(model, "pvalues") and name in model.pvalues.index
            else None,
            "ci95": [
                round(float(ci_low), 6) if ci_low is not None else None,
                round(float(ci_high), 6) if ci_high is not None else None,
            ],
        }
    # VIF for OLS
    if family == "ols" and len(independents) >= 2:
        try:
            X = _add_const(sub[independents])
            out["vif"] = {
                col: round(float(variance_inflation_factor(X.values, i + 1)), 4)
                for i, col in enumerate(independents)
            }
        except Exception as exc:  # noqa: BLE001
            out["vif_error"] = str(exc)[:120]
    return {"ok": True, "result": out}


# ---------------------------------------------------------------------------
# 7. stat_chi_square
# ---------------------------------------------------------------------------


def stat_chi_square(
    file_path: str,
    var_a: str,
    var_b: str,
    *,
    test: str = "independence",
    expected: Optional[list[list[float]]] = None,
) -> dict:
    """Chi-square test of independence / goodness-of-fit + Fisher's exact."""
    if _ss is None:
        return {
            "ok": False,
            "error": {"type": "ImportError", "message": "scipy not installed"},
        }
    df = _load_dataframe(file_path)
    if var_a not in df.columns or var_b not in df.columns:
        return {
            "ok": False,
            "error": {"type": "ValueError", "message": "var_a or var_b not in dataset"},
        }
    table = pd.crosstab(df[var_a], df[var_b]).values
    out: dict[str, Any] = {
        "var_a": var_a,
        "var_b": var_b,
        "test": test,
        "n": int(table.sum()),
    }
    if test == "independence":
        chi2, p, dof, exp = chi2_contingency(table)
        n = table.sum()
        # Cramér's V
        k = min(table.shape)
        cramers_v = math.sqrt(chi2 / (n * (k - 1))) if n * (k - 1) > 0 else None
        out.update(
            {
                "chi2": float(chi2),
                "dof": int(dof),
                "p_value": float(p),
                "cramers_v": round(float(cramers_v), 4)
                if cramers_v is not None
                else None,
                "expected": [[round(float(v), 4) for v in row] for row in exp],
            }
        )
        if table.shape == (2, 2):
            or_val, p_fisher = fisher_exact(table)
            out["fisher_exact"] = {
                "odds_ratio": round(float(or_val), 4),
                "p_value": float(p_fisher),
            }
    elif test == "gof" and expected is not None:
        observed = table.flatten().astype(float)
        exp_arr = np.asarray(expected, dtype=float).flatten()
        if observed.shape != exp_arr.shape:
            return {
                "ok": False,
                "error": {
                    "type": "ValueError",
                    "message": (
                        f"observed ({observed.shape}) and expected "
                        f"({exp_arr.shape}) shape mismatch"
                    ),
                },
            }
        # scipy.stats.chisquare: first positional = observed; f_exp = expected
        chi2, p = _ss.chisquare(observed, f_exp=exp_arr)
        out.update(
            {
                "chi2": float(chi2),
                "dof": int(max(1, len(observed) - 1)),
                "p_value": float(p),
            }
        )
    else:
        return {
            "ok": False,
            "error": {"type": "ValueError", "message": f"unknown test {test}"},
        }
    return {"ok": True, "result": out}


# ---------------------------------------------------------------------------
# 8. stat_nonparametric
# ---------------------------------------------------------------------------


def stat_nonparametric(
    file_path: str,
    value_col: str,
    group_col: Optional[str] = None,
    *,
    test: str = "wilcoxon",
    mu: float = 0.0,
    subject_col: Optional[str] = None,
) -> dict:
    """Non-parametric tests: Wilcoxon, sign, Friedman, Mann-Whitney.

    For Friedman (repeated-measures across >=3 conditions), pass ``subject_col``
    to identify the within-subject unit. Data may be either long format
    (one row per subject x condition) or wide format (one row per subject,
    one column per condition).
    """
    if _ss is None:
        return {
            "ok": False,
            "error": {"type": "ImportError", "message": "scipy not installed"},
        }
    df = _load_dataframe(file_path)
    if value_col not in df.columns:
        return {
            "ok": False,
            "error": {"type": "ValueError", "message": "value_col not in dataset"},
        }
    out: dict[str, Any] = {"test": test, "value_col": value_col, "mu": mu}
    if test == "wilcoxon":
        if group_col and group_col in df.columns:
            groups = [g[value_col].dropna().values for _, g in df.groupby(group_col)]
            if len(groups) == 2:
                u_stat, p = mannwhitneyu(groups[0], groups[1], alternative="two-sided")
                out.update(
                    {
                        "method": "Mann-Whitney U (via group_col)",
                        "u_stat": float(u_stat),
                        "p_value": float(p),
                    }
                )
            else:
                h_stat, p = kruskal(*groups)
                out.update(
                    {
                        "method": "Kruskal-Wallis H",
                        "H": float(h_stat),
                        "p_value": float(p),
                    }
                )
        else:
            x = df[value_col].dropna().values
            if len(x) < 1:
                return {
                    "ok": False,
                    "error": {"type": "ValueError", "message": "no observations"},
                }
            w_stat, p = wilcoxon(x - mu, alternative="two-sided")
            out.update(
                {
                    "method": "Wilcoxon signed-rank",
                    "W": float(w_stat),
                    "p_value": float(p),
                    "n": int(len(x)),
                }
            )
    elif test == "sign":
        x = df[value_col].dropna().values
        pos = int(np.sum(x > mu))
        neg = int(np.sum(x < mu))
        n = pos + neg
        from scipy.stats import binom

        p = float(2 * binom.cdf(min(pos, neg), n, 0.5))
        out.update(
            {
                "method": "Sign test",
                "n": n,
                "positives": pos,
                "negatives": neg,
                "p_value": p,
            }
        )
    elif test == "friedman":
        if not group_col or group_col not in df.columns:
            return {
                "ok": False,
                "error": {
                    "type": "ValueError",
                    "message": "friedman requires group_col (condition column)",
                },
            }
        # Long format: need a subject column to pivot
        if subject_col and subject_col in df.columns:
            pivot = df.pivot_table(
                index=subject_col,
                columns=group_col,
                values=value_col,
                aggfunc="first",
            ).dropna()
        else:
            # Wide format: assume one row per subject, columns are conditions.
            # The original buggy implementation pivoted on df.index, which
            # collapses a long-format frame to empty. The wide-format case
            # still works because each row in the wide frame is one subject.
            pivot = df
        if pivot.shape[1] < 3 or pivot.shape[0] < 2:
            return {
                "ok": False,
                "error": {
                    "type": "ValueError",
                    "message": (
                        "friedman requires >= 3 conditions and >= 2 subjects "
                        f"(got shape {pivot.shape})"
                    ),
                },
            }
        f_stat, p = friedmanchisquare(
            *[pivot[c].dropna().values for c in pivot.columns]
        )
        out.update(
            {
                "method": "Friedman",
                "Q": float(f_stat),
                "p_value": float(p),
                "k_groups": int(pivot.shape[1]),
                "n_subjects": int(pivot.shape[0]),
                "subject_col": subject_col,
            }
        )
    else:
        return {
            "ok": False,
            "error": {"type": "ValueError", "message": f"unknown test {test}"},
        }
    return {"ok": True, "result": out}


# ---------------------------------------------------------------------------
# 9. stat_effect_size
# ---------------------------------------------------------------------------


def stat_effect_size(
    *,
    kind: str,
    x: Optional[list[float]] = None,
    y: Optional[list[float]] = None,
    var_a: Optional[str] = None,
    var_b: Optional[str] = None,
    file_path: Optional[str] = None,
) -> dict:
    """Effect size: Cohen's d, η², Cramér's V, odds ratio, rank-biserial."""
    if _ss is None:
        return {
            "ok": False,
            "error": {"type": "ImportError", "message": "scipy not installed"},
        }
    kind = kind.lower()
    out: dict[str, Any] = {"kind": kind}
    if kind in ("cohens_d", "cohen") and x is not None and y is not None:
        if not x or not y:
            return {
                "ok": False,
                "error": {
                    "type": "ValueError",
                    "message": "x and y required for Cohen's d",
                },
            }
        nx, ny = len(x), len(y)
        mx, my = float(np.mean(x)), float(np.mean(y))
        sx, sy = float(np.std(x, ddof=1)), float(np.std(y, ddof=1))
        pooled = math.sqrt(((nx - 1) * sx**2 + (ny - 1) * sy**2) / (nx + ny - 2))
        d = (mx - my) / pooled if pooled > 0 else None
        out["value"] = round(float(d), 4) if d is not None else None
        out["n1"], out["n2"] = nx, ny
        # 95% CI
        se = (
            math.sqrt((nx + ny) / (nx * ny) + d**2 / (2 * (nx + ny)))
            if d is not None
            else None
        )
        out["ci95"] = _ci(float(d), se, nx + ny)
    elif kind == "eta_squared" and file_path and var_a:
        # From ANOVA: var_a = value column, var_b = grouping column.
        if var_b is None:
            return {
                "ok": False,
                "error": {
                    "type": "ValueError",
                    "message": "var_b (group column) required for eta_squared",
                },
            }
        df = _load_dataframe(file_path)
        if var_a not in df.columns:
            return {
                "ok": False,
                "error": {
                    "type": "ValueError",
                    "message": f"var_a '{var_a}' not in dataset",
                },
            }
        if var_b not in df.columns:
            return {
                "ok": False,
                "error": {
                    "type": "ValueError",
                    "message": f"var_b '{var_b}' not in dataset",
                },
            }
        groups = [g[var_a].dropna().values for _, g in df.groupby(var_b)]
        groups = [g for g in groups if len(g) > 0]
        if len(groups) < 2:
            return {
                "ok": False,
                "error": {
                    "type": "ValueError",
                    "message": "eta_squared requires >= 2 groups",
                },
            }
        all_data = np.concatenate(groups)
        grand_mean = float(np.mean(all_data))
        ss_between = sum(len(g) * (float(np.mean(g)) - grand_mean) ** 2 for g in groups)
        ss_total = float(np.sum((all_data - grand_mean) ** 2))
        eta2 = ss_between / ss_total if ss_total > 0 else None
        out["value"] = round(float(eta2), 4) if eta2 is not None else None
        out["n_groups"] = len(groups)
        out["value_col"] = var_a
        out["group_col"] = var_b
    elif kind in ("cramers_v", "cramer") and file_path and var_a and var_b:
        df = _load_dataframe(file_path)
        table = pd.crosstab(df[var_a], df[var_b]).values
        chi2, _, _, _ = chi2_contingency(table)
        n = table.sum()
        k = min(table.shape)
        cramers = math.sqrt(chi2 / (n * (k - 1))) if n * (k - 1) > 0 else None
        out["value"] = round(float(cramers), 4) if cramers is not None else None
    elif kind in ("odds_ratio", "or") and file_path and var_a and var_b:
        df = _load_dataframe(file_path)
        table = pd.crosstab(df[var_a], df[var_b]).values
        if table.shape == (2, 2):
            or_val, _ = fisher_exact(table)
            out["value"] = round(float(or_val), 4)
        else:
            return {
                "ok": False,
                "error": {
                    "type": "ValueError",
                    "message": "odds_ratio requires 2x2 table",
                },
            }
    elif kind in ("rank_biserial", "rbs") and x is not None and y is not None:
        # Rank-biserial correlation: r = 1 - 2U / (n1 * n2)
        # Uses the Mann-Whitney U convention where U = sum of ranks in x.
        nx, ny = len(x), len(y)
        if not x or not y:
            return {
                "ok": False,
                "error": {
                    "type": "ValueError",
                    "message": "x and y required for rank-biserial",
                },
            }
        try:
            u_stat, _ = mannwhitneyu(x, y, alternative="two-sided")
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "error": {"type": exc.__class__.__name__, "message": str(exc)[:120]},
            }
        r = 1.0 - (2.0 * float(u_stat)) / (nx * ny)
        out["value"] = round(float(r), 4)
        out["n1"], out["n2"] = nx, ny
        out["u_stat"] = float(u_stat)
    else:
        return {
            "ok": False,
            "error": {
                "type": "ValueError",
                "message": f"unsupported kind={kind} or missing params",
            },
        }
    return {"ok": True, "result": out}


# ---------------------------------------------------------------------------
# 10. stat_power
# ---------------------------------------------------------------------------


def stat_power(
    *,
    test: str,
    effect_size: float,
    alpha: float = 0.05,
    power: Optional[float] = None,
    nobs: Optional[int] = None,
    alternative: str = "two-sided",
    df_num: Optional[int] = None,
    ratio: float = 1.0,
) -> dict:
    """Statistical power: solve for power, sample size, or sensitivity.

    Parameters
    ----------
    test : str
        One of "t" (two-sample t), "f" (one-way F), "chi2" (chi-square GOF),
        or "z" (two-proportion z).
    effect_size : float
        Cohen's d (t), Cohen's f (f), w (chi2), or h (z).
    alpha : float
        Significance level (default 0.05).
    power : float, optional
        Target power. Mutually exclusive with ``nobs``.
    nobs : int, optional
        Sample size. Mutually exclusive with ``power``.
    alternative : str
        "two-sided" (default), "larger", or "smaller".
    df_num : int, optional
        Numerator df for the F-test (= k - 1 for one-way ANOVA). Required
        when ``test="f"``; ignored for other tests.
    ratio : float
        Sample-size ratio for the second group vs. the first (t / z tests).
        Default 1.0 (equal groups).
    """
    if _sm_power is None:
        return {
            "ok": False,
            "error": {"type": "ImportError", "message": "statsmodels not installed"},
        }
    test = test.lower()
    if test == "t":
        analyzer = _sm_power.TTestIndPower()
        nobs_kw = "nobs1"
    elif test == "f":
        # One-way ANOVA power. Uses FTestAnovaPower with k_groups = df_num + 1.
        # df_num = k - 1 where k = number of groups. Default df_num=1 (k=2).
        k_groups = (int(df_num) + 1) if df_num is not None else 2
        analyzer = _sm_power.FTestAnovaPower()
        nobs_kw = "nobs"
        f_kw = "k_groups"
    elif test == "chi2":
        analyzer = _sm_power.GofChisquarePower()
        nobs_kw = "nobs"
    elif test == "z":
        # Two-proportion z-test (Cohen's h). Uses NormalIndPower.
        if not hasattr(_sm_power, "NormalIndPower"):
            return {
                "ok": False,
                "error": {
                    "type": "ImportError",
                    "message": "statsmodels >= 0.14 required for z-test power",
                },
            }
        analyzer = _sm_power.NormalIndPower()
        nobs_kw = "nobs1"
    else:
        return {
            "ok": False,
            "error": {"type": "ValueError", "message": f"unknown test {test}"},
        }
    out: dict[str, Any] = {
        "test": test,
        "effect_size": effect_size,
        "alpha": alpha,
        "alternative": alternative,
    }
    if df_num is not None:
        out["df_num"] = int(df_num)
    if nobs is None and power is not None:
        kwargs: dict[str, Any] = dict(
            effect_size=effect_size,
            alpha=alpha,
            power=power,
        )
        if test in ("t", "z"):
            kwargs["ratio"] = ratio
            kwargs["alternative"] = alternative
        if test == "f":
            kwargs[f_kw] = k_groups
        out["solved_nobs"] = int(math.ceil(analyzer.solve_power(**kwargs)))
        if test == "f":
            out["k_groups"] = k_groups
    elif power is None and nobs is not None:
        kwargs = dict(
            effect_size=effect_size,
            alpha=alpha,
            power=None,
        )
        if test == "f":
            kwargs[f_kw] = k_groups
        elif test in ("t", "z"):
            kwargs["ratio"] = ratio
            kwargs["alternative"] = alternative
        kwargs[nobs_kw] = int(nobs)
        out["solved_power"] = float(analyzer.solve_power(**kwargs))
        if test == "f":
            out["k_groups"] = k_groups
    else:
        return {
            "ok": False,
            "error": {
                "type": "ValueError",
                "message": "supply exactly one of power or nobs",
            },
        }
    return {"ok": True, "result": out}


# ---------------------------------------------------------------------------
# 11. stat_outliers
# ---------------------------------------------------------------------------


def stat_outliers(
    file_path: str,
    columns: list[str],
    *,
    method: str = "iqr",
    threshold: float = 1.5,
) -> dict:
    """Outlier detection: IQR, z-score, modified z, Mahalanobis."""
    df = _load_dataframe(file_path)
    cols = [c for c in columns if c in df.columns]
    if not cols:
        return {
            "ok": False,
            "error": {"type": "ValueError", "message": "no valid columns"},
        }
    method = method.lower()
    per_column: dict[str, Any] = {}
    if method == "mahalanobis" and len(cols) < 2:
        return {
            "ok": False,
            "error": {
                "type": "ValueError",
                "message": (f"mahalanobis requires >= 2 columns, got {len(cols)}"),
            },
        }
    if method == "mahalanobis" and len(cols) >= 2:
        sub = df[cols].dropna()
        if len(sub) >= len(cols) + 1:
            from numpy.linalg import LinAlgError

            cov = np.cov(sub.values, rowvar=False)
            try:
                inv_cov = np.linalg.inv(cov)
                mean = sub.mean().values
                diff = sub.values - mean
                d2 = np.einsum("ij,jk,ik->i", diff, inv_cov, diff)
                d = np.sqrt(d2)
                cutoff = (
                    float(np.sqrt(_ss.chi2.ppf(0.975, df=len(cols))))
                    if _ss is not None
                    else float(np.sqrt(5.991))
                )
                mask = d > cutoff
                per_column["__mahalanobis__"] = {
                    "method": "Mahalanobis",
                    "n": int(len(sub)),
                    "cutoff_d": round(cutoff, 4),
                    "n_outliers": int(mask.sum()),
                    "outlier_indices": sorted(
                        int(i) for i in np.where(mask)[0].tolist()
                    ),
                    "max_d": round(float(d.max()), 4),
                }
            except LinAlgError as exc:
                return {
                    "ok": False,
                    "error": {"type": "LinAlgError", "message": str(exc)},
                }
    else:
        for c in cols:
            s = df[c].dropna()
            if not pd.api.types.is_numeric_dtype(s) or len(s) < 3:
                continue
            n = int(len(s))
            if method == "z" or method == "zscore":
                z = (s - s.mean()) / s.std(ddof=0) if s.std(ddof=0) > 0 else s * 0
                mask = z.abs() > threshold
                per_column[c] = {
                    "method": "z-score",
                    "threshold": float(threshold),
                    "n": n,
                    "n_outliers": int(mask.sum()),
                    "outlier_indices": sorted(
                        int(i) for i in np.where(mask.values)[0].tolist()
                    ),
                    "outlier_values": [float(v) for v in s[mask].head(20).tolist()],
                }
            elif method == "modified_z":
                med = float(s.median())
                mad = float((s - med).abs().median())
                if mad == 0:
                    mz = s * 0
                else:
                    mz = 0.6745 * (s - med) / mad
                mask = mz.abs() > threshold
                per_column[c] = {
                    "method": "modified z (Iglewicz–Hoaglin)",
                    "threshold": float(threshold),
                    "n": n,
                    "n_outliers": int(mask.sum()),
                    "outlier_indices": sorted(
                        int(i) for i in np.where(mask.values)[0].tolist()
                    ),
                    "outlier_values": [float(v) for v in s[mask].head(20).tolist()],
                }
            elif method == "iqr":
                q1 = float(s.quantile(0.25))
                q3 = float(s.quantile(0.75))
                iqr = q3 - q1
                lo, hi = q1 - threshold * iqr, q3 + threshold * iqr
                mask = (s < lo) | (s > hi)
                per_column[c] = {
                    "method": "IQR (Tukey fences)",
                    "threshold": float(threshold),
                    "q1": q1,
                    "q3": q3,
                    "iqr": iqr,
                    "lower_fence": lo,
                    "upper_fence": hi,
                    "n": n,
                    "n_outliers": int(mask.sum()),
                    "outlier_indices": sorted(
                        int(i) for i in np.where(mask.values)[0].tolist()
                    ),
                    "outlier_values": [float(v) for v in s[mask].head(20).tolist()],
                }
            else:
                return {
                    "ok": False,
                    "error": {
                        "type": "ValueError",
                        "message": f"unknown method {method}",
                    },
                }
    return {"ok": True, "per_column": per_column, "n_columns": len(per_column)}


# ---------------------------------------------------------------------------
# 12. stat_missing
# ---------------------------------------------------------------------------


def stat_missing(file_path: str) -> dict:
    """Missing-data profile: counts, percentages, MCAR approximation."""
    df = _load_dataframe(file_path)
    n = int(len(df))
    per_column = []
    for c in df.columns:
        miss = int(df[c].isna().sum())
        per_column.append(
            {
                "column": c,
                "dtype": str(df[c].dtype),
                "n_missing": miss,
                "pct_missing": round(100.0 * miss / n, 2) if n else 0.0,
            }
        )
    # Pattern: any full-row missing?
    complete_rows = int(df.dropna(how="any").shape[0])
    # MCAR approximation: missingness correlation with other variables
    mcar_sketch: dict[str, Any] = {}
    for c in df.columns:
        if df[c].isna().sum() > 0 and df[c].isna().sum() < n:
            others = [x for x in df.columns if x != c]
            for o in others[:5]:  # cap to first 5
                if df[o].dtype.kind in "biufc":
                    from scipy.stats import pointbiserialr

                    mask = df[o].notna()
                    r, p = pointbiserialr(
                        df.loc[mask, c].isna().astype(int), df.loc[mask, o]
                    )
                    if p < 0.05:
                        mcar_sketch.setdefault(c, []).append(
                            {
                                "predictor": o,
                                "r": round(float(r), 4),
                                "p_value": round(float(p), 6),
                            }
                        )
    return {
        "ok": True,
        "n_rows": n,
        "complete_rows": complete_rows,
        "complete_rows_pct": round(100.0 * complete_rows / n, 2) if n else 0.0,
        "per_column": per_column,
        "n_columns": len(per_column),
        "mcar_associations": mcar_sketch,
    }


# ──────────────────────────────────────────────────────────────────────────────
# stat_reliability — Cronbach's alpha for scale reliability
# (survey research, questionnaire validation)
# ──────────────────────────────────────────────────────────────────────────────


def stat_reliability(path: str, columns: list[str]) -> dict[str, Any]:
    _verify_deps()
    df = _load_dataframe(path)
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(f"Columns not found in dataset: {missing}")
    sub = df[columns].dropna()
    n_items = len(columns)
    n_subjects = len(sub)
    if n_subjects < 2:
        raise ValueError(
            f"Need at least 2 complete rows for reliability, got {n_subjects}."
        )
    if n_items < 2:
        raise ValueError("Need at least 2 items for Cronbach's alpha.")
    item_var = sub.var(ddof=1)
    total_var = sub.sum(axis=1).var(ddof=1)
    alpha = (n_items / (n_items - 1)) * (1 - item_var.sum() / total_var)
    # item-level diagnostics
    item_diagnostics = []
    for c in columns:
        without = [x for x in columns if x != c]
        sub_without = sub[without]
        var_without = sub_without.sum(axis=1).var(ddof=1)
        if n_items > 2:
            alpha_without = ((n_items - 1) / (n_items - 2)) * (
                1 - sub_without.var(ddof=1).sum() / var_without
            )
        else:
            alpha_without = None
        item_diagnostics.append(
            {
                "item": c,
                "n": int(sub[c].notna().sum()),
                "mean": round(float(sub[c].mean()), 4),
                "sd": round(float(sub[c].std(ddof=1)), 4),
                "alpha_if_deleted": round(alpha_without, 4) if alpha_without else None,
            }
        )
    interpretation = (
        "Excellent"
        if alpha >= 0.9
        else "Good"
        if alpha >= 0.8
        else "Acceptable"
        if alpha >= 0.7
        else "Questionable"
        if alpha >= 0.6
        else "Poor"
        if alpha >= 0.5
        else "Unacceptable"
    )
    return {
        "ok": True,
        "n_items": n_items,
        "n_subjects": n_subjects,
        "cronbach_alpha": round(float(alpha), 4),
        "interpretation": interpretation,
        "item_diagnostics": item_diagnostics,
    }


# ──────────────────────────────────────────────────────────────────────────────
# stat_frequencies — frequency tables for categorical/ordinal variables
# ──────────────────────────────────────────────────────────────────────────────


def stat_frequencies(path: str, columns: list[str]) -> dict[str, Any]:
    df = _load_dataframe(path)
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(f"Columns not found in dataset: {missing}")
    tables = []
    for c in columns:
        tables.append(frequency_table(df[c]))
    return {"ok": True, "n_variables": len(tables), "tables": tables}


# ──────────────────────────────────────────────────────────────────────────────
# stat_describe_all — describe all numeric columns at once
# ──────────────────────────────────────────────────────────────────────────────


def stat_describe_all(path: str) -> dict[str, Any]:
    df = _load_dataframe(path)
    numeric = df.select_dtypes(include="number")
    if numeric.empty:
        return {
            "ok": True,
            "n_numeric": 0,
            "message": "No numeric columns found in dataset.",
            "columns": [],
        }
    results = []
    for c in numeric.columns:
        s = numeric[c].dropna()
        q = s.quantile([0.25, 0.5, 0.75])
        results.append(
            {
                "column": c,
                "n": int(len(s)),
                "missing": int(numeric[c].isna().sum()),
                "mean": round(float(s.mean()), 4),
                "sd": round(float(s.std(ddof=1)), 4),
                "min": round(float(s.min()), 4),
                "q25": round(float(q.iloc[0]), 4),
                "median": round(float(q.iloc[1]), 4),
                "q75": round(float(q.iloc[2]), 4),
                "max": round(float(s.max()), 4),
                "skew": round(float(s.skew()), 4),
                "kurtosis": round(float(s.kurtosis()), 4),
            }
        )
    return {"ok": True, "n_numeric": len(results), "columns": results}


__all__ = [
    "stat_descriptives",
    "stat_assumptions",
    "stat_compare_groups",
    "stat_anova",
    "stat_correlate",
    "stat_regress",
    "stat_chi_square",
    "stat_nonparametric",
    "stat_effect_size",
    "stat_power",
    "stat_outliers",
    "stat_missing",
    "stat_reliability",
    "stat_frequencies",
    "stat_describe_all",
]
