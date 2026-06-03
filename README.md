# SAF — Statistical Analysis Forge

**An MCP server for SPSS-compatible datasets with rich statistical analysis, metadata inspection, and AI-ready interfaces.**

SAF is a privacy-first [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server for working with SPSS-compatible datasets (`.sav`, `.zsav`, `.por`) and tabular files (`.csv`, `.tsv`). Built on [`pyreadstat`](https://github.com/Roche/pyreadstat), it enables AI clients and LLMs to inspect metadata, preview rows, profile variables, generate SPSS syntax, and run comprehensive statistical analyses—all while keeping data local and secure.

## What SAF Is

- ✅ A Python MCP server implementing 19 specialized tools for dataset inspection and analysis
- ✅ A local-first, privacy-preserving assistant for `.sav`, `.zsav`, `.por`, `.csv`, and `.tsv` files
- ✅ Designed for research, survey, and teaching workflows with sensitive respondent data
- ✅ An AI-ready interface: inspect metadata, preview rows, profile variables, compute statistics, generate SPSS syntax
- ✅ Sandbox-enforced with filesystem isolation via `SAF_DATA_ROOT`

## What SAF Is Not

- ❌ Not a replacement for IBM SPSS
- ❌ Does not execute arbitrary SPSS syntax or shell commands
- ❌ Does not upload, transmit, or externally store datasets
- ❌ Does not make claims of full statistical equivalence with IBM SPSS

## Supported File Formats

| Format | Support |
|--------|---------|
| `.sav` | ✅ SPSS system files |
| `.zsav` | ✅ Compressed SPSS system files |
| `.por` | ✅ SPSS portable files |
| `.csv` | ✅ Comma-separated values (tabular) |
| `.tsv` | ✅ Tab-separated values (tabular) |

## Quick Start

### Prerequisites
- Python 3.9+
- `pip`

### Installation

Clone and install the package in editable mode:

```bash
git clone https://github.com/azwafazil/SAF.git
cd SAF
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

### Environment Setup

Set a local data root before running the server:

```bash
export SAF_DATA_ROOT=/absolute/path/to/your/saf-data
```

> **Data Security Note:** Keep real datasets **outside** the repository. The included `.gitignore` blocks common formats, but access control and careful storage remain your responsibility.

### Running the MCP Server

**Option 1: Python module**
```bash
python -m saf_mcp.server
```

**Option 2: Installed CLI**
```bash
saf-mcp
```

**Option 3: Custom MCP transport** (if supported by your MCP client)
```bash
MCP_TRANSPORT=streamable-http saf-mcp
```

## Integration: Claude Desktop

Add SAF to your Claude Desktop configuration:

**File:** `~/.config/Claude/claude_desktop_config.json` (macOS/Linux) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows)

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

Restart Claude Desktop, and SAF tools will appear in the **Tools** panel.

## MCP Tools Overview

SAF exposes **19 tools** organized in three groups:

### Dataset Inspection & Conversion (7 tools)

| Tool | Purpose |
|------|---------|
| `list_data_files` | Enumerate supported files under `SAF_DATA_ROOT` |
| `inspect_spss_metadata` | Read column names, labels, value labels, display formats, measures |
| `preview_spss_data` | Return first *N* rows (1–500) with optional row offset |
| `profile_spss_data` | Per-column: dtype, missing count, top values, summary statistics |
| `convert_spss_to_csv` | Write `.sav` / `.zsav` / `.por` → CSV inside sandbox |
| `convert_csv_to_sav` | Write `.csv` / `.tsv` → `.sav` inside sandbox |
| `generate_basic_spss_syntax` | Generate SPSS syntax (read-only; does not execute) |

### Statistical Analysis (12 tools)

All `saf_stat_*` tools accept SPSS files (`.sav`, `.zsav`, `.por`) or tabular files (`.csv`, `.tsv`) and return plain Python dictionaries with computed results, confidence intervals, and effect sizes.

| Tool | Computes |
|------|----------|
| `saf_stat_descriptives` | *n*, mean, SD, median, min/max, IQR, MAD, skewness, kurtosis, 95% CI |
| `saf_stat_assumptions` | Shapiro-Wilk (or D'Agostino for *n* > 5000) + Levene's homogeneity test |
| `saf_stat_compare_groups` | Independent/paired *t*-test, Welch *t*, Mann-Whitney *U* + Cohen's *d*, Hedges' *g* |
| `saf_stat_anova` | One-way ANOVA (classic/Welch/Kruskal-Wallis) + Tukey HSD + η² |
| `saf_stat_correlate` | Pearson (with Fisher-z CI), Spearman, Kendall + bootstrap CIs |
| `saf_stat_regress` | OLS, logistic, robust (HC3) regression with CIs, AIC/BIC, VIF |
| `saf_stat_chi_square` | Independence test + Cramér's *V* + Fisher exact (2×2); GOF with user-supplied expected |
| `saf_stat_nonparametric` | Wilcoxon signed-rank, sign test, Friedman, Mann-Whitney, Kruskal-Wallis |
| `saf_stat_effect_size` | Cohen's *d*, η², Cramér's *V*, odds ratio, rank-biserial |
| `saf_stat_power` | Solve for power, sample size, or effect size: *t*-test, ANOVA, χ², *z* |
| `saf_stat_outliers` | IQR (Tukey), *z*-score, modified *z* (Iglewicz–Hoaglin), Mahalanobis |
| `saf_stat_missing` | Per-column missing counts/%, complete-row ratio, MCAR association sketch |

### Resources & Prompt Helpers

| Resource | Purpose |
|----------|---------|
| `saf://guide` | Quick orientation to SAF and its capabilities |
| `saf://repo-ingestion` | Reminder of sandbox rules and data safety |
| `analyze_dataset_prompt` | Templated prompt guiding LLM through inspect → preview → profile workflow |

## Example User Prompts

Once SAF is integrated with Claude Desktop, you can use prompts like:

- **"List the datasets in my SAF data root."**
- **"Inspect metadata for `survey.sav`."**
- **"Preview the first 20 rows of `survey.zsav`."**
- **"Profile `wave1.por` and summarize missing values."**
- **"Convert `survey.sav` to `exports/survey.csv`."**
- **"Generate basic SPSS syntax for `survey.sav` using age, gender, and satisfaction."**
- **"Run descriptive statistics for age, split by gender, from `survey.sav`."**
- **"Compute a Pearson correlation matrix for age, income, and satisfaction in `data.csv`."**

## Security & Privacy

### Filesystem Sandbox
- All file paths are resolved **under** `SAF_DATA_ROOT`
- Path traversal attempts (e.g., `../../../etc/passwd`) are blocked
- Supported file extensions are validated
- Read and write operations are confined to the sandbox

### Data Protection
- **No external uploads:** Data remains on your machine
- **No telemetry:** SAF does not phone home
- **Local-first:** All processing is local; suitable for sensitive survey and research data

### Best Practices
- Do not commit real datasets to Git; use `.gitignore` (included)
- Store datasets in a directory outside the repository with restricted access
- Use `SAF_DATA_ROOT` to define an explicit sandbox for your AI-assisted workflows
- Verify file contents and permissions before sharing work products

## Development & Testing

### Run Tests
```bash
pytest tests/
```

### Build Distribution
```bash
pip install build
python -m build
```

### Install Development Dependencies
```bash
pip install -e ".[dev]"
```

## Roadmap

- 🎯 Richer metadata summaries (variable measures, display formats, missing-value rules)
- 🎯 Synthetic dataset fixtures for robust automated testing
- 🎯 Labeled data dictionary exports
- 🎯 Enhanced profiling for dates, categoricals, and survey-scale variables
- 🎯 MCP deployment guides for VS Code, JetBrains IDEs, and other clients
- 🎯 Advanced imputation strategies and data cleaning workflows

## Architecture

```
saf_mcp/
├── server.py          # MCP server entrypoint & tool registration
├── handlers.py        # Tool implementation & business logic
├── validators.py      # Input validation & sandbox enforcement
├── formatters.py      # Output formatting for MCP protocol
└── __main__.py        # CLI entry point
```

## License

MIT License — see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit with clear messages: `git commit -m "Add feature: ..."`
4. Push and open a pull request

## Links & Resources

- **MCP Specification:** [modelcontextprotocol.io](https://modelcontextprotocol.io)
- **pyreadstat:** [Roche/pyreadstat](https://github.com/Roche/pyreadstat)
- **SPSS Documentation:** [IBM SPSS Statistics](https://www.ibm.com/products/spss-statistics)
- **Statistical Methods:** [Scipy.stats](https://docs.scipy.org/doc/scipy/reference/stats.html)

---

**Questions or issues?** Open a [GitHub Issue](https://github.com/azwafazil/SAF/issues) or check the [MCP Specification](https://modelcontextprotocol.io) for more context.
