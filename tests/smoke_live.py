"""Smoke test: execute every SAF MCP tool end-to-end with realistic data.

Covers 7 dataset tools + 12 stat_* tools + 2 resources + 1 prompt.
Records ok/error + key fields for the gap report.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

# Add src to path (editable install should handle this, but be explicit)
HERE = Path(__file__).parent
SRC = HERE / "src"
sys.path.insert(0, str(SRC))

from saf_mcp import security, server  # noqa: E402
from saf_mcp.stats import (  # noqa: E402
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


def banner(s):
    print(f"\n{'=' * 70}\n{s}\n{'=' * 70}")


def show(label, result, max_len=400):
    s = json.dumps(result, default=str)
    print(f"  {label}: ", end="")
    if len(s) > max_len:
        s = s[:max_len] + "..."
    print(s)


# Track all bugs / errors seen
ISSUES = []


def safe_call(name, fn, *args, **kwargs):
    """Call a tool, print result, and record any failures for the gap report."""
    try:
        r = fn(*args, **kwargs)
        ok = r.get("ok", True) if isinstance(r, dict) else True
        if ok is False:
            ISSUES.append((name, "ok=False", r.get("error", {}).get("message", "?")))
        return r
    except Exception as exc:  # noqa: BLE001
        ISSUES.append((name, "EXCEPTION", f"{type(exc).__name__}: {exc}"))
        print(f"  [EXCEPTION in {name}] {type(exc).__name__}: {exc}")
        return None


# ---------------------------------------------------------------------------
# Sandbox + fixtures
# ---------------------------------------------------------------------------

TMP = Path(tempfile.mkdtemp(prefix="saf-smoke-"))
os.environ["SAF_DATA_ROOT"] = str(TMP)
print(f"SAF_DATA_ROOT={TMP}")

# 1. Create CSV fixture
csv_path = TMP / "study.csv"
n = 200
rng = np.random.default_rng(42)
df = pd.DataFrame(
    {
        "id": range(1, n + 1),
        "age": rng.integers(18, 70, n).astype(float),
        "income": rng.normal(50_000, 15_000, n).round(2),
        "score": rng.normal(75, 10, n).round(2),
        "group": rng.choice(["A", "B", "C"], n),
        "sex": rng.choice(["M", "F"], n),
        "satisfied": rng.choice([0, 1], n),
        "region": rng.choice(["N", "S", "E", "W"], n),
    }
)
# Inject missingness + outliers
df.loc[rng.choice(n, 12, replace=False), "income"] = np.nan
df.loc[rng.choice(n, 8, replace=False), "score"] = np.nan
df.loc[0, "income"] = 1_000_000  # outlier
df.loc[1, "score"] = -50  # outlier
df.to_csv(csv_path, index=False)

# 2. Create SPSS fixture (write a .sav to test SPSS path)
import pyreadstat

sav_path = TMP / "study.sav"
pyreadstat.write_sav(df, str(sav_path))

# 3. Create TSV fixture
tsv_path = TMP / "study.tsv"
df.to_csv(tsv_path, sep="\t", index=False)

print(f"\nFixtures: {csv_path.name} ({len(df)} rows), {sav_path.name}, {tsv_path.name}")

# ---------------------------------------------------------------------------
# Tool 1: list_data_files
# ---------------------------------------------------------------------------
banner("1. list_data_files")
r = server.list_data_files()
show("ok", r["ok"])
show("files", [f["path"] for f in r.get("files", [])][:5])
assert r["ok"] is True
assert len(r["files"]) == 3

# ---------------------------------------------------------------------------
# Tool 2: inspect_spss_metadata
# ---------------------------------------------------------------------------
banner("2. inspect_spss_metadata (study.sav)")
r = server.inspect_spss_metadata("study.sav")
show("ok", r["ok"])
meta = r.get("metadata", {})
print(f"  row_count={meta.get('row_count')}  col_count={meta.get('column_count')}")
print(f"  columns={meta.get('columns')[:5]}...")
assert r["ok"] is True

# ---------------------------------------------------------------------------
# Tool 3: preview_spss_data
# ---------------------------------------------------------------------------
banner("3. preview_spss_data (rows=5)")
r = server.preview_spss_data("study.sav", rows=5)
show("ok", r["ok"])
pv = r.get("preview", {})
print(f"  rows_returned={pv.get('row_count')}  cols={len(pv.get('columns', []))}")
assert r["ok"] is True
assert pv.get("row_count") == 5

banner("3b. preview_spss_data (rows=0 should error)")
r = server.preview_spss_data("study.sav", rows=0)
print(f"  ok={r['ok']}  err={r.get('error', {}).get('message')}")

banner("3c. preview_spss_data (rows=1000 should error)")
r = server.preview_spss_data("study.sav", rows=1000)
print(f"  ok={r['ok']}  err={r.get('error', {}).get('message')}")

# ---------------------------------------------------------------------------
# Tool 4: profile_spss_data
# ---------------------------------------------------------------------------
banner("4. profile_spss_data")
r = server.profile_spss_data("study.sav", rows=500)
show("ok", r["ok"])
prof = r.get("profile", {})
print(f"  row_count={prof.get('row_count')}  col_count={prof.get('column_count')}")
print(f"  income mean={prof['columns']['income'].get('mean'):.2f}")
print(f"  group unique={prof['columns']['group'].get('unique_count')}")
assert r["ok"] is True

# ---------------------------------------------------------------------------
# Tool 5: convert_spss_to_csv
# ---------------------------------------------------------------------------
banner("5. convert_spss_to_csv")
out_csv = TMP / "out.csv"
r = server.convert_spss_to_csv("study.sav", "out.csv")
show("ok", r["ok"])
print(f"  rows_written={r.get('rows_written')}")
assert r["ok"] is True
assert out_csv.exists()

# ---------------------------------------------------------------------------
# Tool 6: convert_csv_to_sav
# ---------------------------------------------------------------------------
banner("6. convert_csv_to_sav")
out_sav = TMP / "out.sav"
r = server.convert_csv_to_sav("study.csv", "out.sav")
show("ok", r["ok"])
print(f"  rows_written={r.get('rows_written')}")
assert r["ok"] is True
assert out_sav.exists()

# ---------------------------------------------------------------------------
# Tool 7: generate_basic_spss_syntax
# ---------------------------------------------------------------------------
banner("7. generate_basic_spss_syntax")
r = server.generate_basic_spss_syntax("study.sav", variables=["age", "income"])
show("ok", r["ok"])
print(f"  syntax[:120]={r.get('syntax', '')[:120]!r}")
assert r["ok"] is True
assert "GET FILE" in r["syntax"]
assert "age income" in r["syntax"]

banner("7b. generate_basic_spss_syntax (unknown var)")
r = server.generate_basic_spss_syntax("study.sav", variables=["age", "nonexistent"])
print(f"  ok={r['ok']}  err={r.get('error', {}).get('message')}")
assert r["ok"] is False

# ---------------------------------------------------------------------------
# Tool 8: saf_stat_descriptives
# ---------------------------------------------------------------------------
banner("8. saf_stat_descriptives")
r = server.saf_stat_descriptives("study.csv", ["age", "income", "score", "group"])
show("ok", r["ok"])
for row in r.get("results", []):
    if row.get("dtype", "").startswith(("int", "float")):
        print(
            f"  {row['column']}: n={row['n']} mean={row['mean']:.2f} "
            f"sd={row['sd']:.2f} skew={row['skew']:.3f}"
        )
    else:
        print(f"  {row['column']}: dtype={row['dtype']} top={row.get('top')}")
assert r["ok"] is True
assert len(r["results"]) == 4

# ---------------------------------------------------------------------------
# Tool 9: saf_stat_assumptions
# ---------------------------------------------------------------------------
banner("9. saf_stat_assumptions")
r = server.saf_stat_assumptions("study.csv", ["age", "income"], group_col="group")
show("ok", r["ok"])
for row in r.get("results", []):
    print(
        f"  {row['column']}: {row['normality_test']} "
        f"p={row['normality_p']:.4f} pass={row['normality_pass']}"
    )
print(f"  Levene: {r.get('levene')}")
assert r["ok"] is True

# ---------------------------------------------------------------------------
# Tool 10: saf_stat_compare_groups
# ---------------------------------------------------------------------------
banner("10. saf_stat_compare_groups (M vs F on income, Welch)")
# Make a 2-group CSV
two = pd.DataFrame(
    {
        "g": (["A"] * 50) + (["B"] * 50),
        "v": np.concatenate([rng.normal(50, 10, 50), rng.normal(55, 10, 50)]),
    }
)
two_path = TMP / "two.csv"
two.to_csv(two_path, index=False)
r = server.saf_stat_compare_groups("two.csv", "v", "g", parametric=True)
show("ok", r["ok"])
print(
    f"  method={r['result']['method']} t={r['result'].get('t_stat'):.3f} p={r['result'].get('p_value'):.4f}"
)
print(f"  cohens_d={r['result'].get('cohens_d')}")

banner("10b. compare_groups parametric=False (Mann-Whitney)")
r = server.saf_stat_compare_groups("two.csv", "v", "g", parametric=False)
print(f"  method={r['result']['method']} U={r['result'].get('u_stat'):.2f}")

banner("10c. compare_groups with 3 groups (should error)")
r = server.saf_stat_compare_groups("study.csv", "income", "group")
print(f"  ok={r['ok']}  err={r.get('error', {}).get('message')}")

# ---------------------------------------------------------------------------
# Tool 11: saf_stat_anova
# ---------------------------------------------------------------------------
banner("11. saf_stat_anova")
r = server.saf_stat_anova("study.csv", "income", "group", post_hoc=True)
show("ok", r["ok"])
res = r.get("result", {})
print(f"  method={res.get('method')} F={res.get('F'):.3f} p={res.get('p_value'):.6f}")
print(f"  eta2={res.get('eta_squared')}")
if "post_hoc" in res:
    print(
        f"  post_hoc.method={res['post_hoc']['method']} comparisons={len(res['post_hoc']['comparisons'])}"
    )
elif "post_hoc_error" in res:
    print(f"  post_hoc_error={res['post_hoc_error']}")

banner("11b. anova welch=True")
r = server.saf_stat_anova("study.csv", "income", "group", welch=True, post_hoc=False)
print(f"  method={r['result'].get('method')}")

# ---------------------------------------------------------------------------
# Tool 12: saf_stat_correlate
# ---------------------------------------------------------------------------
banner("12. saf_stat_correlate (pearson age vs income)")
r = server.saf_stat_correlate("study.csv", "age", "income", method="pearson")
show("ok", r["ok"])
print(
    f"  r={r['result']['r']} p={r['result']['p_value']:.4f} ci95={r['result']['ci95']}"
)

banner("12b. correlate spearman + kendall")
for m in ("spearman", "kendall"):
    r = server.saf_stat_correlate("study.csv", "age", "income", method=m)
    print(f"  {m}: r={r['result']['r']} p={r['result']['p_value']:.4f}")

banner("12c. correlate unknown method")
r = server.saf_stat_correlate("study.csv", "age", "income", method="banana")
print(f"  ok={r['ok']}  err={r.get('error', {}).get('message')}")

# ---------------------------------------------------------------------------
# Tool 13: saf_stat_regress
# ---------------------------------------------------------------------------
banner("13. saf_stat_regress (OLS income ~ age + score)")
r = server.saf_stat_regress("study.csv", "income", ["age", "score"], family="ols")
show("ok", r["ok"])
res = r.get("result", {})
print(f"  R2={res.get('r_squared'):.4f}  adj_R2={res.get('adj_r_squared'):.4f}")
print(f"  F={res.get('f_stat'):.3f} p={res.get('f_pvalue'):.4f}")
for k, v in res.get("coefficients", {}).items():
    print(f"  coef[{k}]={v['coef']:.3f} p={v['p_value']:.4f}")
print(f"  VIF={res.get('vif')}")

banner("13b. regress logistic (satisfied ~ age + sex)")
r = server.saf_stat_regress("study.csv", "satisfied", ["age", "sex"], family="logistic")
print(f"  ok={r['ok']}  R2={r['result'].get('r_squared')}")
print(f"  coefs: {list(r['result'].get('coefficients', {}).keys())}")

banner("13c. regress robust HC3")
r = server.saf_stat_regress("study.csv", "income", ["age", "score"], robust=True)
print(f"  ok={r['ok']}  family={r['result'].get('family')}")

# ---------------------------------------------------------------------------
# Tool 14: saf_stat_chi_square
# ---------------------------------------------------------------------------
banner("14. saf_stat_chi_square (sex x group)")
r = server.saf_stat_chi_square("study.csv", "sex", "group", test="independence")
show("ok", r["ok"])
res = r.get("result", {})
print(f"  chi2={res.get('chi2'):.3f} dof={res.get('dof')} p={res.get('p_value'):.4f}")
print(f"  cramers_v={res.get('cramers_v')}  fisher={res.get('fisher_exact')}")

banner("14b. chi-square GOF (sex x group, expected sums to N)")
# Read the actual crosstab to compute matching expected
ct = pd.crosstab(
    pd.read_csv(TMP / "study.csv")["sex"], pd.read_csv(TMP / "study.csv")["group"]
).values
n = int(ct.sum())
expected = [[int(ct[i, j]) for j in range(ct.shape[1])] for i in range(ct.shape[0])]
print(f"  observed={ct.tolist()}  expected={expected}  N={n}")
r = safe_call(
    "chi_square.gof",
    server.saf_stat_chi_square,
    "study.csv",
    "sex",
    "group",
    test="gof",
    expected=expected,
)
print(f"  result={r}")

# ---------------------------------------------------------------------------
# Tool 15: saf_stat_nonparametric
# ---------------------------------------------------------------------------
banner("15. saf_stat_nonparametric (Wilcoxon, mu=50000)")
r = server.saf_stat_nonparametric("study.csv", "income", test="wilcoxon", mu=50000.0)
show("ok", r["ok"])
print(
    f"  method={r['result'].get('method')} W={r['result'].get('W'):.2f} p={r['result'].get('p_value'):.4f}"
)

banner("15b. sign test")
r = server.saf_stat_nonparametric("study.csv", "income", test="sign", mu=50000.0)
print(f"  method={r['result'].get('method')} n={r['result'].get('n')}")

banner("15c. friedman (long format with subject_col)")
# Need 3+ groups, repeated measures — long-format with subject col
fdf = pd.DataFrame(
    {
        "subject": [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4],
        "cond": ["A", "B", "C"] * 4,
        "score": [10, 12, 15, 11, 13, 14, 9, 11, 16, 8, 10, 12],
    }
)
fpath = TMP / "friedman.csv"
fdf.to_csv(fpath, index=False)
r = server.saf_stat_nonparametric(
    "friedman.csv", "score", group_col="cond", subject_col="subject", test="friedman"
)
print(
    f"  method={r['result'].get('method')} Q={r['result'].get('Q'):.3f} p={r['result'].get('p_value'):.4f}"
)

# ---------------------------------------------------------------------------
# Tool 16: saf_stat_effect_size
# ---------------------------------------------------------------------------
banner("16. saf_stat_effect_size (Cohen's d from x,y)")
r = server.saf_stat_effect_size(kind="cohens_d", x=[1, 2, 3, 4, 5], y=[3, 4, 5, 6, 7])
show("ok", r["ok"])
print(f"  value={r['result']['value']}  ci95={r['result'].get('ci95')}")

banner("16b. effect_size eta_squared")
r = safe_call(
    "effect_size.eta_squared",
    server.saf_stat_effect_size,
    kind="eta_squared",
    file_path="study.csv",
    var_a="income",
    var_b="group",
)
print(f"  result={r}")

banner("16c. effect_size cramers_v")
r = server.saf_stat_effect_size(
    kind="cramers_v", file_path="study.csv", var_a="sex", var_b="group"
)
print(f"  ok={r['ok']}  value={r['result'].get('value')}")

banner("16d. effect_size odds_ratio (2x2 only)")
r = server.saf_stat_effect_size(
    kind="odds_ratio", file_path="study.csv", var_a="sex", var_b="satisfied"
)
print(f"  ok={r['ok']}  value={r['result'].get('value')}")

banner("16e. effect_size odds_ratio with 4x4 table (should error)")
r = server.saf_stat_effect_size(
    kind="odds_ratio", file_path="study.csv", var_a="group", var_b="region"
)
print(f"  ok={r['ok']}  err={r.get('error', {}).get('message')}")

banner("16f. effect_size unknown kind")
r = server.saf_stat_effect_size(kind="zzz")
print(f"  ok={r['ok']}  err={r.get('error', {}).get('message')}")

# ---------------------------------------------------------------------------
# Tool 17: saf_stat_power
# ---------------------------------------------------------------------------
banner("17. saf_stat_power (t-test, solve power: n=64, d=0.5)")
r = server.saf_stat_power(test="t", effect_size=0.5, alpha=0.05, nobs=64)
show("ok", r["ok"])
print(f"  solved_power={r['result'].get('solved_power'):.3f}")

banner("17b. solve_nobs (t-test, power=0.8, d=0.5)")
r = server.saf_stat_power(test="t", effect_size=0.5, alpha=0.05, power=0.8)
print(f"  solved_nobs={r['result'].get('solved_nobs')}")

banner("17c. ANOVA power")
r = safe_call(
    "power.f",
    server.saf_stat_power,
    test="f",
    effect_size=0.25,
    alpha=0.05,
    nobs=60,
)
print(f"  result={r}")

banner("17d. chi2 power")
r = safe_call(
    "power.chi2",
    server.saf_stat_power,
    test="chi2",
    effect_size=0.3,
    alpha=0.05,
    nobs=100,
)
print(f"  result={r}")

banner("17e. z-test power (mentioned in docstring, unhandled?)")
r = safe_call(
    "power.z",
    server.saf_stat_power,
    test="z",
    effect_size=0.3,
    alpha=0.05,
    nobs=100,
)
print(f"  result={r}")

banner("17e. power with both power and nobs (should error)")
r = server.saf_stat_power(test="t", effect_size=0.5, power=0.8, nobs=64)
print(f"  ok={r['ok']}  err={r.get('error', {}).get('message')}")

# ---------------------------------------------------------------------------
# Tool 18: saf_stat_outliers
# ---------------------------------------------------------------------------
banner("18. saf_stat_outliers (iqr on income+score)")
r = server.saf_stat_outliers(
    "study.csv", ["income", "score"], method="iqr", threshold=1.5
)
show("ok", r["ok"])
for col, info in r.get("per_column", {}).items():
    print(
        f"  {col}: n_outliers={info['n_outliers']} fences=({info['lower_fence']:.0f}, {info['upper_fence']:.0f})"
    )

banner("18b. outliers z-score")
r = server.saf_stat_outliers("study.csv", ["income"], method="z", threshold=2.0)
print(f"  ok={r['ok']}  n_outliers={r['per_column']['income']['n_outliers']}")

banner("18c. outliers modified_z")
r = server.saf_stat_outliers(
    "study.csv", ["income"], method="modified_z", threshold=3.5
)
print(f"  ok={r['ok']}  n_outliers={r['per_column']['income']['n_outliers']}")

banner("18d. outliers mahalanobis")
r = server.saf_stat_outliers(
    "study.csv", ["age", "income", "score"], method="mahalanobis"
)
info = r["per_column"].get("__mahalanobis__", {})
print(
    f"  ok={r['ok']}  n_outliers={info.get('n_outliers')} cutoff={info.get('cutoff_d')}"
)

banner("18e. outliers unknown method")
r = server.saf_stat_outliers("study.csv", ["income"], method="qqplot")
print(f"  ok={r['ok']}  err={r.get('error', {}).get('message')}")

# ---------------------------------------------------------------------------
# Tool 19: saf_stat_missing
# ---------------------------------------------------------------------------
banner("19. saf_stat_missing")
r = server.saf_stat_missing("study.csv")
show("ok", r["ok"])
print(
    f"  n_rows={r['n_rows']}  complete_rows={r['complete_rows']} ({r['complete_rows_pct']}%)"
)
for c in r.get("per_column", [])[:8]:
    print(f"  {c['column']}: missing={c['n_missing']} ({c['pct_missing']}%)")
print(f"  mcar_associations={r.get('mcar_associations')}")

# ---------------------------------------------------------------------------
# Resources + prompt
# ---------------------------------------------------------------------------
banner("20. saf://guide resource")
print(f"  text[:200]={server.guide()[:200]!r}")

banner("21. saf://repo-ingestion resource")
print(f"  text[:200]={server.repo_ingestion()[:200]!r}")

banner("22. analyze_dataset_prompt")
print(f"  prompt[:200]={server.analyze_dataset_prompt('study.sav')[:200]!r}")

# ---------------------------------------------------------------------------
# SECURITY: path traversal
# ---------------------------------------------------------------------------
banner("S1. SECURITY: path traversal blocked")
r = server.inspect_spss_metadata("../../../etc/passwd")
print(f"  ok={r['ok']}  err={r.get('error', {}).get('message')}")
assert r["ok"] is False

r = server.inspect_spss_metadata("/etc/passwd")
print(f"  /etc/passwd: ok={r['ok']}  err={r.get('error', {}).get('message')}")
assert r["ok"] is False

# ---------------------------------------------------------------------------
# MCP introspection: list tools via FastMCP
# ---------------------------------------------------------------------------
banner("MCP. tools/list (the actual MCP surface)")
import asyncio


async def list_tools():
    tools = await server.mcp.list_tools()
    return tools


tools = asyncio.run(list_tools())
print(f"  total tools registered: {len(tools)}")
for t in tools:
    print(f"    - {t.name}")

# ---------------------------------------------------------------------------
# GAP REPORT
# ---------------------------------------------------------------------------
banner("GAP REPORT")
if not ISSUES:
    print("  (no issues captured)")
else:
    for name, kind, msg in ISSUES:
        print(f"  [{kind}] {name}: {msg}")
print(f"\n  Total issues: {len(ISSUES)}")

print("\n\n>>> SMOKE TEST COMPLETE")
