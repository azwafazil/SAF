# SAF — Statistical Analysis Forge

**An MCP server for SPSS-compatible datasets with rich statistical analysis, frequencies, crosstabs, reliability analysis, and AI-ready interfaces.**

SAF is a privacy-first [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server for working with SPSS-compatible datasets (`.sav`, `.zsav`, `.por`) and tabular files (`.csv`, `.tsv`, `.xlsx`). Built on [`pyreadstat`](https://github.com/Roche/pyreadstat), it enables AI clients and LLMs to inspect metadata, preview rows, profile variables, run frequencies & crosstabs, assess scale reliability, generate SPSS syntax, and perform comprehensive statistical analyses — all while keeping data local and secure.

## What SAF Is

- ✅ A Python MCP server implementing **24 specialized tools** for dataset inspection and analysis
- ✅ Local-first, privacy-preserving assistant for `.sav`, `.zsav`, `.por`, `.csv`, `.tsv`, and `.xlsx` files
- ✅ Designed for research, survey, and teaching workflows with sensitive respondent data
- ✅ Sandbox-enforced with filesystem isolation via `SAF_DATA_ROOT`

## What SAF Is Not

- ❌ Not a replacement for IBM SPSS
- ❌ Does not execute arbitrary SPSS syntax or shell commands
- ❌ Does not upload, transmit, or externally store datasets

## Supported File Formats

| Format | Support |
|--------|---------|
| `.sav` | ✅ SPSS system files |
| `.zsav` | ✅ Compressed SPSS system files |
| `.por` | ✅ SPSS portable files |
| `.csv` | ✅ Comma-separated values |
| `.tsv` | ✅ Tab-separated values |
| `.xlsx` | ✅ Excel workbooks |

## Quick Start

### Installation

```bash
git clone https://github.com/azwafazil/SAF.git
cd SAF
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Environment Setup

```bash
export SAF_DATA_ROOT=/absolute/path/to/your/saf-data
```

### Running

```bash
saf-mcp                                          # stdio (default)
MCP_TRANSPORT=streamable-http saf-mcp            # HTTP/SSE
```

## MCP Tools Overview

SAF exposes **24 tools** in four groups:

### Dataset Operations (7 tools)

| Tool | Purpose |
|------|---------|
| `list_data_files` | Enumerate supported files under `SAF_DATA_ROOT` |
| `inspect_spss_metadata` | Read column names, labels, value labels, formats, measures |
| `preview_spss_data` | Return first N rows (1–500) |
| `profile_spss_data` | Per-column: dtype, missing count, top values, summary stats |
| `convert_spss_to_csv` | Write `.sav` / `.zsav` / `.por` → CSV |
| `convert_csv_to_sav` | Write `.csv` / `.tsv` / `.xlsx` → `.sav` |
| `generate_basic_spss_syntax` | Generate SPSS syntax (read-only) |

### Survey Analysis (4 new tools)

| Tool | Purpose |
|------|---------|
| `cross_tabulation` | Contingency tables with row/column/total percentages |
| `saf_stat_frequencies` | Frequency tables for categorical/ordinal variables |
| `saf_stat_reliability` | Cronbach's alpha for scale reliability with item diagnostics |
| `saf_stat_describe_all` | Describe all numeric columns at once |

### Statistical Analysis (12 tools)

| Tool | Computes |
|------|----------|
| `saf_stat_descriptives` | n, mean, SD, median, min/max, IQR, MAD, skew, kurtosis, 95% CI |
| `saf_stat_assumptions` | Shapiro-Wilk (or D'Agostino for n > 5000) + Levene's test |
| `saf_stat_compare_groups` | t-test (indep/paired/Welch) + Mann-Whitney + Cohen's d |
| `saf_stat_anova` | One-way ANOVA / Welch / Kruskal-Wallis + Tukey HSD + η² |
| `saf_stat_correlate` | Pearson (Fisher-z CI), Spearman, Kendall + bootstrap CIs |
| `saf_stat_regress` | OLS, logistic, robust (HC3) regression with CIs, AIC/BIC, VIF |
| `saf_stat_chi_square` | Independence test + Cramér's V + Fisher exact; GOF |
| `saf_stat_nonparametric` | Wilcoxon, sign, Friedman, Mann-Whitney, Kruskal-Wallis |
| `saf_stat_effect_size` | Cohen's d, η², Cramér's V, odds ratio, rank-biserial |
| `saf_stat_power` | Solve for power, sample size, or effect size |
| `saf_stat_outliers` | IQR (Tukey), z-score, modified z, Mahalanobis |
| `saf_stat_missing` | Per-column missing counts/%, complete-row ratio, MCAR sketch |

### Utility (1 tool)

| Tool | Purpose |
|------|---------|
| `list_tools` | List all available SAF MCP tools with descriptions |

### Resources & Prompt Helpers

| Resource | Purpose |
|----------|---------|
| `saf://guide` | Quick orientation to SAF and its capabilities |
| `saf://repo-ingestion` | Reminder of sandbox rules and data safety |
| `analyze_dataset_prompt` | Guided analysis workflow: inspect → preview → profile → frequencies → describe → missing |
| `survey_analysis_prompt` | Survey-specific workflow with optional reliability analysis |

## Live Deployment

SAF is publicly accessible at:

```
https://nasf.cloud/mcp
```

Connect any MCP-compatible agent (opencode, Hermes, Claude Code) via:

```json
{
  "mcpServers": {
    "saf": {
      "type": "remote",
      "url": "https://nasf.cloud/mcp"
    }
  }
}
```

## Example User Prompts

- **"List the datasets in my SAF data root."**
- **"Inspect metadata for `survey.sav`."**
- **"Run frequencies on `gender`, `age_group`, and `education` from `survey.sav`."**
- **"Cross-tabulate `satisfaction` by `region` with column percentages."**
- **"Check Cronbach's alpha for items q1 through q10 in `questionnaire.sav`."**
- **"Describe all numeric columns in `data.sav`."**
- **"Convert `data.xlsx` to `data.sav`."**
- **"Run descriptive statistics for age, split by gender, from `survey.sav`."**

## Security & Privacy

### Filesystem Sandbox
- All file paths resolved under `SAF_DATA_ROOT`
- Path traversal attempts blocked
- Supported file extensions validated
- Read/write operations confined to the sandbox

### Data Protection
- **No external uploads:** data stays on your machine
- **No telemetry:** SAF does not phone home
- **Local-first:** all processing is local

## Architecture

```
saf_mcp/
├── server.py          # MCP server entrypoint & tool registration
├── security.py        # Sandbox enforcement & extension validation
├── spss_utils.py      # SPSS/tabular read, write, preview, profile, frequencies
├── stats.py           # 15 statistical analysis primitives
└── __init__.py        # Package metadata
```

## License

MIT License — see [LICENSE](LICENSE) for details.

---

**Built by Azwa Fazil** · [azwafazil21@gmail.com](mailto:azwafazil21@gmail.com)
