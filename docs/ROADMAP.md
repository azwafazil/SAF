# Roadmap

## Completed

- [x] **SPSS-style Data Dictionary** (v0.3.0) — Variable View: names, labels,
      value labels, measure level (nominal/ordinal/scale), missing counts,
      data types, unique values, and suggested research role (IV, DV,
      grouping, scale_item, identifier). Works for all supported formats.
- [x] Richer variable-label and value-label summaries.
- [x] Missing-value rule summaries from SPSS file metadata.

## Planned (in priority order)

1. **Analysis Recipe Runner** — batch multiple analyses in one call.
2. **APA 7 + SPSS-style Report Generator** — Markdown/CSV/JSON output.
3. **Test Recommendation Engine** — ask research questions → suggest test.
4. **Scale Diagnostics** — reverse coding, item-total correlation, composite scores.
5. **Assumption Checker** — automated normality/Levene warnings on every test.
6. **SPSS Syntax Generator v2** — CROSSTABS, T-TEST, ONEWAY, CORRELATIONS, RELIABILITY.
7. **Factor Analysis** — KMO, Bartlett's, EFA, rotation, loading table.
8. **Regression Expansion** — hierarchical, moderation, mediation.
9. **Audit Log** — record every analysis for reproducibility.
10. **Visualization / Charting** — matplotlib + seaborn, base64 PNG via MCP.

## Stretch

- Export support for labeled CSV dictionaries.
- Clearer profiling for dates and categorical variables.
- Synthetic dataset fixtures for broader tests.
- Streamable HTTP deployment docs.
