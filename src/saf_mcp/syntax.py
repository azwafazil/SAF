"""SPSS Syntax Generator v2 — produces ready-to-run SPSS syntax.

Generates syntax for:
  - DESCRIPTIVES
  - FREQUENCIES
  - CROSSTABS
  - T-TEST (independent, paired, one-sample)
  - ONEWAY (ANOVA)
  - CORRELATIONS
  - REGRESSION
  - RELIABILITY (Cronbach's alpha)
"""

from __future__ import annotations

from typing import Any


def _wrap_line(line: str, indent: int = 4, width: int = 72) -> str:
    """Roughly wrap a long line for readability."""
    if len(line) <= width:
        return " " * indent + line
    break_point = line.rfind(" ", 0, width)
    if break_point < 0:
        return " " * indent + line
    return " " * indent + line[:break_point] + "\n" + _wrap_line(line[break_point + 1:], indent)


def _sanitise(path: str) -> str:
    """Escape single quotes in file paths for SPSS."""
    return path.replace("'", "''")


def syntax_descriptives(dataset_path: str, variables: list[str]) -> str:
    """Generate DESCRIPTIVES syntax."""
    var_line = " ".join(variables)
    return (
        f"GET FILE='{_sanitise(dataset_path)}'.\n"
        f"DATASET NAME SAFDataset WINDOW=FRONT.\n"
        f"DESCRIPTIVES VARIABLES={var_line}\n"
        f"  /STATISTICS=MEAN STDDEV VARIANCE MIN MAX SEMEAN KURTOSIS SKEWNESS.\n"
        f"EXECUTE.\n"
    )


def syntax_frequencies(dataset_path: str, variables: list[str]) -> str:
    """Generate FREQUENCIES syntax."""
    var_line = " ".join(variables)
    return (
        f"GET FILE='{_sanitise(dataset_path)}'.\n"
        f"DATASET NAME SAFDataset WINDOW=FRONT.\n"
        f"FREQUENCIES VARIABLES={var_line}\n"
        f"  /ORDER=ANALYSIS.\n"
        f"EXECUTE.\n"
    )


def syntax_crosstabs(
    dataset_path: str,
    row_var: str,
    col_var: str,
    layer_vars: list[str] | None = None,
    statistics: list[str] | None = None,
) -> str:
    """Generate CROSSTABS syntax.

    Parameters
    ----------
    statistics : list, optional
        SPSS statistics keywords, e.g. ["CHISQ", "PHI", "LAMBDA", "GAMMA"].
        Defaults to ["CHISQ"].
    """
    if statistics is None:
        statistics = ["CHISQ"]
    stat_line = "\n  ".join(f"/STATISTICS={s}" for s in statistics)
    layers = ""
    if layer_vars:
        layers = "\n" + "\n".join(
            f"  /LAYERS={v}" for v in layer_vars
        )
    return (
        f"GET FILE='{_sanitise(dataset_path)}'.\n"
        f"DATASET NAME SAFDataset WINDOW=FRONT.\n"
        f"CROSSTABS\n"
        f"  /TABLES={row_var} BY {col_var}{layers}\n"
        f"  /FORMAT=AVALUE TABLES\n"
        f"  /CELLS=COUNT ROW COLUMN TOTAL{'' if statistics else ''}\n"
        f"{stat_line}\n"
        f"EXECUTE.\n"
    )


def syntax_ttest(
    dataset_path: str,
    value_col: str,
    group_col: str | None = None,
    test_value: float | None = None,
    paired: bool = False,
) -> str:
    """Generate T-TEST syntax.

    Parameters
    ----------
    value_col : str  Dependent variable.
    group_col : str, optional  Grouping variable (independent samples).
    test_value : float, optional  One-sample test value.
    paired : bool  Paired t-test (requires two value columns).
    """
    if paired:
        # value_col contains two space-separated variable names
        return (
            f"GET FILE='{_sanitise(dataset_path)}'.\n"
            f"DATASET NAME SAFDataset WINDOW=FRONT.\n"
            f"T-TEST PAIRS={value_col}\n"
            f"  /CRITERIA=CI(.95)\n"
            f"  /MISSING=ANALYSIS.\n"
            f"EXECUTE.\n"
        )
    if group_col:
        return (
            f"GET FILE='{_sanitise(dataset_path)}'.\n"
            f"DATASET NAME SAFDataset WINDOW=FRONT.\n"
            f"T-TEST GROUPS={group_col}(0 1)\n"
            f"  /MISSING=ANALYSIS\n"
            f"  /VARIABLES={value_col}\n"
            f"  /CRITERIA=CI(.95).\n"
            f"EXECUTE.\n"
        )
    if test_value is not None:
        return (
            f"GET FILE='{_sanitise(dataset_path)}'.\n"
            f"DATASET NAME SAFDataset WINDOW=FRONT.\n"
            f"T-TEST\n"
            f"  /TESTVAL={test_value}\n"
            f"  /MISSING=ANALYSIS\n"
            f"  /VARIABLES={value_col}\n"
            f"  /CRITERIA=CI(.95).\n"
            f"EXECUTE.\n"
        )
    return "T-TEST syntax requires group_col, test_value, or paired=True."


def syntax_oneway(
    dataset_path: str,
    dependent: str,
    factor: str,
    post_hoc: list[str] | None = None,
    contrasts: list[str] | None = None,
    descriptive: bool = True,
    homogeneity: bool = True,
) -> str:
    """Generate ONEWAY (ANOVA) syntax."""
    lines = [
        f"GET FILE='{_sanitise(dataset_path)}'.",
        "DATASET NAME SAFDataset WINDOW=FRONT.",
        f"ONEWAY {dependent} BY {factor}",
    ]
    if descriptive:
        lines.append("  /STATISTICS DESCRIPTIVES")
    if homogeneity:
        lines.append("  /STATISTICS HOMOGENEITY")
    if post_hoc:
        ph = " ".join(post_hoc)
        lines.append(f"  /POSTHOC={ph} ALPHA(0.05)")
    if contrasts:
        lines.append("  /CONTRAST=" + " ".join(contrasts))
    lines.append("  /MISSING ANALYSIS.")
    lines.append("EXECUTE.\n")
    return "\n".join(lines)


def syntax_correlations(
    dataset_path: str,
    variables: list[str],
    print_format: str = "full",
) -> str:
    """Generate CORRELATIONS syntax."""
    var_line = " ".join(variables)
    return (
        f"GET FILE='{_sanitise(dataset_path)}'.\n"
        f"DATASET NAME SAFDataset WINDOW=FRONT.\n"
        f"CORRELATIONS\n"
        f"  /VARIABLES={var_line}\n"
        f"  /PRINT={print_format} TWOTAIL NOSIG\n"
        f"  /MISSING=PAIRWISE.\n"
        f"EXECUTE.\n"
    )


def syntax_regression(
    dataset_path: str,
    dependent: str,
    independents: list[str],
    method: str = "ENTER",
    statistics: list[str] | None = None,
) -> str:
    """Generate REGRESSION syntax.

    Parameters
    ----------
    method : str  ENTER, STEPWISE, BACKWARD, FORWARD.
    statistics : list, optional
        SPSS statistics keywords, e.g. ["R", "ANOVA", "COEFF", "TOL", "ZPP"].
        Defaults to ["R", "ANOVA", "COEFF", "TOL"].
    """
    if statistics is None:
        statistics = ["R", "ANOVA", "COEFF", "TOL"]
    stat_line = "\n  ".join(f"/STATISTICS={s}" for s in statistics)
    ivs = " ".join(independents)
    return (
        f"GET FILE='{_sanitise(dataset_path)}'.\n"
        f"DATASET NAME SAFDataset WINDOW=FRONT.\n"
        f"REGRESSION\n"
        f"  /DESCRIPTIVES MEAN STDDEV CORR SIG N\n"
        f"  /MISSING LISTWISE\n"
        f"{stat_line}\n"
        f"  /DEPENDENT {dependent}\n"
        f"  /METHOD={method} {ivs}.\n"
        f"EXECUTE.\n"
    )


def syntax_reliability(
    dataset_path: str,
    items: list[str],
    model: str = "ALPHA",
    statistics: list[str] | None = None,
) -> str:
    """Generate RELIABILITY (Cronbach's alpha) syntax.

    Parameters
    ----------
    model : str  ALPHA, SPLIT, GUTTMAN, PARALLEL, STRICTPARALLEL.
    statistics : list, optional
        SPSS keywords, e.g. ["SCALE", "DESCRIPTIVE", "CORR"].
        Defaults to ["SCALE", "DESCRIPTIVE"].
    """
    if statistics is None:
        statistics = ["SCALE", "DESCRIPTIVE"]
    stat_line = "\n  ".join(f"/SUMMARY={s}" for s in statistics)
    var_line = " ".join(items)
    return (
        f"GET FILE='{_sanitise(dataset_path)}'.\n"
        f"DATASET NAME SAFDataset WINDOW=FRONT.\n"
        f"RELIABILITY\n"
        f"  /VARIABLES={var_line}\n"
        f"  /SCALE('ALL ITEMS') ALL\n"
        f"  /MODEL={model}\n"
        f"{stat_line}\n"
        f"  /MISSING=LISTWISE.\n"
        f"EXECUTE.\n"
    )


def syntax_for_recipe(
    dataset_path: str,
    recipe_step: dict[str, Any],
) -> str:
    """Dispatch to the correct syntax generator based on recipe step."""
    kind = recipe_step.get("kind", "")
    if kind == "descriptives":
        return syntax_descriptives(dataset_path, recipe_step.get("variables", []))
    if kind == "frequencies":
        return syntax_frequencies(dataset_path, recipe_step.get("variables", []))
    if kind == "crosstabs":
        return syntax_crosstabs(
            dataset_path,
            recipe_step.get("row_var", ""),
            recipe_step.get("col_var", ""),
            recipe_step.get("layer_vars"),
            recipe_step.get("statistics"),
        )
    if kind in ("ttest", "t_test", "compare_groups"):
        return syntax_ttest(
            dataset_path,
            recipe_step.get("value_col", ""),
            recipe_step.get("group_col"),
            recipe_step.get("test_value"),
            recipe_step.get("paired", False),
        )
    if kind == "anova":
        return syntax_oneway(
            dataset_path,
            recipe_step.get("dependent", ""),
            recipe_step.get("factor", ""),
            recipe_step.get("post_hoc"),
        )
    if kind == "correlation":
        return syntax_correlations(dataset_path, recipe_step.get("variables", []))
    if kind == "regression":
        return syntax_regression(
            dataset_path,
            recipe_step.get("dependent", ""),
            recipe_step.get("independents", []),
            recipe_step.get("method", "ENTER"),
        )
    if kind == "reliability":
        return syntax_reliability(dataset_path, recipe_step.get("items", []))
    return f"* Unknown recipe kind: {kind}\n"
