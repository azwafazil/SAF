"""SAF MCP server."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

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
from .stats import (
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

mcp = FastMCP("SAF")


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


@mcp.resource("saf://guide")
def guide() -> str:
    return (
        "SAF -- Statistical Analysis Forge -- is a privacy-first MCP server for "
        "SPSS-compatible datasets. Use it to inspect metadata, preview rows, profile "
        "variables, convert files, and generate basic SPSS syntax. SAF does not execute "
        "SPSS syntax and does not access files outside SAF_DATA_ROOT."
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
        "Analyze the SPSS-compatible dataset at this SAF sandbox path: "
        f"{path}\n\n"
        "First inspect metadata, then preview a small number of rows, then profile "
        "variables. Do not request data outside SAF_DATA_ROOT. Summarize data quality, "
        "missingness, notable labels, and reasonable next analysis steps."
    )


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
