"""SAF APA 7 Report Generator — produces APA-style interpretation text.

Functions take a result dict from a stat_* tool and produce:
  - apa_interpretation(kind, result) → APA sentence/paragraph
  - generate_markdown_report(path, recipe_result) → full Markdown report
  - export_csv_tables(recipe_result) → CSV table strings
"""

from __future__ import annotations

import csv
import io
from typing import Any


def _sig(p: float | None) -> str:
    if p is None:
        return "ns"
    if p < 0.001:
        return "p < .001"
    if p < 0.01:
        return f"p = {p:.3f}"
    if p < 0.05:
        return f"p = {p:.3f}"
    return f"p = {p:.3f}"


def _rnd(v: Any, decimals: int = 2) -> str:
    try:
        return f"{float(v):.{decimals}f}"
    except (ValueError, TypeError):
        return str(v)


def apa_interpretation(kind: str, result: dict[str, Any]) -> str:
    """Generate an APA 7-style interpretation sentence from a stat result."""
    r = result.get("result") or result
    if not r or not isinstance(r, dict):
        return ""

    try:
        if kind == "descriptives":
            cols = result.get("results", [])
            parts = []
            for c in cols[:5]:
                n = c.get("n", "?")
                m = _rnd(c.get("mean", "?"))
                s = _rnd(c.get("sd", "?"))
                parts.append(f"{c['column']} (M = {m}, SD = {s}, n = {n})")
            return "Descriptive statistics: " + "; ".join(parts) + "."

        if kind == "frequencies":
            tables = result.get("tables", [])
            parts = []
            for t in tables[:3]:
                vals = t.get("frequencies", [])
                top = vals[0] if vals else {}
                parts.append(f"{t['variable']}: top value = {top.get('value')} ({top.get('percent', 0)}%)")
            return "Frequency distributions: " + "; ".join(parts) + "."

        if kind == "reliability":
            a = _rnd(r.get("cronbach_alpha", "?"))
            n_items = r.get("n_items", "?")
            interp = r.get("interpretation", "")
            return (
                f"Cronbach's alpha for {n_items} items was α = {a}, "
                f"indicating {interp.lower()} internal consistency."
            )

        if kind in ("compare_groups", "t_test"):
            method = r.get("method", "t-test")
            t = _rnd(r.get("t_stat", "?"))
            p = _sig(r.get("p_value"))
            d = _rnd(r.get("cohens_d", "?"))
            n1 = r.get("n_group1", "?")
            n2 = r.get("n_group2", "?")
            return (
                f"An independent-samples {method} was conducted. "
                f"There was{' a' if r.get('p_value', 1) < 0.05 else ' no'} "
                f"significant difference, t({_rnd(r.get('df', '?'))}) = {t}, {p}, "
                f"Cohen's d = {d} (n1 = {n1}, n2 = {n2})."
            )

        if kind == "anova":
            method = r.get("method", "ANOVA")
            fv = _rnd(r.get("F", "?"))
            p = _sig(r.get("p_value"))
            e2 = _rnd(r.get("eta_squared", "?"))
            return (
                f"A one-way {method} was conducted. "
                f"There was{' a' if r.get('p_value', 1) < 0.05 else ' no'} "
                f"significant effect, F({_rnd(r.get('df_between', '?'))}, "
                f"{_rnd(r.get('df_within', '?'))}) = {fv}, {p}, η² = {e2}."
            )

        if kind == "correlation":
            method = r.get("method", "Pearson")
            rv = _rnd(r.get("r", "?"))
            p = _sig(r.get("p_value"))
            n = r.get("n", "?")
            return (
                f"A {method} correlation was conducted between {r.get('x', '?')} "
                f"and {r.get('y', '?')}. There was{' a' if r.get('p_value', 1) < 0.05 else ' no'} "
                f"significant relationship, r({n - 2}) = {rv}, {p}."
            )

        if kind == "regression":
            r2 = _rnd(r.get("r_squared", "?"))
            fv = _rnd(r.get("f_stat", "?"))
            p = _sig(r.get("f_pvalue"))
            n = r.get("n", "?")
            k = len(r.get("independents", []))
            return (
                f"A linear regression was conducted with {r.get('dependent', '?')} "
                f"as dependent variable. The model was{' significant' if r.get('f_pvalue', 1) < 0.05 else ' not significant'}, "
                f"F({k}, {n - k - 1}) = {fv}, {p}, R² = {r2}."
            )

        if kind == "chi_square":
            c2 = _rnd(r.get("chi2", "?"))
            p = _sig(r.get("p_value"))
            dof = r.get("dof", "?")
            cv = _rnd(r.get("cramers_v", "?"))
            return (
                f"A chi-square test of independence was conducted. "
                f"There was{' a' if r.get('p_value', 1) < 0.05 else ' no'} "
                f"significant association, χ²({dof}, N = {r.get('n', '?')}) = {c2}, {p}, "
                f"Cramér's V = {cv}."
            )

        if kind == "assumptions":
            rows = result.get("results", [])
            parts = []
            for row in rows[:3]:
                sw = _rnd(row.get("normality_p", 1), 3)
                status = "passed" if row.get("normality_pass") else "failed"
                parts.append(f"{row['column']}: Shapiro-Wilk {status} (p = {sw})")
            lv = result.get("levene")
            if lv:
                lp = _rnd(lv.get("levene_p", 1), 3)
                lstat = "homoscedastic" if lv.get("homoscedastic") else "heteroscedastic"
                parts.append(f"Levene's test: {lstat} (p = {lp})")
            return "Assumption checks: " + "; ".join(parts) + "."

        if kind == "missing":
            n_rows = result.get("n_rows", "?")
            complete = result.get("complete_rows", "?")
            pct = _rnd(result.get("complete_rows_pct", "?"))
            return (
                f"Missing data analysis: {complete} of {n_rows} rows ({pct}%) "
                f"were complete. {result.get('n_columns', '?')} columns examined."
            )

        if kind == "outliers":
            cols = result.get("per_column", {})
            parts = []
            for name, info in cols.items():
                if isinstance(info, dict):
                    parts.append(f"{name}: {info.get('n_outliers', 0)} outliers detected ({info.get('method', '?')})")
            return "Outlier analysis: " + "; ".join(parts) + "." if parts else "No outliers detected."

        return ""
    except Exception:
        return ""


def _markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    """Render a simple Markdown table."""
    sep = "| " + " | ".join("---" for _ in headers) + " |"
    header_line = "| " + " | ".join(headers) + " |"
    body = "\n".join("| " + " | ".join(row) + " |" for row in rows)
    return f"{header_line}\n{sep}\n{body}"


def generate_markdown_report(
    path: str,
    recipe_result: dict[str, Any],
    title: str = "SAF Analysis Report",
) -> str:
    """Generate a complete Markdown report from a recipe result."""
    recipe = recipe_result.get("recipe", recipe_result)
    lines: list[str] = []

    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"**Dataset**: `{path}`  ")
    lines.append(
        f"**Date**: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}  "
    )
    lines.append(f"**Steps**: {recipe.get('n_steps', 0)} total, "
                 f"{recipe.get('n_ok', 0)} ok, {recipe.get('n_failed', 0)} failed  ")
    lines.append(f"**Duration**: {recipe.get('total_elapsed', 0)}s  ")
    lines.append("")
    lines.append("---")
    lines.append("")

    for result in recipe.get("results", []):
        step = result.get("step", "?")
        kind = result.get("kind", "?")
        label = result.get("label", kind)
        ok = result.get("ok", False)

        icon = "✅" if ok else "❌"
        lines.append(f"## Step {step}: {label} {icon}")
        lines.append("")

        if not ok:
            lines.append(f"**Error**: {result.get('error', 'Unknown error')}")
            lines.append("")
            continue

        apa = result.get("apa", "")
        if apa:
            lines.append(f"> {apa}")
            lines.append("")

        # Detailed result rendering
        data = result.get("result") or result.get("results") or result.get("per_column")

        if isinstance(data, dict):
            h = list(data.keys())[:10]
            r = [[str(data.get(k, ""))[:80] for k in h]]
            lines.append(_markdown_table(h, r))
            lines.append("")

        elif isinstance(data, list) and data:
            if isinstance(data[0], dict):
                h = list(data[0].keys())[:8]
                r = [[str(d.get(k, ""))[:60] for k in h] for d in data[:20]]
                lines.append(_markdown_table(h, r))
                lines.append("")

        # SPSS syntax
        spss = result.get("spss_syntax", "")
        if spss:
            lines.append("**SPSS Syntax**:")
            lines.append("```spss")
            lines.append(spss.strip())
            lines.append("```")
            lines.append("")

        lines.append("---")
        lines.append("")

    # Warnings section
    warnings = recipe.get("warnings", [])
    if warnings:
        lines.append("## ⚠️ Warnings")
        lines.append("")
        for w in warnings:
            lines.append(f"- {w}")
        lines.append("")

    lines.append("*Report generated by SAF (Statistical Analysis Forge)*")
    return "\n".join(lines)


def export_csv_tables(recipe_result: dict[str, Any]) -> dict[str, str]:
    """Export each step's result as a CSV string.

    Returns dict mapping step labels → CSV string.
    """
    recipe = recipe_result.get("recipe", recipe_result)
    exports: dict[str, str] = {}

    for result in recipe.get("results", []):
        if not result.get("ok"):
            continue
        label = result.get("label", f"step_{result.get('step', 0)}")
        kind = result.get("kind", "?")
        data = result.get("result") or result.get("results") or result.get("per_column")

        buf = io.StringIO()
        writer = csv.writer(buf)

        if isinstance(data, dict):
            writer.writerow(list(data.keys()))
            writer.writerow([str(v)[:100] for v in data.values()])

        elif isinstance(data, list) and data:
            if isinstance(data[0], dict):
                writer.writerow(list(data[0].keys())[:15])
                for row in data[:200]:
                    writer.writerow([str(row.get(k, ""))[:100] for k in list(data[0].keys())[:15]])

        exports[label] = buf.getvalue()

    return exports
