from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from .io import list_data_files as _list_data_files
from .io import read_dataset, write_csv_from_sav, write_sav_from_csv
from .metadata import data_dictionary, metadata_to_dict
from .recipes import run_recipe
from .reporting import export_markdown_report as _export_markdown_report
from .stats.descriptive import descriptive, frequencies, missing_profile
from .stats.inferential import chi_square_test, correlation_matrix, one_way_anova, t_test_independent
from .stats.regression import ols_regression
from .stats.reliability import cronbach_alpha
from .syntax import generate_spss_syntax as _generate_spss_syntax

mcp = FastMCP("SAF MCP", json_response=True)


@mcp.tool()
def list_data_files() -> dict[str, Any]:
    """List CSV, Excel, and SPSS files inside SAF_DATA_ROOT."""
    return {"ok": True, "files": _list_data_files()}


@mcp.tool()
def inspect_dataset(file: str) -> dict[str, Any]:
    """Inspect dataset shape, variables, and SPSS metadata if available."""
    df, meta = read_dataset(file)
    return {
        "ok": True,
        "file": file,
        "n_rows": len(df),
        "n_columns": df.shape[1],
        "columns": list(df.columns),
        "metadata": metadata_to_dict(meta),
    }


@mcp.tool()
def preview_dataset(file: str, rows: int = 10) -> dict[str, Any]:
    """Preview the first rows of a dataset."""
    df, _ = read_dataset(file)
    return {"ok": True, "file": file, "rows": df.head(rows).to_dict(orient="records")}


@mcp.tool()
def profile_dataset(file: str) -> dict[str, Any]:
    """Create a basic data dictionary and missing-data profile."""
    df, _ = read_dataset(file)
    return {"ok": True, "dictionary": data_dictionary(file), "missing": missing_profile(df)}


@mcp.tool()
def descriptive_statistics(file: str, variables: list[str]) -> dict[str, Any]:
    """Run descriptive statistics for numeric variables."""
    df, _ = read_dataset(file)
    return descriptive(df, variables)


@mcp.tool()
def frequency_table(file: str, variable: str) -> dict[str, Any]:
    """Run a frequency table for one variable."""
    df, _ = read_dataset(file)
    return frequencies(df, variable)


@mcp.tool()
def cronbach_alpha_tool(file: str, items: list[str]) -> dict[str, Any]:
    """Run Cronbach's alpha for Likert-scale items."""
    df, _ = read_dataset(file)
    return cronbach_alpha(df, items)


@mcp.tool()
def independent_t_test(file: str, dv: str, group: str, group_a: str, group_b: str) -> dict[str, Any]:
    """Run Welch independent samples t-test."""
    df, _ = read_dataset(file)
    return t_test_independent(df, dv, group, group_a, group_b)


@mcp.tool()
def anova_one_way(file: str, dv: str, between: str) -> dict[str, Any]:
    """Run one-way ANOVA."""
    df, _ = read_dataset(file)
    return one_way_anova(df, dv, between)


@mcp.tool()
def chi_square(file: str, row: str, column: str) -> dict[str, Any]:
    """Run chi-square test of independence for two categorical variables."""
    df, _ = read_dataset(file)
    return chi_square_test(df, row, column)


@mcp.tool()
def correlations(file: str, variables: list[str], method: str = "pearson") -> dict[str, Any]:
    """Run Pearson or Spearman correlation matrix."""
    df, _ = read_dataset(file)
    return correlation_matrix(df, variables, method)


@mcp.tool()
def regression_ols(file: str, dv: str, predictors: list[str]) -> dict[str, Any]:
    """Run ordinary least squares regression."""
    df, _ = read_dataset(file)
    return ols_regression(df, dv, predictors)


@mcp.tool()
def generate_spss_syntax(file: str, analyses: list[dict[str, Any]]) -> dict[str, Any]:
    """Generate SPSS syntax text for common analyses. Does not execute SPSS."""
    return {"ok": True, "syntax": _generate_spss_syntax(file, analyses)}


@mcp.tool()
def run_analysis_recipe(file: str, steps_json: str) -> dict[str, Any]:
    """Run a reproducible analysis recipe. steps_json must be a JSON list."""
    steps = json.loads(steps_json)
    if not isinstance(steps, list):
        return {"ok": False, "error": "steps_json must decode to a list."}
    return run_recipe(file, steps)


@mcp.tool()
def export_markdown_report(title: str, results_json: str, output_file: str) -> dict[str, Any]:
    """Export results JSON into a Markdown report inside SAF_DATA_ROOT."""
    results = json.loads(results_json)
    if not isinstance(results, list):
        return {"ok": False, "error": "results_json must decode to a list."}
    return _export_markdown_report(title, results, output_file)


@mcp.tool()
def convert_csv_to_sav(input_csv: str, output_sav: str) -> dict[str, Any]:
    """Convert CSV to SPSS .sav inside SAF_DATA_ROOT."""
    return write_sav_from_csv(input_csv, output_sav)


@mcp.tool()
def convert_sav_to_csv(input_sav: str, output_csv: str) -> dict[str, Any]:
    """Convert SPSS .sav to CSV inside SAF_DATA_ROOT."""
    return write_csv_from_sav(input_sav, output_csv)


@mcp.prompt()
def choose_statistical_test(research_question: str, variables: str) -> str:
    """Prompt template to help a student choose the correct statistical test."""
    return f"""
You are SAF, a statistics tutor. Help the student choose a statistical test.

Research question:
{research_question}

Variables:
{variables}

Return:
1. Independent variable and dependent variable.
2. Measurement level for each variable.
3. Recommended test.
4. Why this test fits.
5. Assumptions to check.
6. SPSS menu path if relevant.
7. SAF MCP tool to call.
""".strip()


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
