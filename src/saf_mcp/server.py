"""SAF MCP server."""

from __future__ import annotations

import os
from typing import Any

import pandas as pd
from mcp.server.fastmcp import FastMCP

from .security import (
    SPSS_EXTENSIONS,
    TABULAR_EXTENSIONS,
    SUPPORTED_EXTENSIONS,
    SAFSecurityError,
    get_data_root,
    relative_to_root,
    require_existing_dataset,
    resolve_output_path,
)
from .spss_utils import (
    basic_spss_syntax,
    dataframe_preview,
    metadata_to_dict,
    profile_dataframe,
    read_spss,
    read_tabular,
    write_csv,
    write_sav,
)
from .spss_utils import frequency_table

from .stats import (
    stat_anova,
    stat_assumptions,
    stat_chi_square,
    stat_compare_groups,
    stat_correlate,
    stat_describe_all,
    stat_descriptives,
    stat_effect_size,
    stat_frequencies,
    stat_missing,
    stat_nonparametric,
    stat_outliers,
    stat_power,
    stat_regress,
    stat_reliability,
)

SAF_HOST = os.environ.get("SAF_HOST", "127.0.0.1")
SAF_PORT = int(os.environ.get("SAF_PORT", "8000"))

mcp = FastMCP("SAF", host=SAF_HOST, port=SAF_PORT)


def _error(error: Exception) -> dict[str, Any]:
    return {
        "ok": False,
        "error": {
            "type": error.__class__.__name__,
            "message": str(error),
        },
    }


def _success(**payload: Any) -> dict[str, Any]:
    return {"ok": True, **payload}


@mcp.tool()
def list_data_files() -> dict[str, Any]:
    """List supported dataset files under SAF_DATA_ROOT."""
    try:
        root = get_data_root()
        if not root.exists():
            return _success(data_root=str(root), files=[])

        files = []
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
                files.append(
                    {
                        "path": relative_to_root(path),
                        "extension": path.suffix.lower(),
                        "size_bytes": path.stat().st_size,
                    }
                )
        return _success(
            data_root=str(root), files=sorted(files, key=lambda item: item["path"])
        )
    except Exception as exc:  # noqa: BLE001 - MCP tools should return structured errors.
        return _error(exc)


@mcp.tool()
def inspect_spss_metadata(path: str) -> dict[str, Any]:
    """Inspect metadata for a .sav, .zsav, or .por file."""
    try:
        dataset_path = require_existing_dataset(path, SPSS_EXTENSIONS)
        _, metadata = read_spss(dataset_path, metadata_only=True)
        return _success(
            path=relative_to_root(dataset_path), metadata=metadata_to_dict(metadata)
        )
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
def preview_spss_data(path: str, rows: int = 20) -> dict[str, Any]:
    """Preview rows from a .sav, .zsav, or .por file."""
    try:
        if rows < 1 or rows > 500:
            raise ValueError("rows must be between 1 and 500.")
        dataset_path = require_existing_dataset(path, SPSS_EXTENSIONS)
        df, metadata = read_spss(dataset_path, rows=rows)
        return _success(
            path=relative_to_root(dataset_path),
            requested_rows=rows,
            preview=dataframe_preview(df),
            metadata=metadata_to_dict(metadata),
        )
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
def profile_spss_data(path: str, rows: int | None = 5000) -> dict[str, Any]:
    """Profile variables in a .sav, .zsav, or .por file."""
    try:
        if rows is not None and (rows < 1 or rows > 100000):
            raise ValueError("rows must be between 1 and 100000, or null.")
        dataset_path = require_existing_dataset(path, SPSS_EXTENSIONS)
        df, metadata = read_spss(dataset_path, rows=rows)
        return _success(
            path=relative_to_root(dataset_path),
            sampled_rows=rows,
            profile=profile_dataframe(df),
            metadata=metadata_to_dict(metadata),
        )
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
def convert_spss_to_csv(path: str, output_path: str) -> dict[str, Any]:
    """Convert a .sav, .zsav, or .por file to CSV inside SAF_DATA_ROOT."""
    try:
        dataset_path = require_existing_dataset(path, SPSS_EXTENSIONS)
        csv_path = resolve_output_path(output_path, {".csv"})
        df, _ = read_spss(dataset_path)
        write_csv(df, csv_path)
        return _success(
            input_path=relative_to_root(dataset_path),
            output_path=relative_to_root(csv_path),
            rows_written=int(len(df)),
            columns_written=int(len(df.columns)),
        )
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
def convert_csv_to_sav(path: str, output_path: str) -> dict[str, Any]:
    """Convert a CSV or TSV file to .sav inside SAF_DATA_ROOT."""
    try:
        tabular_path = require_existing_dataset(path, TABULAR_EXTENSIONS)
        sav_path = resolve_output_path(output_path, {".sav"})
        df = read_tabular(tabular_path)
        write_sav(df, sav_path)
        return _success(
            input_path=relative_to_root(tabular_path),
            output_path=relative_to_root(sav_path),
            rows_written=int(len(df)),
            columns_written=int(len(df.columns)),
        )
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
def generate_basic_spss_syntax(
    path: str, variables: list[str] | None = None
) -> dict[str, Any]:
    """Generate basic SPSS syntax without executing it."""
    try:
        dataset_path = require_existing_dataset(path, SPSS_EXTENSIONS)
        if variables is not None:
            _, metadata = read_spss(dataset_path, metadata_only=True)
            known_variables = set(metadata_to_dict(metadata)["columns"])
            unknown = sorted(set(variables) - known_variables)
            if unknown:
                raise ValueError(f"Unknown variables: {', '.join(unknown)}")
        syntax = basic_spss_syntax(relative_to_root(dataset_path), variables)
        return _success(path=relative_to_root(dataset_path), syntax=syntax)
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


# ═══════════════════════════════════════════════════════════════════════════════
# Statistical analysis tools (12 stat_* primitives)
# Donated 2026-06-02 by Muhammad Arif bin Fazil <ariffazil@arif-fazil.com>
# Originally forged as part of the arifOS sovereign organ (decommissioned);
# ported to upstream-style (no F1-F13, no VAULT999) for inclusive reuse.
# ═══════════════════════════════════════════════════════════════════════════════


@mcp.tool()
def saf_stat_descriptives(path: str, columns: list[str]) -> dict[str, Any]:
    """Univariate summary (n, mean, sd, median, min, max, IQR, MAD, skew, kurtosis, 95% CI)."""
    try:
        return stat_descriptives(path, columns)
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
def saf_stat_assumptions(
    path: str, columns: list[str], group_col: str | None = None
) -> dict[str, Any]:
    """Shapiro-Wilk normality (D'Agostino fallback for n>5000) + Levene homoscedasticity."""
    try:
        return stat_assumptions(path, columns, group_col)
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
def saf_stat_compare_groups(
    path: str,
    value_col: str,
    group_col: str,
    paired: bool = False,
    parametric: bool = True,
    equal_var: bool = False,
) -> dict[str, Any]:
    """Two-group comparison: t-test (indep/paired/Welch) + Mann-Whitney, with Cohen's d."""
    try:
        return stat_compare_groups(
            path,
            value_col,
            group_col,
            paired=paired,
            parametric=parametric,
            equal_var=equal_var,
        )
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
def saf_stat_anova(
    path: str,
    value_col: str,
    group_col: str,
    welch: bool = False,
    post_hoc: bool = True,
) -> dict[str, Any]:
    """One-way ANOVA: classic / Welch / Kruskal-Wallis, with optional Tukey HSD."""
    try:
        return stat_anova(path, value_col, group_col, welch=welch, post_hoc=post_hoc)
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
def saf_stat_correlate(
    path: str,
    x: str,
    y: str,
    method: str = "pearson",
    alpha: float = 0.05,
    bootstrap: int = 0,
    seed: int | None = None,
) -> dict[str, Any]:
    """Correlation: Pearson / Spearman / Kendall with CI.

    Pearson: 95% CI via Fisher z-transform.
    Spearman / Kendall: CI via percentile bootstrap when ``bootstrap > 0``.
    Set ``seed`` for reproducible bootstrap.
    """
    try:
        return stat_correlate(
            path,
            x,
            y,
            method=method,
            alpha=alpha,
            bootstrap=bootstrap,
            seed=seed,
        )
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
def saf_stat_regress(
    path: str,
    dependent: str,
    independents: list[str],
    family: str = "ols",
    robust: bool = False,
) -> dict[str, Any]:
    """OLS / logistic / robust (HC3) regression with coefficients, CIs, AIC/BIC, VIF (OLS)."""
    try:
        return stat_regress(path, dependent, independents, family=family, robust=robust)
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
def saf_stat_chi_square(
    path: str,
    var_a: str,
    var_b: str,
    test: str = "independence",
    expected: list[list[float]] | None = None,
) -> dict[str, Any]:
    """Chi-square test of independence / goodness-of-fit + Fisher's exact (2x2)."""
    try:
        return stat_chi_square(path, var_a, var_b, test=test, expected=expected)
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
def saf_stat_nonparametric(
    path: str,
    value_col: str,
    group_col: str | None = None,
    test: str = "wilcoxon",
    mu: float = 0.0,
    subject_col: str | None = None,
) -> dict[str, Any]:
    """Non-parametric tests: Wilcoxon, sign, Friedman, Mann-Whitney (auto), Kruskal-Wallis (auto).

    For Friedman (repeated-measures, >=3 conditions), pass ``subject_col``
    to identify within-subject units when data is in long format.
    """
    try:
        return stat_nonparametric(
            path,
            value_col,
            group_col,
            test=test,
            mu=mu,
            subject_col=subject_col,
        )
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
def saf_stat_effect_size(
    kind: str,
    x: list[float] | None = None,
    y: list[float] | None = None,
    file_path: str | None = None,
    var_a: str | None = None,
    var_b: str | None = None,
) -> dict[str, Any]:
    """Effect size: Cohen's d, η², Cramér's V, odds ratio, rank-biserial.

    Kinds:
      - "cohens_d" / "cohen":  x, y required (raw samples)
      - "eta_squared":         file_path, var_a=value_col, var_b=group_col
      - "cramers_v" / "cramer": file_path, var_a, var_b (categorical)
      - "odds_ratio" / "or":   file_path, var_a, var_b (2x2 table)
      - "rank_biserial" / "rbs": x, y required (raw samples)
    """
    try:
        return stat_effect_size(
            kind=kind,
            x=x,
            y=y,
            file_path=file_path,
            var_a=var_a,
            var_b=var_b,
        )
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
def saf_stat_power(
    test: str,
    effect_size: float,
    alpha: float = 0.05,
    power: float | None = None,
    nobs: int | None = None,
    alternative: str = "two-sided",
    df_num: int | None = None,
    ratio: float = 1.0,
) -> dict[str, Any]:
    """Statistical power: solve for power, sample size, or sensitivity.

    Supported tests: "t" (two-sample t, Cohen's d), "f" (one-way F, Cohen's f;
    requires ``df_num`` = k-1), "chi2" (chi-square GOF, Cohen's w),
    "z" (two-proportion z, Cohen's h).
    """
    try:
        return stat_power(
            test=test,
            effect_size=effect_size,
            alpha=alpha,
            power=power,
            nobs=nobs,
            alternative=alternative,
            df_num=df_num,
            ratio=ratio,
        )
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
def saf_stat_outliers(
    path: str,
    columns: list[str],
    method: str = "iqr",
    threshold: float = 1.5,
) -> dict[str, Any]:
    """Outlier detection: IQR (Tukey), z-score, modified z (Iglewicz-Hoaglin), Mahalanobis (multi)."""
    try:
        return stat_outliers(path, columns, method=method, threshold=threshold)
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
def saf_stat_missing(path: str) -> dict[str, Any]:
    """Missing-data profile: per-column counts/pcts, complete-row ratio, MCAR association sketch."""
    try:
        return stat_missing(path)
    except Exception as exc:  # noqa: BLE001
        return _error(exc)


@mcp.tool()
def saf_stat_frequencies(path: str, columns: list[str]) -> dict[str, Any]:
    """Frequency tables for categorical or ordinal variables: counts, percentages, cumulative."""
    try:
        return stat_frequencies(path, columns)
    except Exception as exc:
        return _error(exc)


@mcp.tool()
def saf_stat_reliability(path: str, columns: list[str]) -> dict[str, Any]:
    """Cronbach's alpha for scale reliability. Minimum 2 items, listwise deletion."""
    try:
        return stat_reliability(path, columns)
    except Exception as exc:
        return _error(exc)


@mcp.tool()
def saf_stat_describe_all(path: str) -> dict[str, Any]:
    """Describe all numeric columns at once: n, mean, sd, quartiles, skew, kurtosis."""
    try:
        return stat_describe_all(path)
    except Exception as exc:
        return _error(exc)


@mcp.tool()
def cross_tabulation(
    path: str, row_var: str, col_var: str, percentages: str = "none"
) -> dict[str, Any]:
    """Cross-tabulation (contingency table) between two categorical variables.

    Parameters
    ----------
    path : str  Path relative to SAF_DATA_ROOT.
    row_var : str  Variable name for rows.
    col_var : str  Variable name for columns.
    percentages : str  One of "none", "row", "column", "total".
        When "row", each cell shows row-wise percentage.
        When "column", each cell shows column-wise percentage.
        When "total", each cell shows percentage of grand total.
    """
    try:
        from .stats import _load_dataframe

        df = _load_dataframe(path)
        if row_var not in df.columns:
            raise ValueError(f"Row variable not found: {row_var}")
        if col_var not in df.columns:
            raise ValueError(f"Column variable not found: {col_var}")
        ct = pd.crosstab(df[row_var], df[col_var], margins=True, margins_name="Total")
        result = {
            "row_variable": row_var,
            "col_variable": col_var,
            "n": int(len(df)),
            "table": {
                str(idx): {str(c): int(ct.loc[idx, c]) for c in ct.columns}
                for idx in ct.index
            },
            "columns": [str(c) for c in ct.columns],
            "index": [str(i) for i in ct.index],
        }
        if percentages != "none":
            pct_map = {"row": "index", "column": "columns", "total": "all"}
            ct_pct = pd.crosstab(
                df[row_var], df[col_var], margins=True, margins_name="Total", normalize=pct_map[percentages]
            )
            result["percentages"] = {
                "type": percentages,
                "table": {
                    str(idx): {str(c): round(float(ct_pct.loc[idx, c]) * 100, 2) for c in ct_pct.columns}
                    for idx in ct_pct.index
                },
            }
        return _success(**result)
    except Exception as exc:
        return _error(exc)


@mcp.tool()
def list_tools() -> dict[str, Any]:
    """List all available SAF MCP tools with descriptions."""
    tools = [
        {"name": "list_data_files", "description": "List supported dataset files under SAF_DATA_ROOT."},
        {"name": "inspect_spss_metadata", "description": "Inspect metadata for a .sav, .zsav, or .por file."},
        {"name": "preview_spss_data", "description": "Preview rows from a .sav, .zsav, or .por file."},
        {"name": "profile_spss_data", "description": "Profile variables in a .sav, .zsav, or .por file."},
        {"name": "convert_spss_to_csv", "description": "Convert a .sav, .zsav, or .por file to CSV."},
        {"name": "convert_csv_to_sav", "description": "Convert a CSV or TSV file to .sav."},
        {"name": "generate_basic_spss_syntax", "description": "Generate basic SPSS syntax for a dataset."},
        {"name": "cross_tabulation", "description": "Cross-tabulation (contingency table) between two categorical variables."},
        {"name": "saf_stat_descriptive", "description": "Univariate summary (n, mean, sd, median, min, max, IQR, MAD, skew, kurtosis, 95% CI)."},
        {"name": "saf_stat_describe_all", "description": "Describe all numeric columns at once."},
        {"name": "saf_stat_frequencies", "description": "Frequency tables for categorical or ordinal variables."},
        {"name": "saf_stat_reliability", "description": "Cronbach's alpha for scale reliability."},
        {"name": "saf_stat_assumptions", "description": "Normality (Shapiro-Wilk) + homoscedasticity (Levene)."},
        {"name": "saf_stat_compare_groups", "description": "Two-group comparison: t-test + Mann-Whitney."},
        {"name": "saf_stat_anova", "description": "One-way ANOVA / Welch / Kruskal-Wallis."},
        {"name": "saf_stat_correlate", "description": "Pearson / Spearman / Kendall correlation with CI."},
        {"name": "saf_stat_regress", "description": "OLS / logistic / robust regression."},
        {"name": "saf_stat_chi_square", "description": "Chi-square test / Fisher exact."},
        {"name": "saf_stat_nonparametric", "description": "Wilcoxon / sign / Friedman."},
        {"name": "saf_stat_effect_size", "description": "Cohen's d, η², Cramér's V, odds ratio."},
        {"name": "saf_stat_power", "description": "Power analysis: solve for N, power, or effect size."},
        {"name": "saf_stat_outliers", "description": "Outlier detection: IQR, z-score, Mahalanobis."},
        {"name": "saf_stat_missing", "description": "Missing-data profile per column."},
    ]
    return _success(tools=tools)


@mcp.resource("saf://guide")
def guide() -> str:
    return (
        "SAF MCP -- Statistical Analysis Framework -- is a privacy-first MCP server "
        "for SPSS-compatible datasets (.sav, .zsav, .por) plus CSV, TSV, and XLSX. "
        "\n\n"
        "Use it to: inspect metadata, preview rows, profile variables, convert file "
        "formats, generate SPSS syntax, run frequencies & crosstabs, assess scale "
        "reliability (Cronbach's alpha), and perform 12 statistical analysis routines "
        "(descriptives, assumptions, group comparisons, ANOVA, correlation, regression, "
        "chi-square, non-parametric, effect size, power, outliers, missing data).\n\n"
        "SAF does not execute SPSS syntax nor access files outside SAF_DATA_ROOT."
    )


@mcp.resource("saf://repo-ingestion")
def repo_ingestion() -> str:
    return (
        "Keep real respondent datasets out of git. Place .sav, .zsav, .por, .csv, and "
        ".tsv files in SAF_DATA_ROOT, then reference paths relative to that directory. "
        "The server validates extensions and blocks traversal outside the sandbox."
    )


@mcp.prompt()
def analyze_dataset_prompt(path: str) -> str:
    return (
        "Analyze the dataset at this SAF sandbox path: "
        f"{path}\n\n"
        "1. Inspect metadata (inspect_spss_metadata)\n"
        "2. Preview a small number of rows (preview_spss_data)\n"
        "3. Profile variables (profile_spss_data)\n"
        "4. Run frequencies on categorical columns (saf_stat_frequencies)\n"
        "5. Describe all numeric columns (saf_stat_describe_all)\n"
        "6. Check missing data patterns (saf_stat_missing)\n\n"
        "Summarize data quality, missingness, notable labels, "
        "and recommend next analysis steps."
    )


@mcp.prompt()
def survey_analysis_prompt(path: str, scale_columns: list[str] | None = None) -> str:
    prompt = (
        "Analyze the survey dataset at this SAF sandbox path: "
        f"{path}\n\n"
        "1. Inspect metadata and preview rows\n"
        "2. Profile all variables\n"
        "3. Run frequencies on all categorical/demographic columns\n"
    )
    if scale_columns:
        prompt += (
            f"4. Assess scale reliability for: {', '.join(scale_columns)} "
            "(saf_stat_reliability)\n"
        )
    prompt += (
        "5. Run descriptives on numeric/scale variables\n"
        "6. Check for outliers\n"
        "7. Run cross-tabulations between key demographic and outcome variables\n"
        "8. Report findings in a clear, structured format"
    )
    return prompt


def main() -> None:
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    try:
        mcp.run(transport=transport)
    except TypeError as exc:
        if transport == "streamable-http":
            raise RuntimeError(
                "Installed MCP package does not support MCP_TRANSPORT=streamable-http. "
                "Upgrade mcp[cli] or run with the default stdio transport."
            ) from exc
        raise


if __name__ == "__main__":
    main()
