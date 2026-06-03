# SAF -- Statistical Analysis Forge

SAF is a privacy-first MCP server for working with SPSS-compatible datasets such as .sav, .zsav, and .por files. It helps AI clients inspect metadata, preview rows, profile variables, convert files, and generate basic SPSS syntax without requiring IBM SPSS.

SAF stands for Statistical Analysis Forge. The project is intentionally broader than one vendor workflow: it is a dataset assistant for SPSS-compatible files, built on `pyreadstat`, which wraps ReadStat.

## What SAF Is

- A Python Model Context Protocol server for dataset inspection and conversion.
- A local-first assistant for `.sav`, `.zsav`, `.por`, `.csv`, and `.tsv` files.
- A privacy-first tool intended for research, survey, and teaching workflows where datasets may contain sensitive respondent data.
- A way for AI clients to inspect metadata, preview rows, profile variables, and generate basic SPSS syntax.

## What SAF Is Not

- SAF is not IBM SPSS.
- SAF does not replace IBM SPSS or claim full statistical equivalence with IBM SPSS.
- SAF does not execute arbitrary SPSS syntax.
- SAF does not execute arbitrary shell commands.
- SAF does not upload, transmit, or externally store user datasets.

## Supported Formats

SAF currently supports these formats:

- `.sav`
- `.zsav`
- `.por`
- `.csv`
- `.tsv`

SPSS-compatible formats are handled through `pyreadstat`.

## Installation

Clone the repository, create an environment, and install the package in editable mode:

```bash
git clone https://github.com/azwafazil/SAF.git
cd SAF
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Set a local data root before running the server:

```bash
export SAF_DATA_ROOT=/absolute/path/to/your/saf-data
```

Keep real datasets outside the repository. The included `.gitignore` blocks common data formats, but access control and careful storage are still your responsibility.

## Running The MCP Server

Run with Python:

```bash
python -m saf_mcp.server
```

Or run the installed CLI:

```bash
saf-mcp
```

The default MCP transport is `stdio`. To request streamable HTTP where supported by your installed MCP package:

```bash
MCP_TRANSPORT=streamable-http saf-mcp
```

## Claude Desktop Config Example

```json
{
  "mcpServers": {
    "saf": {
      "command": "saf-mcp",
      "env": {
        "SAF_DATA_ROOT": "/absolute/path/to/your/saf-data"
      }
    }
  }
}
```

## MCP Capabilities

The server exposes **19 tools** in three groups.

### Dataset tools (7)

| Tool | Purpose |
|------|---------|
| `list_data_files` | Enumerate supported files under `SAF_DATA_ROOT`. |
| `inspect_spss_metadata` | Read column names, labels, value labels, formats. |
| `preview_spss_data` | Return the first *N* rows (1-500). |
| `profile_spss_data` | Per-column dtype, missing count, top values, summary stats. |
| `convert_spss_to_csv` | Write a `.sav` / `.zsav` / `.por` to CSV inside the sandbox. |
| `convert_csv_to_sav` | Write a CSV / TSV to `.sav` inside the sandbox. |
| `generate_basic_spss_syntax` | Produce SPSS syntax (not execute it) for inspection. |

### Statistical analysis tools (12, donated)

All `saf_stat_*` tools accept either SPSS-compatible files (`.sav`, `.zsav`,
`.por`) or tabular files (`.csv`, `.tsv`) and return plain Python dicts —
no F1-F13 governance, no VAULT999 sealing.

| Tool | What it computes |
|------|------------------|
| `saf_stat_descriptives` | n, mean, sd, median, min/max, IQR, MAD, skew, kurtosis, 95% CI of mean. |
| `saf_stat_assumptions` | Shapiro-Wilk normality (D'Agostino fallback for n>5000) + Levene homoscedasticity. |
| `saf_stat_compare_groups` | Two-group t-test (indep / paired / Welch) or Mann-Whitney, with Cohen's d + Hedges' g. |
| `saf_stat_anova` | One-way ANOVA (classic / Welch / Kruskal-Wallis) with optional Tukey HSD + eta-squared. |
| `saf_stat_correlate` | Pearson (Fisher-z CI), Spearman, Kendall. Spearman/Kendall support bootstrap CI. |
| `saf_stat_regress` | OLS / logistic / robust (HC3) regression with CIs, AIC/BIC, VIF (OLS). |
| `saf_stat_chi_square` | Independence test + Cramér's V + Fisher's exact (2x2); GOF test with user-supplied expected. |
| `saf_stat_nonparametric` | Wilcoxon signed-rank, sign test, Friedman (long or wide format), Mann-Whitney (auto), Kruskal-Wallis (auto). |
| `saf_stat_effect_size` | Cohen's d, η², Cramér's V, odds ratio, rank-biserial correlation. |
| `saf_stat_power` | Solve for power / sample size / sensitivity: t-test (d), one-way F (f, k_groups), chi-square (w), z (h). |
| `saf_stat_outliers` | IQR (Tukey), z-score, modified z (Iglewicz–Hoaglin), Mahalanobis (multi-column). |
| `saf_stat_missing` | Per-column counts / pcts, complete-row ratio, MCAR-association sketch. |

### Resources & prompt

| URI / name | Purpose |
|------------|---------|
| `saf://guide` | Quick orientation to the server. |
| `saf://repo-ingestion` | Reminder of the SAF_DATA_ROOT sandbox rule. |
| `analyze_dataset_prompt` | Templated prompt for guiding an LLM through inspect → preview → profile. |

## Example User Prompts

- "List the datasets in my SAF data root."
- "Inspect metadata for `survey.sav`."
- "Preview the first 20 rows of `survey.zsav`."
- "Profile `wave1.por` and summarize missing values."
- "Convert `survey.sav` to `exports/survey.csv`."
- "Generate basic SPSS syntax for `survey.sav` using age, gender, and satisfaction."

## Security Notes

Do not commit real `.sav`, `.zsav`, `.por`, `.csv`, or `.tsv` datasets. University survey files may contain sensitive respondent data.

SAF enforces a filesystem sandbox through `SAF_DATA_ROOT`. All file paths are resolved under that directory, extensions are validated, and traversal attempts are blocked. SAF generates SPSS syntax as text only; it never executes that syntax.

## Roadmap

- Richer metadata summaries for labels, measures, display formats, and missing-value rules.
- Synthetic dataset fixtures for stronger automated tests.
- Labeled data dictionary exports.
- Improved profiling for dates, categoricals, and survey-scale variables.
- Expanded MCP deployment documentation.
