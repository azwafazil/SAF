# Changelog

All notable changes to SAF (Statistical Analysis Forge) are documented here.
The format is loosely based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased] — 2026-06-03 — Improve-Stats-Tools

### Fixed

- **`saf_stat_chi_square` GOF test** previously raised
  `chisquare() got multiple values for argument 'f_obs'`. The call was
  passing `observed` positionally and as `f_obs=` simultaneously. Now
  correctly passes `observed` positionally and `f_exp=` as keyword.
  Added shape-mismatch check (returns a clear error instead of `nan`).
- **`saf_stat_nonparametric` Friedman** pivoted on `df.index` which
  collapses long-format data to an empty frame (`Q=nan`, `p=nan`).
  Now accepts an explicit `subject_col` parameter for long-format input;
  wide-format input (rows = subjects, columns = conditions) still works.
- **`saf_stat_effect_size` eta_squared** had a broken arg check
  (`var_b not in (x or [])` always true). Returns clean error if `var_b`
  is missing, and now reports `n_groups`, `value_col`, `group_col`.
- **`saf_stat_power` F-test** was using `FTestPower.solve_power` which
  requires `df_denom` (not `df_den`) and often failed to converge for
  one-way ANOVA. Switched to `FTestAnovaPower` with `k_groups = df_num + 1`.
  Matches G*Power output (e.g. f=0.25, k=3, power=0.8 → N=158).
- **`saf_stat_power` z-test** was advertised in the docstring but raised
  "unknown test z". Now uses `NormalIndPower` for two-proportion z-tests
  (Cohen's h).
- **`saf_stat_outliers` mahalanobis with 1 column** silently fell through
  to the per-column loop and hit "unknown method" error. Now returns a
  clear error: `"mahalanobis requires >= 2 columns, got 1"`.
- **`saf_stat_compare_groups` Cohen's d** was only computed for the
  Student t-test (`equal_var=True`). Welch t-test now also reports
  Cohen's d (pooled SD) plus Hedges' g (small-sample bias-corrected).

### Added

- **`saf_stat_correlate` bootstrap CI** for Spearman / Kendall. Set
  `bootstrap=1000` (and optional `seed=42`) to get a 95% percentile-
  bootstrap CI. Without `bootstrap`, the response still includes
  `ci95=[null, null]` for non-parametric methods (was already the case
  but now documented). Custom `alpha` is also exposed.
- **`saf_stat_effect_size` rank-biserial correlation** (`kind="rank_biserial"`).
  Computed via Mann-Whitney U: `r = 1 - 2U / (n1 * n2)`.
- **`saf_stat_power` new parameters**: `alternative` (two-sided / larger
  / smaller, t and z only), `df_num` (optional for F-test, defaults to
  k=2), `ratio` (sample-size ratio for two-sample t / z tests).
- **CHANGELOG.md** and **examples/jsonrpc.md** — JSON-RPC examples
  for every category of tool call.
- **24 new tests** in `tests/test_stats_v2.py` covering the fixes,
  new features, and edge cases.

### Changed

- **`saf_stat_nonparametric` signature** gained a `subject_col` parameter
  (default `None`). Wide-format Friedman users see no change.
- **`saf_stat_correlate` signature** gained `alpha`, `bootstrap`, `seed`
  parameters (all default to existing behavior).
- **`saf_stat_power` signature** gained `alternative`, `df_num`, `ratio`
  parameters (all optional, backwards compatible).
- **`saf_stat_effect_size` docstring** now enumerates every supported
  `kind` and the args each requires.

### Stats surface (53 tests, 100% green)

```
test_stats.py:        29 baseline tests
test_stats_v2.py:     24 new tests for fixes + features
test_imports.py:      2 (path traversal, module imports)
```

## [0.1.0] — 2026-06-02 — Initial donation

### Added

- 7 dataset tools: `list_data_files`, `inspect_spss_metadata`,
  `preview_spss_data`, `profile_spss_data`, `convert_spss_to_csv`,
  `convert_csv_to_sav`, `generate_basic_spss_syntax`.
- 12 statistical tools: `saf_stat_descriptives`, `saf_stat_assumptions`,
  `saf_stat_compare_groups`, `saf_stat_anova`, `saf_stat_correlate`,
  `saf_stat_regress`, `saf_stat_chi_square`, `saf_stat_nonparametric`,
  `saf_stat_effect_size`, `saf_stat_power`, `saf_stat_outliers`,
  `saf_stat_missing`.
- Resources: `saf://guide`, `saf://repo-ingestion`.
- Prompt: `analyze_dataset_prompt`.
- SECURITY.md, ROADMAP.md, INGESTION_NOTES.md.
- `pyproject.toml`, `examples/claude_desktop_config.example.json`.

[Unreleased]: https://github.com/azwafazil/SAF/compare/08e987d...HEAD
[0.1.0]: https://github.com/azwafazil/SAF/releases/tag/0.1.0
