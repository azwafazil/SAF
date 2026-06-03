from __future__ import annotations


def generate_spss_syntax(file: str, analyses: list[dict]) -> str:
    """Generate basic SPSS syntax for common analyses.

    This does not execute SPSS. It gives students a reproducible syntax draft.
    """
    lines = [f"* SAF-generated SPSS syntax for {file}.", ""]
    for analysis in analyses:
        kind = analysis.get("kind")
        if kind == "descriptives":
            vars_ = " ".join(analysis["variables"])
            lines.append(f"DESCRIPTIVES VARIABLES={vars_} /STATISTICS=MEAN STDDEV MIN MAX.")
        elif kind == "frequencies":
            vars_ = " ".join(analysis["variables"])
            lines.append(f"FREQUENCIES VARIABLES={vars_} /ORDER=ANALYSIS.")
        elif kind == "crosstabs":
            lines.append(
                f"CROSSTABS /TABLES={analysis['row']} BY {analysis['column']} "
                "/STATISTICS=CHISQ PHI /CELLS=COUNT ROW COLUMN."
            )
        elif kind == "ttest_independent":
            lines.append(
                f"T-TEST GROUPS={analysis['group']}({analysis['group_a']} {analysis['group_b']}) "
                f"/VARIABLES={analysis['dv']} /MISSING=ANALYSIS."
            )
        elif kind == "anova":
            lines.append(f"ONEWAY {analysis['dv']} BY {analysis['between']} /STATISTICS DESCRIPTIVES HOMOGENEITY.")
        elif kind == "correlation":
            vars_ = " ".join(analysis["variables"])
            lines.append(f"CORRELATIONS /VARIABLES={vars_} /PRINT=TWOTAIL NOSIG /MISSING=PAIRWISE.")
        elif kind == "regression":
            predictors = " ".join(analysis["predictors"])
            lines.append(f"REGRESSION /DEPENDENT {analysis['dv']} /METHOD=ENTER {predictors}.")
        elif kind == "reliability":
            items = " ".join(analysis["items"])
            scale = analysis.get("scale_name", "Scale")
            lines.append(f"RELIABILITY /VARIABLES={items} /SCALE('{scale}') ALL /MODEL=ALPHA.")
        else:
            lines.append(f"* Unsupported SAF syntax kind: {kind}.")
        lines.append("")
    return "\n".join(lines).strip() + "\n"
